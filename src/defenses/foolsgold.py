"""FoolsGold (Fung, Yoon, and Beschastnikh, RAID 2020).

A sybil-resistant aggregator built on the same cosine signal GradCos and FLAME
use, but read the opposite way. Sybils (colluding backdoor clients) share a
common poisoning objective, so their *aggregated update histories* stay unusually
similar to one another over time, while honest clients — training on their own
shards — do not. FoolsGold therefore penalises clients whose historical update
direction is too close to another client's, driving their aggregation weight
toward zero, while leaving well-separated honest clients at full weight.

Design notes for this codebase:
  * History is the running sum of each client's per-round update delta, keyed by
    client id, so the detector accumulates evidence across rounds (a single round
    is often not enough to separate sybils).
  * "Pardoning" rescales similarities so an honest client that happens to look
    like a sybil is not wrongly down-weighted.
  * The logit re-weighting and 0.99 cap follow the original formulation.
  * Clients whose final weight is ~0 are reported as flagged, so the engine's
    detection-rate / false-positive-rate metrics work as for the other defenses.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class FoolsGold(DefenseStrategy):
    def __init__(self, flag_threshold: float = 1e-3):
        super().__init__()
        # cid -> running sum of that client's update deltas (feature-importance
        # weighting from the original paper is omitted; the plain history variant
        # is standard and reference-free).
        self.history: dict[int, np.ndarray] = {}
        self.flag_threshold = flag_threshold

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = [self.flatten(u[1]) - g for u in updates]
        n = len(deltas)

        for cid, d in zip(cids, deltas):
            if cid not in self.history:
                self.history[cid] = np.zeros_like(d)
            self.history[cid] += d

        # Similarity is taken on the trainable parameters. The accumulated
        # history is otherwise ~99.98% batch counter (it grows exactly linearly),
        # so every pair of client histories sits at cosine >= 0.9998 whether they
        # collude or not, and the weighting is decided by 4th-decimal residue --
        # which is what made FoolsGold bimodal across seeds.
        wv = self._foolsgold_weights([self.sig(self.history[c]) for c in cids], n)

        # Clients driven to (near) zero weight are the flagged sybils.
        self.last_flagged_cids = [cids[i] for i in range(n) if wv[i] <= self.flag_threshold]

        wsum = float(wv.sum())
        if wsum <= 0:
            # Degenerate round: fall back to uniform so we never divide by zero.
            wv = np.ones(n) / n
            wsum = 1.0
        agg_delta = np.zeros_like(g)
        for i in range(n):
            agg_delta += (wv[i] / wsum) * deltas[i]

        new = g + agg_delta
        return self.pack(self.unflatten(new, self.current_global),
                         {"foolsgold_kept": int((wv > self.flag_threshold).sum())})

    @staticmethod
    def _foolsgold_weights(hist_vecs: list[np.ndarray], n: int) -> np.ndarray:
        if n == 1:
            return np.ones(1)
        H = np.stack(hist_vecs)
        norms = np.linalg.norm(H, axis=1, keepdims=True) + 1e-12
        unit = H / norms
        cs = np.clip(unit @ unit.T, -1.0, 1.0)
        np.fill_diagonal(cs, 0.0)

        maxcs = cs.max(axis=1) + 1e-12
        # Pardoning: if client i's peak similarity is below client j's, scale
        # cs[i, j] down so i is not blamed for j's resemblance to it.
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if maxcs[i] < maxcs[j]:
                    cs[i, j] *= maxcs[i] / maxcs[j]

        wv = 1.0 - cs.max(axis=1)
        wv = np.clip(wv, 0.0, 1.0)
        wv = wv / (wv.max() + 1e-12)
        wv[wv == 1.0] = 0.99
        # Logit re-scaling: sharpens the separation between trusted and penalised.
        wv = np.log(wv / (1.0 - wv) + 1e-12) + 0.5
        wv = np.clip(wv, 0.0, 1.0)
        return wv
