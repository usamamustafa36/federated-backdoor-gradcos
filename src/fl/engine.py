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
    # Per-round geometry of the updates the defense actually sees. These make
    # "salience" a measured quantity rather than a label attached to a trigger
    # name: salience_gap is how far the backdoor rotates a poisoned update off
    # the honest consensus direction, and mal_pair_cos is the collusion signal
    # GradCos/FoolsGold/FLAME read. Both are NaN on clean rounds.
    salience_gap: list[float] = field(default_factory=list)
    mal_pair_cos: list[float] = field(default_factory=list)
    honest_pair_cos: list[float] = field(default_factory=list)
    mal_norm_ratio: list[float] = field(default_factory=list)
    # Defect diagnostics, logged on EVERY round (clean or attacked) and in both
    # signal_subspace modes, so each run measures the counter's footprint on the
    # vector actually transmitted. Pure logging: nothing here feeds a decision.
    #   buffer_norm_share : median over clients of ||d_buffers||^2 / ||d||^2
    #   buffer_dist_share : median over client pairs of the buffers' share of
    #                       the squared pairwise distance ||d_i - d_j||^2
    #   pair_cos_full     : mean off-diagonal cosine over ALL clients, full vector
    #   pair_cos_sig      : the same over the trainable parameters only
    buffer_norm_share: list[float] = field(default_factory=list)
    buffer_dist_share: list[float] = field(default_factory=list)
    pair_cos_full: list[float] = field(default_factory=list)
    pair_cos_sig: list[float] = field(default_factory=list)

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
        # KNOWN DEFECT (iteration 4/5, see paper Sec. "Reproducibility notes"):
        # get_weights returns .numpy() views that ALIAS the model's storage, so
        # in round 1 only, every client's local training mutates global_weights
        # in place: round-1 clients train sequentially (client k starts from
        # client k-1's trained weights, BatchNorm counters accumulate), defenses
        # get the last client's weights as the "global", and the round-1
        # diagnostics are referenced to the round-1 aggregate. From round 2 on
        # global_weights are fresh arrays and the defect is gone. The fix below
        # is default-OFF so that the P1/P2 campaigns keep one code path;
        # `federated.copy_initial_global: true` turns it on. Iteration 5's
        # controlled check: experiments/round1_alias/.
        if bool(getattr(cfg.federated, "copy_initial_global", False)):
            self.global_weights = [np.array(w, copy=True) for w in self.global_weights]

        # Class weights to counter heavy IDS imbalance (benign is rare).
        self.class_weights = self._compute_class_weights()
        self._tmask = None          # lazily-built trainable-parameter mask

    def _compute_class_weights(self) -> np.ndarray:
        """Per-class loss weights.

        CICIoT2023's 8-class grouping is imbalanced 121:1 (DDoS 64.7% of rows,
        BruteForce 0.53%). Full inverse-frequency weighting -- what this used to
        do unconditionally -- gives BruteForce about 24x DDoS's weight, so a
        256-row batch holding ~1.4 BruteForce rows has its gradient set by those
        rows. Measured centrally on 200k rows, 15 epochs, same architecture:

            scheme            CA       macro-F1   CA swing over last 10 epochs
            none              0.8068   0.5606     0.0088
            inverse           0.6677   0.5851     0.0842
            sqrt-inverse      0.7611   0.6191     0.0323
            effective-number  0.8085   0.5901     0.0099
            (RandomForest on the same features: 0.7864 / 0.6496)

        Both `sqrt` and `effective` dominate `inverse` outright -- each is better
        on accuracy AND on macro-F1 AND on stability. Between the two it is a
        real trade: `effective` is +4.7 accuracy, `sqrt` is +2.9 macro-F1.

        `effective` is the default. The criticism this addresses is that the
        detector sat 0.066 above a constant classifier (majority floor 0.652);
        `effective` puts it 0.157 above, and past a tuned RandomForest, while
        still beating the old scheme on macro-F1. `sqrt` is the macro-F1-optimal
        choice if the rare classes are weighted more heavily in a later revision.
        Set `training.class_weighting` to override.
        """
        scheme = str(getattr(getattr(self.cfg, "training", object()),
                             "class_weighting", "effective")).lower()
        counts = np.bincount(self.ds.y_train, minlength=self.ds.num_classes).astype(np.float64)
        counts[counts == 0] = 1.0
        if scheme in ("none", "off", "uniform"):
            w = np.ones_like(counts)
        elif scheme in ("inverse", "inv"):
            w = counts.sum() / (self.ds.num_classes * counts)
        elif scheme in ("effective", "effective_number"):
            beta = 0.999
            w = (1.0 - beta) / (1.0 - np.power(beta, counts))
        else:                                   # "sqrt" (default)
            w = np.sqrt(counts.sum() / (self.ds.num_classes * counts))
        w = w / w.mean()                        # keep the loss scale comparable
        return w.astype(np.float32)

    def _client_fit(self, client: ClientState) -> FitRes:
        """Load global weights, train locally, return a Flower FitRes."""
        tu.set_weights(self.model, self.global_weights)
        x, y = client.training_data()
        # attack.mal_local_epochs (default 0 = off): malicious clients train for
        # this many local epochs instead of federated.local_epochs. Iteration-4
        # pilot: one epoch's backdoor is diluted away by parameter averaging.
        epochs = self.cfg.federated.local_epochs
        mal_ep = int(getattr(self.cfg.attack, "mal_local_epochs", 0) or 0)
        if client.malicious and mal_ep > 0:
            epochs = mal_ep
        n = tu.local_train(
            self.model, x, y,
            epochs=epochs,
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

    def _transform_malicious(self, results, rnd: int):
        """Apply the configured defense-aware transform to the malicious updates
        before aggregation. Operates on the FitRes list.

        constrained   rescale each malicious update to the round's MEDIAN honest
                      update norm, preserving direction (evades norm filtering).
        decorrelated  add zero-sum per-client noise across the malicious cohort,
                      which destroys the pairwise-similarity signal that
                      GradCos/FoolsGold/FLAME detect collusion with, while
                      cancelling under averaging so the backdoor still lands.
        adaptive      decorrelated, then norm-matched: neither direction nor
                      magnitude looks unusual. The strongest attacker here.
        """
        variant = getattr(self.cfg.attack, "variant", "simple")
        if variant not in ("constrained", "decorrelated", "adaptive"):
            return results
        g = np.concatenate([w.ravel() for w in self.global_weights])

        parsed = []  # (fr, ndarrays, delta_flat, norm, is_malicious)
        for _, fr in results:
            nds = parameters_to_ndarrays(fr.parameters)
            delta = np.concatenate([w.ravel() for w in nds]) - g
            parsed.append((fr, nds, delta, float(np.linalg.norm(delta)),
                           bool(fr.metrics.get("malicious", 0))))

        # Norms are taken on the trainable parameters. The attacker is trying to
        # look ordinary to a defense, and the defenses now measure there; over
        # the raw vector "match the median honest norm" meant matching a batch
        # counter, and the zero-sum noise was scaled to it (making it ~10x the
        # model update it was hiding in).
        tmask = self._signal_mask()
        parsed = [(fr, nds, d, float(np.linalg.norm(d[tmask])), mal)
                  for (fr, nds, d, _, mal) in parsed]
        honest_norms = [n for (_, _, _, n, mal) in parsed if not mal]
        if not honest_norms:
            return results
        target = float(np.median(honest_norms))

        # Decorrelation acts on the malicious block as a whole, so compute it
        # once here and look each client's row up below.
        new_delta = {}
        if variant in ("decorrelated", "adaptive"):
            mal_idx = [i for i, (_, _, _, _, mal) in enumerate(parsed) if mal]
            if len(mal_idx) >= 2:
                from ..attacks.evasion import zero_sum_noise, evasion_report
                block = np.stack([parsed[i][2] for i in mal_idx])
                rng = np.random.RandomState(self.cfg.seed * 1000 + rnd)
                scale = float(getattr(self.cfg.attack, "evasion_noise", 1.0))
                evaded = block + zero_sum_noise(block, scale, rng,
                                                mask=self._trainable_mask())
                self.last_evasion = evasion_report(block, evaded, mask=tmask)
                for k, i in enumerate(mal_idx):
                    new_delta[i] = evaded[k]

        out = []
        for i, (fr, nds, delta, norm, mal) in enumerate(parsed):
            delta = new_delta.get(i, delta)
            norm = float(np.linalg.norm(delta[tmask]))
            # `decorrelated` deliberately stops here, leaving the norm inflated;
            # `adaptive` goes on to hide that inflation too.
            renorm = mal and norm > 1e-12 and variant in ("constrained", "adaptive")
            if mal and (renorm or i in new_delta):
                if renorm:
                    # Rescale the MODEL UPDATE to the median honest norm and
                    # leave the BatchNorm buffers alone. Scaling the whole
                    # vector would also drag running_mean/running_var and the
                    # batch counter, which is collateral damage the attacker has
                    # no reason to inflict and which no defense now measures.
                    delta = delta.copy()
                    delta[tmask] *= (target / norm)
                scaled = g + delta
                # reshape flat vector back to the per-layer ndarrays
                new_nds, off = [], 0
                for w in nds:
                    new_nds.append(scaled[off:off + w.size].reshape(w.shape).astype(w.dtype))
                    off += w.size
                fr = FitRes(status=fr.status,
                            parameters=ndarrays_to_parameters(new_nds),
                            num_examples=fr.num_examples, metrics=fr.metrics)
            out.append((None, fr))
        return out

    def _boost_malicious(self, results):
        """attack.boost (default 1.0 = off): multiply the TRAINABLE part of each
        malicious delta by this factor (model-replacement-style scaling, Bagdasaryan
        et al. 2020). BatchNorm buffers are left as trained. Applied after the
        variant transform."""
        boost = float(getattr(self.cfg.attack, "boost", 1.0) or 1.0)
        if boost == 1.0:
            return results
        g = np.concatenate([w.ravel() for w in self.global_weights])
        tmask = self._trainable_mask()
        out = []
        for cp, fr in results:
            if fr.metrics.get("malicious", 0):
                nds = parameters_to_ndarrays(fr.parameters)
                d = np.concatenate([w.ravel() for w in nds]) - g
                d[tmask] *= boost
                flat = g + d
                new, off = [], 0
                for w in nds:
                    new.append(flat[off:off + w.size].reshape(w.shape).astype(w.dtype))
                    off += w.size
                fr = FitRes(status=fr.status, parameters=ndarrays_to_parameters(new),
                            num_examples=fr.num_examples, metrics=fr.metrics)
            out.append((cp, fr))
        return out

    def _signal_mask(self) -> np.ndarray:
        """The subspace decisions and logged geometry are measured on.

        Returns an all-True mask under `defense.signal_subspace: full`, which
        reproduces the pre-fix behaviour for the controlled comparison."""
        if str(getattr(self.cfg.defense, "signal_subspace", "trainable")).lower() == "full":
            return np.ones_like(self._trainable_mask(), dtype=bool)
        return self._trainable_mask()

    def _trainable_mask(self) -> np.ndarray:
        """Flat mask over the flattened state_dict, True on trainable params.
        Cached: the model shape does not change across rounds."""
        if getattr(self, "_tmask", None) is None:
            from ..defenses.base import DefenseStrategy
            self._tmask = DefenseStrategy.trainable_flat_mask(self.model)
        return self._tmask

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

            # Defense-aware attacker variants (constrained / decorrelated /
            # adaptive) reshape the malicious updates before the server sees
            # them; `simple` passes straight through. See attacks/evasion.py.
            if getattr(self.cfg.attack, "enabled", False):
                results = self._transform_malicious(results, rnd)
                results = self._boost_malicious(results)

            # Let defense strategies see the pre-aggregation global model (needed
            # to compute per-client update deltas, FLTrust root direction, etc.).
            if hasattr(self.strategy, "set_current_global"):
                self.strategy.set_current_global(self.global_weights)

            # Genuine Flower aggregation. Custom strategies may also stash which
            # clients they flagged on `self` for defense-metric logging.
            pre_global = self.global_weights
            params, agg_metrics = self.strategy.aggregate_fit(rnd, results, [])
            if params is not None:
                self.global_weights = parameters_to_ndarrays(params)
                tu.set_weights(self.model, self.global_weights)

            if rnd % self.cfg.logging.log_every == 0 or rnd == rounds:
                self._log_round(rnd, selected, agg_metrics, hist, verbose,
                                pre_agg=results, pre_global=pre_global)

        return hist

    def _log_round(self, rnd, selected, agg_metrics, hist: History, verbose,
                   pre_agg=None, pre_global=None):
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

        geo = self._update_geometry(pre_agg, pre_global)
        hist.salience_gap.append(geo["salience_gap"])
        hist.mal_pair_cos.append(geo["mal_pair_cos"])
        hist.honest_pair_cos.append(geo["honest_pair_cos"])
        hist.mal_norm_ratio.append(geo["mal_norm_ratio"])
        dd = self._defect_diagnostics(pre_agg, pre_global)
        hist.buffer_norm_share.append(dd["buffer_norm_share"])
        hist.buffer_dist_share.append(dd["buffer_dist_share"])
        hist.pair_cos_full.append(dd["pair_cos_full"])
        hist.pair_cos_sig.append(dd["pair_cos_sig"])

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

    def _defect_diagnostics(self, results, pre_global) -> dict:
        """How much of the transmitted update the non-trainable buffers carry.

        Computed over all participating clients on every round, independently of
        signal_subspace, so a `full` run and a `trainable` run report the same
        quantities about the same kind of vector. Never used by any decision.
        """
        nan = {"buffer_norm_share": float("nan"), "buffer_dist_share": float("nan"),
               "pair_cos_full": float("nan"), "pair_cos_sig": float("nan")}
        if not results or pre_global is None:
            return nan
        g = np.concatenate([w.ravel() for w in pre_global]).astype(np.float64)
        deltas = np.stack([
            np.concatenate([w.ravel() for w in parameters_to_ndarrays(fr.parameters)])
            .astype(np.float64) - g
            for _, fr in results])
        if len(deltas) < 2:
            return nan
        # Always the TRAINABLE mask (not _signal_mask, which is all-True under
        # `full`): the point is to measure the buffers in either mode.
        mask = np.asarray(self._trainable_mask(), dtype=bool)
        if mask.all():
            return nan
        sq_all = (deltas ** 2).sum(axis=1)
        sq_buf = (deltas[:, ~mask] ** 2).sum(axis=1)
        norm_share = float(np.median(sq_buf / (sq_all + 1e-30)))
        n = len(deltas)
        iu = np.triu_indices(n, 1)

        def pair_sqdist(x):
            sq = (x ** 2).sum(axis=1)
            return np.maximum(sq[:, None] + sq[None, :] - 2.0 * (x @ x.T), 0.0)[iu]

        d_all = pair_sqdist(deltas)
        d_buf = pair_sqdist(deltas[:, ~mask])
        dist_share = float(np.median(d_buf / (d_all + 1e-30)))

        def mean_offdiag_cos(x):
            u = x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-30)
            c = np.clip(u @ u.T, -1.0, 1.0)
            return float(c[iu].mean())

        return {"buffer_norm_share": norm_share, "buffer_dist_share": dist_share,
                "pair_cos_full": mean_offdiag_cos(deltas),
                "pair_cos_sig": mean_offdiag_cos(deltas[:, mask])}

    def _update_geometry(self, results, pre_global) -> dict:
        """Measure the update geometry the defenses actually read.

        ``salience_gap`` is the operational definition of trigger salience used
        in the paper: how much further off the honest consensus direction a
        poisoned update sits than an honest one does,

            gap = mean_i in honest cos(d_i, dbar_h) - mean_j in mal cos(d_j, dbar_h),

        with ``dbar_h`` the mean honest update. It is 0 when the backdoor does
        not rotate the update at all and grows as the trigger becomes more
        conspicuous, so BSR and DR can be regressed on it directly instead of on
        the trigger's name. ``mal_pair_cos`` and ``honest_pair_cos`` are the
        collusion signal (mean off-diagonal cosine within each group), and
        ``mal_norm_ratio`` is the median malicious norm over the median honest
        norm -- what a magnitude-based rule would see. All NaN with no attacker.
        """
        nan = {"salience_gap": float("nan"), "mal_pair_cos": float("nan"),
               "honest_pair_cos": float("nan"), "mal_norm_ratio": float("nan")}
        if not results or pre_global is None:
            return nan

        g = np.concatenate([w.ravel() for w in pre_global])
        deltas, is_mal = [], []
        for _, fr in results:
            nds = parameters_to_ndarrays(fr.parameters)
            deltas.append(np.concatenate([w.ravel() for w in nds]) - g)
            is_mal.append(bool(fr.metrics.get("malicious", 0)))
        deltas = np.stack(deltas)
        # Measure the geometry the defenses actually decide on: trainable
        # parameters only. Over the raw state_dict, salience_gap collapses to
        # ~4e-5 and every pairwise cosine sits at 0.998, because one BatchNorm
        # batch counter carries 98% of the norm. See
        # DefenseStrategy.set_signal_mask.
        deltas = deltas[:, self._signal_mask()]
        is_mal = np.array(is_mal, dtype=bool)
        if not is_mal.any() or is_mal.all():
            return nan

        unit = deltas / (np.linalg.norm(deltas, axis=1, keepdims=True) + 1e-12)
        honest_mean = deltas[~is_mal].mean(axis=0)
        hm = honest_mean / (np.linalg.norm(honest_mean) + 1e-12)
        cos_to_hm = unit @ hm

        def mean_offdiag(u):
            if len(u) < 2:
                return float("nan")
            c = np.clip(u @ u.T, -1.0, 1.0)
            n = len(u)
            return float((c.sum() - np.trace(c)) / (n * (n - 1)))

        norms = np.linalg.norm(deltas, axis=1)
        return {
            "salience_gap": float(cos_to_hm[~is_mal].mean() - cos_to_hm[is_mal].mean()),
            "mal_pair_cos": mean_offdiag(unit[is_mal]),
            "honest_pair_cos": mean_offdiag(unit[~is_mal]),
            "mal_norm_ratio": float(np.median(norms[is_mal])
                                    / (np.median(norms[~is_mal]) + 1e-12)),
        }
