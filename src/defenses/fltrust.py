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

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        g = self.flatten(self.current_global)
        g0 = self._server_update()
        g0_norm = np.linalg.norm(g0) + 1e-12

        agg = np.zeros_like(g)
        ts_sum = 0.0
        flagged = []
        for cid, nds, _, _ in updates:
            gi = self.flatten(nds) - g
            gi_norm = np.linalg.norm(gi) + 1e-12
            cos = float(np.dot(gi, g0) / (gi_norm * g0_norm))
            ts = max(cos, 0.0)                       # ReLU trust score
            if ts <= 0.0:
                flagged.append(cid)
                continue
            agg += ts * (gi / gi_norm) * g0_norm     # rescale to ||g0||
            ts_sum += ts

        if ts_sum > 0:
            agg /= ts_sum
        new = g + agg
        self.last_flagged_cids = flagged
        return self.pack(self.unflatten(new, self.current_global),
                         {"fltrust_trusted": len(updates) - len(flagged)})
