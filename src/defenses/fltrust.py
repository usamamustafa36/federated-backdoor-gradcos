"""FLTrust (Cao et al., 2020).

The server keeps a small clean 'root' dataset, trains it one step from the
current global model to get a trusted update direction g0. Each client update
gi is scored by ReLU(cosine(gi, g0)) and rescaled to ||g0||, then trust-weighted
averaged. Updates pointing away from the trusted direction (cos <= 0) get zero
weight -> effectively excluded.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class FLTrust(DefenseStrategy):
    def __init__(self, dataset, cfg, device, root_size: int = 300):
        super().__init__()
        self.cfg = cfg
        self.device = device
        self.dataset = dataset
        self.root_x, self.root_y = self._sample_root(dataset, root_size, cfg.seed)
        # Iteration 9: pure logging for Corollary 3 (never feeds a decision).
        self._counter_mask = None
        self.last_counter_diag: dict | None = None

    @staticmethod
    def _sample_root(dataset, root_size, seed):
        """Class-balanced clean reference set held by the server."""
        rng = np.random.RandomState(seed + 999)
        y = dataset.y_train
        classes = np.unique(y)
        per = max(1, root_size // len(classes))
        idx = []
        for c in classes:
            c_idx = np.where(y == c)[0]
            take = min(per, len(c_idx))
            idx.append(rng.choice(c_idx, size=take, replace=False))
        idx = np.concatenate(idx)
        rng.shuffle(idx)
        return dataset.x_train[idx], dataset.y_train[idx]

    def _server_update(self) -> np.ndarray:
        """Train a copy of the global model on the root set; return its flat update."""
        from ..fl.torch_utils import get_weights, local_train, set_weights
        from ..models.cnn_lstm import build_model

        model = build_model(self.cfg, self.dataset.num_features, self.dataset.num_classes)
        set_weights(model, [w.astype(np.float32) for w in self.current_global])
        local_train(
            model, self.root_x, self.root_y,
            epochs=self.cfg.federated.local_epochs,
            lr=self.cfg.model.lr,
            batch_size=self.cfg.federated.batch_size,
            device=self.device,
        )
        g = self.flatten(self.current_global)
        return self.flatten([w.astype(np.float64) for w in get_weights(model)]) - g

    def _get_counter_mask(self, n: int) -> np.ndarray | None:
        """Flat mask of the num_batches_tracked coordinates (state_dict order)."""
        if self._counter_mask is None:
            from ..models.cnn_lstm import build_model
            model = build_model(self.cfg, self.dataset.num_features,
                                self.dataset.num_classes)
            parts = []
            for k, v in model.state_dict().items():
                size = int(np.asarray(v.detach().cpu().numpy()).size)
                parts.append(np.full(size, k.endswith("num_batches_tracked"), dtype=bool))
            self._counter_mask = np.concatenate(parts)
        return self._counter_mask if self._counter_mask.size == n else None

    def _counter_diag(self, g0: np.ndarray, deltas: list) -> dict:
        """Corollary 3's quantities on the real updates of this round:
        q0 / qi = counter share of the squared norm of the server's / client's
        FULL update, the corollary's lower bound
        sqrt(qi q0) - sqrt((1-qi)(1-q0)) and the measured full-vector cosine."""
        nan = float("nan")
        m = self._get_counter_mask(g0.size)
        if m is None or not deltas:
            return {"q0": nan, "qi_min": nan, "qsum_min": nan,
                    "bound_min": nan, "cos_full_min": nan}
        def share(v):
            t = float(np.dot(v, v))
            return float(np.dot(v[m], v[m])) / t if t > 0 else nan
        q0 = share(g0)
        n0 = float(np.linalg.norm(g0)) + 1e-12
        qs, bounds, coss = [], [], []
        for d in deltas:
            qi = share(d)
            qs.append(qi)
            bounds.append(np.sqrt(qi * q0) - np.sqrt(max(0.0, (1 - qi) * (1 - q0))))
            coss.append(float(np.dot(d, g0)) / ((float(np.linalg.norm(d)) + 1e-12) * n0))
        return {"q0": q0, "qi_min": float(np.min(qs)),
                "qsum_min": float(q0 + np.min(qs)),
                "bound_min": float(np.min(bounds)),
                "cos_full_min": float(np.min(coss))}

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        g = self.flatten(self.current_global)
        g0 = self._server_update()
        g0_norm = np.linalg.norm(g0) + 1e-12
        self.last_counter_diag = self._counter_diag(g0, [self.flatten(nds) - g
                                                          for _, nds, _, _ in updates])

        # Trust score and the norm rescaling are both measured on the trainable
        # parameters. On the raw vector, ||g0|| and ||gi|| are dominated by
        # num_batches_tracked, and the server runs 2 batches on its 300-row root
        # set against each client's 79 -- so "rescale to ||g0||" shrank every
        # client update by ~40x for reasons unrelated to trust, which is what
        # made FLTrust learn ~40x too slowly. The scale is applied to the FULL
        # update so the BatchNorm buffers still aggregate.
        g0s = self.sig(g0)
        g0s_norm = float(np.linalg.norm(g0s)) + 1e-12
        agg = np.zeros_like(g)
        ts_sum = 0.0
        flagged = []
        for cid, nds, _, _ in updates:
            gi = self.flatten(nds) - g
            gis = self.sig(gi)
            gis_norm = float(np.linalg.norm(gis)) + 1e-12
            cos = float(np.dot(gis, g0s) / (gis_norm * g0s_norm))
            ts = max(cos, 0.0)                       # ReLU trust score
            if ts <= 0.0:
                flagged.append(cid)
                continue
            agg += ts * gi * (g0s_norm / gis_norm)   # rescale to ||g0|| on-subspace
            ts_sum += ts

        if ts_sum > 0:
            agg /= ts_sum
        new = g + agg
        self.last_flagged_cids = flagged
        return self.pack(self.unflatten(new, self.current_global),
                         {"fltrust_trusted": len(updates) - len(flagged)})
