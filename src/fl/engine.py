"""Federated training engine.

A thin synchronous round-loop that orchestrates real Flower Strategy objects
(FedAvg and our custom defense strategies). No Ray / gRPC: clients are trained
in-process and their updates handed to ``strategy.aggregate_fit`` as genuine
Flower ``FitRes`` objects. This keeps the aggregation logic 100% Flower while
staying fast and debuggable on a single laptop.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
from flwr.common import (
    Code,
    FitRes,
    Status,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)

from .. import config
from ..data.preprocess import Dataset
from ..models.cnn_lstm import build_model
from . import torch_utils as tu


@dataclass
class ClientState:
    """One federated client: a fixed slice of the training data, plus an
    optional attacker hook that poisons its local data before training."""
    cid: int
    x: np.ndarray
    y: np.ndarray
    malicious: bool = False
    attack_fn: object = None  # callable(x, y) -> (x_poisoned, y_poisoned)

    def training_data(self):
        if self.malicious and self.attack_fn is not None:
            return self.attack_fn(self.x, self.y)
        return self.x, self.y


@dataclass
class History:
    rounds: list[int] = field(default_factory=list)
    accuracy: list[float] = field(default_factory=list)
    macro_f1: list[float] = field(default_factory=list)
    loss: list[float] = field(default_factory=list)
    bsr: list[float] = field(default_factory=list)            # backdoor success rate
    detection_rate: list[float] = field(default_factory=list)  # malicious clients caught
    false_positive_rate: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__


class FederatedEngine:
    def __init__(
        self,
        cfg,
        dataset: Dataset,
        clients: list[ClientState],
        strategy,
        device: str,
        backdoor_eval=None,   # callable(model) -> bsr float, or None
    ):
        self.cfg = cfg
        self.ds = dataset
        self.clients = clients
        self.strategy = strategy
        self.device = device
        self.backdoor_eval = backdoor_eval

        # One reused model instance for both client training and global eval.
        self.model = build_model(cfg, dataset.num_features, dataset.num_classes)
        self.global_weights = tu.get_weights(self.model)

        # Class weights to counter heavy IDS imbalance (benign is rare).
        self.class_weights = self._compute_class_weights()

    def _compute_class_weights(self) -> np.ndarray:
        counts = np.bincount(self.ds.y_train, minlength=self.ds.num_classes).astype(np.float64)
        counts[counts == 0] = 1.0
        w = counts.sum() / (self.ds.num_classes * counts)
        return w.astype(np.float32)

    def _client_fit(self, client: ClientState) -> FitRes:
        """Load global weights, train locally, return a Flower FitRes."""
        tu.set_weights(self.model, self.global_weights)
        x, y = client.training_data()
        n = tu.local_train(
            self.model, x, y,
            epochs=self.cfg.federated.local_epochs,
            lr=self.cfg.model.lr,
            batch_size=self.cfg.federated.batch_size,
            device=self.device,
            class_weights=self.class_weights,
        )
        weights = tu.get_weights(self.model)
        return FitRes(
            status=Status(Code.OK, ""),
            parameters=ndarrays_to_parameters(weights),
            num_examples=n,
            metrics={"cid": client.cid, "malicious": int(client.malicious)},
        )

    def _constrain_malicious(self, results):
        """Norm-match malicious updates to the median honest update (constrained
        backdoor). Operates on the FitRes list before aggregation."""
        g = np.concatenate([w.ravel() for w in self.global_weights])

        parsed = []  # (fr, ndarrays, delta_flat, norm, is_malicious)
        for _, fr in results:
            nds = parameters_to_ndarrays(fr.parameters)
            delta = np.concatenate([w.ravel() for w in nds]) - g
            parsed.append((fr, nds, delta, float(np.linalg.norm(delta)),
                           bool(fr.metrics.get("malicious", 0))))

        honest_norms = [n for (_, _, _, n, mal) in parsed if not mal]
        if not honest_norms:
            return results
        target = float(np.median(honest_norms))

        out = []
        for fr, nds, delta, norm, mal in parsed:
            if mal and norm > 1e-12:
                scaled = g + delta * (target / norm)
                # reshape flat vector back to the per-layer ndarrays
                new_nds, i = [], 0
                for w in nds:
                    new_nds.append(scaled[i:i + w.size].reshape(w.shape).astype(w.dtype))
                    i += w.size
                fr = FitRes(status=fr.status,
                            parameters=ndarrays_to_parameters(new_nds),
                            num_examples=fr.num_examples, metrics=fr.metrics)
            out.append((None, fr))
        return out

    def _select_clients(self, rnd: int) -> list[ClientState]:
        k = self.cfg.federated.clients_per_round
        if k >= len(self.clients):
            return self.clients
        rng = np.random.RandomState(self.cfg.seed + rnd)
        idx = rng.choice(len(self.clients), size=k, replace=False)
        return [self.clients[i] for i in idx]

    def run(self, verbose: bool = True) -> History:
        hist = History()
        rounds = self.cfg.federated.rounds

        for rnd in range(1, rounds + 1):
            # Per-round liveness ping for the external silent-hang watchdog.
            config.touch_heartbeat()
            selected = self._select_clients(rnd)
            results = [(None, self._client_fit(c)) for c in selected]

            # Constrained backdoor variant: rescale each malicious update to the
            # round's median honest-update norm, so norm-based defenses (Krum,
            # FLAME clipping) can't flag it on magnitude while the backdoor
            # DIRECTION is preserved.
            if (getattr(self.cfg.attack, "enabled", False)
                    and getattr(self.cfg.attack, "variant", "simple") == "constrained"):
                results = self._constrain_malicious(results)

            # Let defense strategies see the pre-aggregation global model (needed
            # to compute per-client update deltas, FLTrust root direction, etc.).
            if hasattr(self.strategy, "set_current_global"):
                self.strategy.set_current_global(self.global_weights)

            # Genuine Flower aggregation. Custom strategies may also stash which
            # clients they flagged on `self` for defense-metric logging.
            params, agg_metrics = self.strategy.aggregate_fit(rnd, results, [])
            if params is not None:
                self.global_weights = parameters_to_ndarrays(params)
                tu.set_weights(self.model, self.global_weights)

            if rnd % self.cfg.logging.log_every == 0 or rnd == rounds:
                self._log_round(rnd, selected, agg_metrics, hist, verbose)

        return hist

    def _log_round(self, rnd, selected, agg_metrics, hist: History, verbose):
        ev = tu.evaluate(
            self.model, self.ds.x_test, self.ds.y_test,
            self.ds.num_classes, self.device,
        )
        hist.rounds.append(rnd)
        hist.accuracy.append(ev["accuracy"])
        hist.macro_f1.append(ev["macro_f1"])
        hist.loss.append(ev["loss"])

        bsr = float(self.backdoor_eval(self.model)) if self.backdoor_eval else float("nan")
        hist.bsr.append(bsr)

        # Defense metrics: did the strategy flag the right clients this round?
        dr, fpr = self._defense_metrics(selected, agg_metrics)
        hist.detection_rate.append(dr)
        hist.false_positive_rate.append(fpr)

        if verbose:
            msg = (f"round {rnd:>3} | acc {ev['accuracy']:.4f} | f1 {ev['macro_f1']:.4f} "
                   f"| loss {ev['loss']:.4f}")
            if self.backdoor_eval:
                msg += f" | BSR {bsr:.4f}"
            if not np.isnan(dr):
                msg += f" | DR {dr:.2f} FPR {fpr:.2f}"
            print(msg, flush=True)

    def _defense_metrics(self, selected, agg_metrics):
        """Compare strategy-flagged clients (if any) against ground truth."""
        flagged = getattr(self.strategy, "last_flagged_cids", None)
        if flagged is None:
            return float("nan"), float("nan")
        flagged = set(flagged)
        mal = {c.cid for c in selected if c.malicious}
        honest = {c.cid for c in selected if not c.malicious}
        dr = len(flagged & mal) / len(mal) if mal else 0.0
        fpr = len(flagged & honest) / len(honest) if honest else 0.0
        return dr, fpr
