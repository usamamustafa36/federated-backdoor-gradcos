"""Krum / Multi-Krum (Blanchard et al., 2017).

Score each client by the sum of squared distances to its n-f-2 nearest
neighbours; the client(s) with the smallest score sit in the densest part of
the update cloud and are kept. Multi-Krum keeps the best n-f and averages them.
Excluded clients are reported as 'flagged' for detection metrics.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class Krum(DefenseStrategy):
    def __init__(self, num_malicious: int = 4, multi: bool = True):
        super().__init__()
        self.f = num_malicious
        self.multi = multi

    def aggregate_fit(self, server_round, results, failures):
        if not results:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        vecs = np.stack([self.flatten(u[1]) for u in updates])
        n = len(vecs)

        # Krum needs n > 2f + 2; clamp f to what the cohort can support.
        f = int(self.f)
        if n <= 2 * f + 2:
            f = max(0, (n - 3) // 2)

        # Pairwise squared L2 distances.
        sq = np.sum(vecs ** 2, axis=1)
        dist = sq[:, None] + sq[None, :] - 2.0 * (vecs @ vecs.T)
        np.fill_diagonal(dist, np.inf)
        dist = np.maximum(dist, 0.0)

        k = max(1, n - f - 2)
        scores = np.array([np.sort(dist[i])[:k].sum() for i in range(n)])

        m = max(1, n - f) if self.multi else 1
        selected = set(np.argsort(scores)[:m].tolist())
        self.last_flagged_cids = [cids[i] for i in range(n) if i not in selected]

        sel = [updates[i] for i in sorted(selected)]
        agg = self.weighted_average([u[1] for u in sel], [u[2] for u in sel])
        return self.pack(agg, {"krum_selected": len(sel), "krum_f": f})
