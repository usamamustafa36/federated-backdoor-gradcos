"""FLDetector (Zhang, Cao, Jia and Gong, KDD 2022).

Included for two reasons. It is the most recent defense this paper evaluates,
which matters because the bibliography cites work through 2025 and the
manuscript otherwise stops at FLAME (2022). And it sits **outside** the
direction/magnitude split the paper is organised around: FLDetector scores a
client on how *consistent* its updates are across rounds, not on where a single
update points or how large it is. The Discussion already concedes that its
two-family taxonomy is not exhaustive and names this paper; evaluating it turns
that concession into evidence.

Method. The server keeps the recent global models and each client's recent
updates. Assuming the loss is smooth, a client's update at round t should be
predictable from the previous one via the Cauchy mean value theorem,

    g_i^t  ~=  g_i^{t-1} + H^{t-1} (w^t - w^{t-1}),

with the Hessian approximated by L-BFGS from the stored (model, update)
differences. A client whose actual update departs from that prediction is
behaving inconsistently over time. The per-client suspicious score is the
normalised prediction error averaged over a window, and clients are split into
two groups by k-means on that score; the higher-error group is flagged, but only
when the split is real -- a Gap-statistic-style check keeps everyone when the
scores form a single cluster, so clean rounds cost no false positives.

Deliberate simplification: the reference implementation re-initialises the
global model when it detects attackers. We only flag and exclude, so that the
comparison against every other defense here is like for like -- all of them are
scored on which clients they keep.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class FLDetector(DefenseStrategy):
    def __init__(self, window: int = 10, lbfgs_pairs: int = 5,
                 min_rounds: int = 3, gap_ratio: float = 2.0):
        super().__init__()
        self.window = window                # rounds of scores to average
        self.lbfgs_pairs = lbfgs_pairs      # curvature pairs kept for L-BFGS
        self.min_rounds = min_rounds        # rounds before scoring can start
        self.gap_ratio = gap_ratio          # separation needed to call a split real
        self.prev_global: np.ndarray | None = None
        self.prev_mean: np.ndarray | None = None
        self.prev_updates: dict[int, np.ndarray] = {}
        self.dw: list[np.ndarray] = []      # global-model differences
        self.dg: list[np.ndarray] = []      # mean-update differences
        self.scores: dict[int, list[float]] = {}

    # ---- L-BFGS Hessian-vector product (two-loop recursion) --------------
    def _hv(self, v: np.ndarray) -> np.ndarray:
        """Approximate H @ v from the stored curvature pairs. Falls back to the
        zero map before enough history exists, which makes the predictor
        'the update does not change', a reasonable prior for early rounds."""
        if not self.dw:
            return np.zeros_like(v)
        q = v.copy()
        alphas, rhos = [], []
        for s, y in zip(reversed(self.dw), reversed(self.dg)):
            denom = float(np.dot(y, s))
            if abs(denom) < 1e-12:
                alphas.append(0.0); rhos.append(0.0); continue
            rho = 1.0 / denom
            a = rho * float(np.dot(s, q))
            q = q - a * y
            alphas.append(a); rhos.append(rho)
        s_last, y_last = self.dw[-1], self.dg[-1]
        yy = float(np.dot(y_last, y_last))
        gamma = float(np.dot(s_last, y_last)) / yy if yy > 1e-12 else 1.0
        r = gamma * q
        for (s, y), a, rho in zip(zip(self.dw, self.dg), reversed(alphas), reversed(rhos)):
            if rho == 0.0:
                continue
            b = rho * float(np.dot(y, r))
            r = r + s * (a - b)
        return r

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = {u[0]: self.sig(self.flatten(u[1]) - g) for u in updates}
        gw = self.sig(g)
        n = len(cids)

        flagged: list[int] = []
        info: dict = {"fld_round": int(server_round)}

        if self.prev_global is not None:
            dw = gw - self.prev_global
            hv = self._hv(dw)
            errs = {}
            for cid in cids:
                prev = self.prev_updates.get(cid)
                if prev is None:
                    continue
                pred = prev + hv
                errs[cid] = float(np.linalg.norm(deltas[cid] - pred))
            if errs:
                # Normalise so the scale of the update does not set the score.
                tot = sum(errs.values()) or 1.0
                for cid, e in errs.items():
                    self.scores.setdefault(cid, []).append(e / tot)
                    self.scores[cid] = self.scores[cid][-self.window:]

            ready = [c for c in cids if len(self.scores.get(c, [])) >= self.min_rounds]
            if len(ready) >= 4:
                s = np.array([float(np.mean(self.scores[c])) for c in ready])
                flagged = self._split(ready, s, info)

        # roll history forward
        mean_delta = np.mean([deltas[c] for c in cids], axis=0)
        if self.prev_global is not None and self.prev_mean is not None:
            self.dw.append(gw - self.prev_global)
            self.dg.append(mean_delta - self.prev_mean)
            self.dw = self.dw[-self.lbfgs_pairs:]
            self.dg = self.dg[-self.lbfgs_pairs:]
        self.prev_global = gw
        self.prev_mean = mean_delta
        self.prev_updates = dict(deltas)

        self.last_flagged_cids = flagged
        keep = [u for u in updates if u[0] not in set(flagged)]
        if not keep:                          # never discard the whole cohort
            keep = updates
            self.last_flagged_cids = []
        info["fld_flagged"] = len(self.last_flagged_cids)
        agg = self.weighted_average([u[1] for u in keep], [u[2] for u in keep])
        return self.pack(agg, info)

    def _split(self, ready, s, info) -> list[int]:
        """Two-means on the suspicious scores, with a gap check so a single
        cluster is left alone."""
        lo, hi = float(s.min()), float(s.max())
        if hi - lo < 1e-12:
            return []
        c0, c1 = lo, hi
        lab = np.zeros(len(s), dtype=int)
        for _ in range(25):
            lab = (np.abs(s - c1) < np.abs(s - c0)).astype(int)
            if lab.all() or not lab.any():
                return []
            c0, c1 = float(s[lab == 0].mean()), float(s[lab == 1].mean())
        within = max(float(s[lab == 0].std()), float(s[lab == 1].std()), 1e-9)
        if (c1 - c0) < self.gap_ratio * within:
            info["fld_gap"] = "single cluster — nobody flagged"
            return []
        info["fld_gap"] = float((c1 - c0) / within)
        hi_idx = [i for i, l in enumerate(lab) if l == 1]
        # benign-majority assumption: the suspicious group must be the minority
        if len(hi_idx) > len(s) / 2:
            return []
        return [ready[i] for i in hi_idx]
