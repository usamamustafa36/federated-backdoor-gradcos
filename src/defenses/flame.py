"""FLAME (Nguyen et al., 2022).

Three stages on the client update deltas:
  1. Clustering  - HDBSCAN on pairwise cosine distance; keep the majority
                   cluster, drop outliers (poisoned models point in odd
                   directions and fall outside it).
  2. Clipping    - clip each admitted delta's L2 norm to the median norm S,
                   bounding the influence of any single update.
  3. Noising     - add Gaussian noise (sigma = lambda * S) to the aggregate to
                   wash out residual backdoor signal (differential-privacy style).
"""
from __future__ import annotations

import numpy as np
from sklearn.cluster import HDBSCAN

from .base import DefenseStrategy


class FLAME(DefenseStrategy):
    def __init__(self, noise_lambda: float = 0.001, seed: int = 42,
                 noise_mask: np.ndarray | None = None):
        super().__init__()
        self.noise_lambda = noise_lambda
        self.rng = np.random.RandomState(seed)
        # Flat bool mask (len = flattened model): True where DP noise may be
        # applied (trainable params), False on BatchNorm running stats / counters.
        # Noising running_var can make it negative -> sqrt(neg)=NaN in eval BN,
        # which collapses the model. None -> noise everything (legacy behaviour).
        self.noise_mask = noise_mask

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])  # (n, d)
        n = len(deltas)

        # --- 1. clustering on cosine distance ---
        norms = np.linalg.norm(deltas, axis=1, keepdims=True) + 1e-12
        unit = deltas / norms
        cos_sim = np.clip(unit @ unit.T, -1.0, 1.0)
        cos_dist = (1.0 - cos_sim).astype(np.float64)
        np.fill_diagonal(cos_dist, 0.0)

        admitted = self._majority_cluster(cos_dist, n)
        self.last_flagged_cids = [cids[i] for i in range(n) if i not in admitted]

        # --- 2. norm clipping to the median of admitted norms ---
        adm = sorted(admitted)
        adm_norms = norms[adm, 0]
        S = float(np.median(adm_norms))
        clipped = []
        counts = []
        for i in adm:
            scale = min(1.0, S / (norms[i, 0]))
            clipped.append(deltas[i] * scale)
            counts.append(updates[i][2])
        clipped = np.stack(clipped)

        # weighted mean of clipped deltas
        w = np.array(counts, dtype=np.float64)
        w = w / w.sum()
        agg_delta = (clipped * w[:, None]).sum(axis=0)

        # --- 3. add noise (trainable params only) ---
        # FLAME's differential-privacy noise targets the model UPDATE. BatchNorm
        # running stats are not part of that update; noising running_var can make
        # it negative -> sqrt(neg)=NaN in eval-mode BatchNorm. Mask them out.
        sigma = self.noise_lambda * S
        if sigma > 0:
            noise = self.rng.normal(0.0, sigma, size=agg_delta.shape)
            if self.noise_mask is not None:
                noise = noise * self.noise_mask
            agg_delta = agg_delta + noise

        new = g + agg_delta
        return self.pack(self.unflatten(new, self.current_global),
                         {"flame_admitted": len(adm), "flame_S": S})

    def _majority_cluster(self, cos_dist: np.ndarray, n: int) -> set[int]:
        """Return indices of the majority cluster (FLAME admits these)."""
        if n < 4:
            return set(range(n))  # too few to cluster meaningfully
        min_cluster_size = n // 2 + 1
        labels = HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric="precomputed",
            allow_single_cluster=True,
        ).fit_predict(cos_dist)

        valid = labels[labels >= 0]
        if len(valid) == 0:
            return set(range(n))  # all noise -> admit everyone (no confident outliers)
        # majority (largest) cluster id
        vals, counts = np.unique(valid, return_counts=True)
        majority = vals[np.argmax(counts)]
        return set(np.where(labels == majority)[0].tolist())
