"""Shared base for defense aggregation strategies.

All defenses subclass Flower's FedAvg and override ``aggregate_fit``. The base
provides the plumbing they share: pulling per-client ndarrays out of FitRes,
flatten/unflatten, weighted averaging, and a ``last_flagged_cids`` slot the
engine reads to compute detection-rate / false-positive-rate.
"""
from __future__ import annotations

import numpy as np
from flwr.common import FitRes, ndarrays_to_parameters, parameters_to_ndarrays
from flwr.server.strategy import FedAvg


class DefenseStrategy(FedAvg):
    def __init__(self, **kwargs):
        kwargs.setdefault("fraction_fit", 1.0)
        kwargs.setdefault("fraction_evaluate", 0.0)
        kwargs.setdefault("accept_failures", False)
        super().__init__(**kwargs)
        self.last_flagged_cids: list[int] = []
        self.current_global: list[np.ndarray] | None = None

    # The engine pushes the pre-round global model here.
    def set_current_global(self, weights: list[np.ndarray]) -> None:
        self.current_global = [np.asarray(w, dtype=np.float64) for w in weights]

    # ---- helpers --------------------------------------------------------
    @staticmethod
    def extract(results) -> list[tuple[int, list[np.ndarray], int, bool]]:
        """-> [(cid, ndarrays, num_examples, is_malicious), ...]"""
        out = []
        for _, fr in results:  # fr: FitRes
            nds = [w.astype(np.float64) for w in parameters_to_ndarrays(fr.parameters)]
            cid = int(fr.metrics.get("cid", -1))
            mal = bool(fr.metrics.get("malicious", 0))
            out.append((cid, nds, int(fr.num_examples), mal))
        return out

    @staticmethod
    def flatten(nds: list[np.ndarray]) -> np.ndarray:
        return np.concatenate([w.ravel() for w in nds])

    @staticmethod
    def trainable_flat_mask(model) -> np.ndarray:
        """Flat boolean mask over the flattened state_dict (same order as
        ``flatten``): True where the entry is a trainable parameter, False for
        buffers (BatchNorm ``running_mean``/``running_var``, ``num_batches_tracked``).

        Used by FLAME so its DP noise touches only the model update and never the
        normalization buffers: additive noise on ``running_var`` can drive it
        negative, and eval-mode BatchNorm then computes ``sqrt(running_var+eps)``
        = NaN, collapsing every prediction.
        """
        buf_keys = {k for k, _ in model.named_buffers()}
        parts = []
        for k, v in model.state_dict().items():
            size = int(np.asarray(v.detach().cpu().numpy()).size)
            parts.append(np.full(size, k not in buf_keys, dtype=bool))
        return np.concatenate(parts)

    @staticmethod
    def unflatten(vec: np.ndarray, template: list[np.ndarray]) -> list[np.ndarray]:
        out, i = [], 0
        for w in template:
            n = w.size
            out.append(vec[i:i + n].reshape(w.shape))
            i += n
        return out

    @staticmethod
    def weighted_average(weight_sets: list[list[np.ndarray]], counts: list[int]) -> list[np.ndarray]:
        total = float(sum(counts)) or 1.0
        agg = [np.zeros_like(w) for w in weight_sets[0]]
        for ws, c in zip(weight_sets, counts):
            for k, w in enumerate(ws):
                agg[k] += w * (c / total)
        return agg

    def pack(self, nds: list[np.ndarray], metrics: dict | None = None):
        out = [w.astype(np.float32) for w in nds]
        return ndarrays_to_parameters(out), (metrics or {})
