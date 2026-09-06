"""Order-statistic and magnitude-based aggregators.

Every defense in the rest of this package reads update *direction*: Krum scores
Euclidean neighbourhoods, FLAME/FoolsGold/GradCos read pairwise cosine. That
shared reliance is the blind spot the paper reports, so the natural controls are
aggregators that never look at direction at all. The rules here are the standard
non-cosine robust estimators:

  * ``median``      - coordinate-wise median (Yin et al., 2018).
  * ``trimmedmean`` - coordinate-wise beta-trimmed mean (Yin et al., 2018).
  * ``rfa``         - geometric median of the updates via smoothed Weiszfeld
                      (Pillutla et al., RFA). Unlike the coordinate-wise rules
                      this is a genuine multivariate median, so it is not fooled
                      by an attacker who spreads its perturbation across
                      coordinates.
  * ``bulyan``      - Bulyan (El Mhamdi et al., 2018): iterated Multi-Krum
                      selection followed by a coordinate-wise trimmed mean over
                      the selected set, i.e. a distance filter *and* an order
                      statistic.
  * ``normclip``    - norm clipping to the median update norm plus Gaussian
                      noise (Sun et al., 2019). This is FLAME with the cosine
                      clustering removed, which isolates how much of FLAME's
                      robustness is the magnitude stage rather than the
                      direction stage.

The three purely coordinate-wise rules never single out a client, so they report
``last_flagged_cids = None`` and the engine records DR/FPR as N/A for them rather
than as zero. Bulyan does select a subset and is scored like Krum.
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class _DeltaStrategy(DefenseStrategy):
    """Shared plumbing: turn results into a (n, d) delta matrix and write back a
    single aggregated delta on top of the round's global model."""

    def _deltas(self, results):
        updates = self.extract(results)
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])
        return updates, g, deltas

    def _finish(self, g, agg_delta, info):
        return self.pack(self.unflatten(g + agg_delta, self.current_global), info)


class CoordMedian(_DeltaStrategy):
    def __init__(self):
        super().__init__()
        self.last_flagged_cids = None      # no per-client decision to score

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        _, g, deltas = self._deltas(results)
        return self._finish(g, np.median(deltas, axis=0), {"median_n": len(deltas)})


class TrimmedMean(_DeltaStrategy):
    """Coordinate-wise trimmed mean: drop the ``beta`` largest and ``beta``
    smallest values in every coordinate, average what is left. ``beta`` must
    exceed the number of attackers for the guarantee to hold, so it is clamped to
    what the cohort supports."""

    def __init__(self, beta: float = 0.2):
        super().__init__()
        self.beta = beta
        self.last_flagged_cids = None

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        _, g, deltas = self._deltas(results)
        n = len(deltas)
        k = int(np.floor(self.beta * n))
        k = max(0, min(k, (n - 1) // 2))
        if k == 0:
            agg = deltas.mean(axis=0)
        else:
            srt = np.sort(deltas, axis=0)
            agg = srt[k:n - k].mean(axis=0)
        return self._finish(g, agg, {"trim_k": k, "trim_n": n})


class GeometricMedian(_DeltaStrategy):
    """RFA: the geometric (spatial) median of the client updates, computed with
    the smoothed Weiszfeld iteration
        w_i = 1 / max(nu, ||delta_i - z||),  z <- sum_i w_i delta_i / sum_i w_i.
    A handful of iterations is enough at this cohort size."""

    def __init__(self, iters: int = 8, nu: float = 1e-6):
        super().__init__()
        self.iters = iters
        self.nu = nu
        self.last_flagged_cids = None

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates, g, deltas = self._deltas(results)
        counts = np.array([u[2] for u in updates], dtype=np.float64)
        alpha = counts / counts.sum()

        # The Weiszfeld weights come from distances measured on the trainable
        # parameters; the geometric median itself is still computed over the
        # full update so the buffers aggregate. On the raw vector the shared
        # batch counter cancels in (delta_i - z) anyway, so this mainly guards
        # against the counter dominating if the cohort ever becomes uneven.
        sig = self.sig(deltas)
        z = (deltas * alpha[:, None]).sum(axis=0)      # start from the weighted mean
        for _ in range(self.iters):
            d = np.linalg.norm(sig - self.sig(z), axis=1)
            w = alpha / np.maximum(self.nu, d)
            wsum = w.sum()
            if wsum <= 0 or not np.isfinite(wsum):
                break
            z = (deltas * (w / wsum)[:, None]).sum(axis=0)
        return self._finish(g, z, {"rfa_iters": self.iters})


class Bulyan(_DeltaStrategy):
    """Bulyan: run Multi-Krum selection ``theta = n - 2f`` times (removing the
    winner each time), then take a coordinate-wise trimmed mean over the selected
    set, keeping in each coordinate the ``theta - 2f`` values closest to that
    coordinate's median. Needs n >= 4f + 3; f is clamped down when the cohort is
    too small, and the rule degrades to Multi-Krum + median in that case."""

    def __init__(self, num_malicious: int = 4):
        super().__init__()
        self.f = num_malicious

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates, g, deltas = self._deltas(results)
        cids = [u[0] for u in updates]
        n = len(deltas)

        f = int(self.f)
        if n < 4 * f + 3:
            f = max(0, (n - 3) // 4)

        theta = max(1, n - 2 * f)
        # Selection on the trainable subspace, trimming on the full update.
        selected = self._iterated_krum(self.sig(deltas), n, f, theta)
        self.last_flagged_cids = [cids[i] for i in range(n) if i not in selected]

        sel = deltas[sorted(selected)]
        beta = max(1, theta - 2 * f)
        med = np.median(sel, axis=0)
        # keep, per coordinate, the beta entries nearest that coordinate's median
        order = np.argsort(np.abs(sel - med), axis=0)[:beta]
        agg = np.take_along_axis(sel, order, axis=0).mean(axis=0)
        return self._finish(g, agg, {"bulyan_f": f, "bulyan_theta": theta,
                                     "bulyan_beta": beta})

    @staticmethod
    def _iterated_krum(deltas: np.ndarray, n: int, f: int, theta: int) -> set[int]:
        sq = np.sum(deltas ** 2, axis=1)
        dist = sq[:, None] + sq[None, :] - 2.0 * (deltas @ deltas.T)
        dist = np.maximum(dist, 0.0)
        np.fill_diagonal(dist, np.inf)

        remaining = list(range(n))
        chosen: set[int] = set()
        while len(chosen) < theta and len(remaining) > 0:
            m = len(remaining)
            k = max(1, m - f - 2)
            sub = dist[np.ix_(remaining, remaining)]
            scores = np.sort(sub, axis=1)[:, :k].sum(axis=1)
            winner = remaining[int(np.argmin(scores))]
            chosen.add(winner)
            remaining.remove(winner)
        return chosen


class NormClip(_DeltaStrategy):
    """Norm clipping to the median update norm, plus Gaussian noise -- FLAME's
    magnitude stage without its cosine clustering stage. ``noise_mask`` keeps the
    noise off BatchNorm buffers for the same reason FLAME needs it (noised
    ``running_var`` can go negative and make eval-mode BN produce NaNs)."""

    def __init__(self, noise_lambda: float = 0.001, seed: int = 42,
                 noise_mask: np.ndarray | None = None):
        super().__init__()
        self.noise_lambda = noise_lambda
        self.rng = np.random.RandomState(seed)
        self.noise_mask = noise_mask
        self.last_flagged_cids = None

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates, g, deltas = self._deltas(results)
        # Norms on the trainable parameters. Over the raw vector ||delta|| is
        # ~98% batch counter, so a client could inflate its real update tenfold
        # and move this norm by under 1% -- clipping to the median norm
        # constrained nothing, and sigma = lambda * S was ~10x too large.
        norms = np.linalg.norm(self.sig(deltas), axis=1) + 1e-12
        S = float(np.median(norms))
        scale = np.minimum(1.0, S / norms)
        clipped = deltas * scale[:, None]

        w = np.array([u[2] for u in updates], dtype=np.float64)
        w = w / w.sum()
        agg = (clipped * w[:, None]).sum(axis=0)

        sigma = self.noise_lambda * S
        if sigma > 0:
            noise = self.rng.normal(0.0, sigma, size=agg.shape)
            if self.noise_mask is not None:
                noise = noise * self.noise_mask
            agg = agg + noise
        return self._finish(g, agg, {"normclip_S": S})
