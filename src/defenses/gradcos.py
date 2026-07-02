"""GradCos - proposed defense (thesis 3.6).

Intuition: honest clients optimise the same objective on similar-distribution
data, so their update directions are mutually well-aligned. A backdoor pushes a
client's update toward the trigger->benign association, dropping its cosine
similarity to the honest majority. GradCos flags malicious clients from the
pairwise cosine-similarity structure of the updates and aggregates only the rest.

Key property (vs FLTrust): needs NO clean server-side dataset - the signal comes
purely from inter-client agreement.

Two detection methods:
  * "meansim" (v1) - flag clients whose MEAN pairwise cosine similarity to the
        cohort falls below an adaptive (median - k*MAD) threshold. Simple, but
        FAILS under collusion: when many attackers (20-30%) submit mutually
        similar backdoor updates, each one's mean similarity is propped up by its
        fellow attackers, so none looks like a tail outlier.
  * "cluster" (v2, DEFAULT) - collusion-robust. Cluster the updates in cosine
        space and, under the benign-majority assumption (<50% malicious), keep
        the LARGEST cluster and flag the rest. Collusion now HELPS detection: the
        more tightly the attackers agree, the more cleanly they separate as a
        minority cluster. A separation gate keeps all clients when no group is
        meaningfully distinct (clean rounds), protecting clean accuracy.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class GradCos(DefenseStrategy):
    def __init__(self, threshold: float = 0.5, adaptive: bool = True,
                 min_keep_fraction: float = 0.5, method: str = "cluster",
                 separation_k: float = 1.5):
        super().__init__()
        self.threshold = threshold
        self.adaptive = adaptive
        self.min_keep_fraction = min_keep_fraction
        self.method = method
        self.separation_k = separation_k

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])
        n = len(deltas)

        # Pairwise cosine similarity of update directions.
        norms = np.linalg.norm(deltas, axis=1, keepdims=True) + 1e-12
        unit = deltas / norms
        cos = np.clip(unit @ unit.T, -1.0, 1.0)

        if self.method == "clique":
            keep_mask, info = self._clique_keep(cos, n, server_round)
        elif self.method == "cluster":
            keep_mask, info = self._cluster_keep(cos, n)
        else:
            keep_mask, info = self._meansim_keep(cos, n, server_round)

        # Safety floor: never drop more than (1 - min_keep_fraction); if we would,
        # keep the highest-agreement clients instead.
        min_keep = max(1, int(np.ceil(self.min_keep_fraction * n)))
        if keep_mask.sum() < min_keep:
            mean_sim = (cos.sum(axis=1) - np.diag(cos)) / max(n - 1, 1)
            keep_idx = np.argsort(mean_sim)[::-1][:min_keep]
            keep_mask = np.zeros(n, dtype=bool)
            keep_mask[keep_idx] = True

        self.last_flagged_cids = [cids[i] for i in range(n) if not keep_mask[i]]

        kept = [updates[i] for i in range(n) if keep_mask[i]]
        agg = self.weighted_average([u[1] for u in kept], [u[2] for u in kept])
        info["gradcos_kept"] = int(keep_mask.sum())
        return self.pack(agg, info)

    # ---- v3: collusion-clique detection (convergence-regime signal) ----------
    def _clique_keep(self, cos: np.ndarray, n: int, rnd: int):
        """Flag the colluding clique. Near convergence, honest gradients shrink to
        noise and point in diverse directions (each client's MAX similarity to any
        peer is low), while colluding attackers keep injecting the SAME backdoor
        direction -> each has a near-twin (high max-similarity). So flag clients
        whose top peer-similarity is an outlier above the cohort.

        - A homogeneity gate keeps everyone when most clients have a twin (early
          training / IID cohorts where all updates align) -> protects clean acc.
        - Falls back to the v1 mean-similarity outlier test when no clique is found
          (e.g. an isolated attacker), so low-malicious detection is preserved.
        """
        if n < 4:
            return np.ones(n, dtype=bool), {"gradcos_method": "clique"}
        c = cos.copy()
        np.fill_diagonal(c, -np.inf)
        top1 = c.max(axis=1)                      # each client's nearest-peer similarity
        med = float(np.median(top1))
        mad = float(np.median(np.abs(top1 - med))) + 1e-9
        thr = med + self.separation_k * 1.4826 * mad
        flag = top1 > thr

        max_flag = int(n * (1 - self.min_keep_fraction))   # benign-majority cap
        if flag.sum() == 0 or flag.sum() > max_flag:
            # no distinct clique, or too many "twins" (homogeneous cohort) ->
            # defer to the mean-similarity outlier detector.
            keep, info = self._meansim_keep(cos, n, rnd)
            info["gradcos_method"] = "clique->meansim"
            return keep, info
        return ~flag, {"gradcos_method": "clique", "gradcos_thr": float(thr),
                       "gradcos_clique": int(flag.sum())}

    # ---- v2: collusion-robust cluster-majority -------------------------------
    def _cluster_keep(self, cos: np.ndarray, n: int):
        """Keep the largest cosine-space cluster (benign majority); flag the rest.

        A separation gate prevents flagging when no group is meaningfully
        distinct, so clean rounds keep everyone (no false positives)."""
        if n < 4:
            return np.ones(n, dtype=bool), {"gradcos_method": "cluster", "gradcos_sep": 0.0}

        dist = (1.0 - cos).astype(np.float64)
        np.fill_diagonal(dist, 0.0)
        labels = self._agglomerative_2(dist, n)

        vals, counts = np.unique(labels, return_counts=True)
        majority = vals[np.argmax(counts)]
        maj = labels == majority
        minority = ~maj

        # Separation gate: only trust the split if the minority sits clearly
        # farther from the majority than the majority's own internal spread.
        if minority.sum() == 0 or maj.sum() == 0:
            return np.ones(n, dtype=bool), {"gradcos_method": "cluster", "gradcos_sep": 0.0}
        intra = dist[np.ix_(maj, maj)]
        intra_mean = intra[np.triu_indices(maj.sum(), k=1)].mean() if maj.sum() > 1 else 0.0
        intra_std = intra[np.triu_indices(maj.sum(), k=1)].std() if maj.sum() > 1 else 0.0
        inter_mean = dist[np.ix_(minority, maj)].mean()
        # separation in units of majority's internal-distance spread
        sep = (inter_mean - intra_mean) / (intra_std + 1e-6)

        keep_mask = maj.copy()
        if sep < self.separation_k:           # no convincing outlier group
            keep_mask = np.ones(n, dtype=bool)
        return keep_mask, {"gradcos_method": "cluster", "gradcos_sep": float(sep),
                           "gradcos_minority": int(minority.sum())}

    @staticmethod
    def _agglomerative_2(dist: np.ndarray, n: int) -> np.ndarray:
        """2-cluster agglomerative labels on a precomputed distance matrix."""
        from sklearn.cluster import AgglomerativeClustering
        for kw in ({"metric": "precomputed"}, {"affinity": "precomputed"}):
            try:
                return AgglomerativeClustering(
                    n_clusters=2, linkage="average", **kw
                ).fit_predict(dist)
            except TypeError:
                continue
        # Fallback: split by median of mean-distance if sklearn API mismatches.
        md = dist.mean(axis=1)
        return (md > np.median(md)).astype(int)

    # ---- v1: mean-similarity adaptive threshold (kept for comparison) --------
    def _meansim_keep(self, cos: np.ndarray, n: int, rnd: int):
        c = cos.copy()
        np.fill_diagonal(c, 0.0)
        mean_sim = c.sum(axis=1) / max(n - 1, 1)
        thr = self._threshold(mean_sim, rnd)
        keep_mask = mean_sim >= thr
        return keep_mask, {"gradcos_method": "meansim", "gradcos_threshold": float(thr),
                           "gradcos_mean_sim": float(mean_sim.mean())}

    def _threshold(self, mean_sim: np.ndarray, rnd: int) -> float:
        """Fixed threshold, or an adaptive one from the cohort's own spread.

        Adaptive: flag clients whose mean similarity is a robust-z below the
        median (median - k * MAD). Auto-calibrates as the model converges."""
        if not self.adaptive:
            return self.threshold
        med = float(np.median(mean_sim))
        mad = float(np.median(np.abs(mean_sim - med))) + 1e-9
        data_driven = med - 1.5 * 1.4826 * mad
        return max(self.threshold * 0.0, min(data_driven, med))
