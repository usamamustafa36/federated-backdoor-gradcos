"""AlignIns (Xu, Zhang and Hu, CVPR 2025): direction-alignment inspection.

Port of `agg_alignins` in the authors' code (github.com/JiiahaoXU/AlignIns,
src/aggregation.py, commit 49b7d32), onto this codebase's DefenseStrategy.
Per round, on the client update deltas d_i:

  TDA_i  = cos(d_i, theta_t)            temporal direction alignment with the
                                        current global model theta_t (not with
                                        the mean update).
  MPSA_i = fraction of the top-k |d_i| coordinates whose sign equals the
           coordinate-wise majority sign p = sgn(sum_j sgn(d_j)); k = 0.3 * dim.
  MZ(x)_i = |x_i - median(x)| / std(x)  (population std, as in the reference).

A client is kept iff MZ(TDA)_i < lambda_c and MZ(MPSA)_i < lambda_s (both 1.0).
Every update is then clipped to the median norm of the KEPT updates, and the kept
clipped updates are averaged with data-size weights. No client kept -> the
global model is left unchanged (the reference returns a zero update).

Signal subspace. TDA, MPSA, the top-k mask and the clip norm are DECISIONS and
use `self.sig(...)`; under `signal_subspace: full` they are taken over the whole
flattened state_dict, which is what the reference implementation does (it builds
both the update and theta_t with parameters_to_vector over state_dict()). Its
CIFAR-10 ResNet-9 sets track_running_stats=False (no buffers, unaffected); its
CIFAR-100 VGG-9 (nn.BatchNorm2d defaults) and Tiny-ImageNet torchvision
ResNet-18 do transmit num_batches_tracked.

What the decomposition predicts (paper Sec. "Aggregation rules"):
  * TDA is a cosine against theta_t, whose counter coordinate C_t grows every
    round while d_i's counter coordinate is the client's batch count b_i; under
    the defect TDA is compressed toward a common value and its residue tracks
    b_i / ||d_i||, i.e. shard size. The MZ-score divides by the spread, so the
    compression itself is undone; what decides is the residue.
  * MPSA is sign-based and scale-free: the counter is one coordinate whose sign
    is + for every client, so it agrees with the majority and moves MPSA by at
    most 1/k. Predicted: (almost) unaffected.
  * The post-filter clip is a norm and is counter-dominated (as for NormClip).

Deviation from the reference, stated: when std(x) == 0 the reference divides by
zero (NaN z-scores, every client rejected, zero update); here the z-scores are
set to 0 (every client passes that filter).
"""
from __future__ import annotations

import numpy as np

from .base import DefenseStrategy


class AlignIns(DefenseStrategy):
    def __init__(self, sparsity: float = 0.3, lambda_s: float = 1.0,
                 lambda_c: float = 1.0):
        super().__init__()
        self.sparsity = float(sparsity)
        self.lambda_s = float(lambda_s)
        self.lambda_c = float(lambda_c)
        self.last_scores: dict = {}

    @staticmethod
    def _mz(x: np.ndarray) -> np.ndarray:
        sd = float(np.std(x))
        if sd == 0.0 or not np.isfinite(sd):
            return np.zeros_like(x)
        return np.abs(x - np.median(x)) / sd

    def scores(self, deltas: np.ndarray, g: np.ndarray):
        """-> (tda, mpsa) over the decision subspace. deltas (n, d), g (d,)."""
        S = self.sig(deltas)
        gs = self.sig(g)
        gn = float(np.linalg.norm(gs))
        dn = np.linalg.norm(S, axis=1)
        tda = (S @ gs) / np.maximum(dn * gn, 1e-6)       # torch CosineSimilarity eps
        major = np.sign(np.sign(S).sum(axis=0))
        k = max(1, int(S.shape[1] * self.sparsity))
        mpsa = np.empty(len(S))
        for i in range(len(S)):
            idx = np.argpartition(-np.abs(S[i]), k - 1)[:k]
            mpsa[i] = float(np.mean(np.sign(S[i, idx]) == major[idx]))
        return tda, mpsa, dn

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])
        n = len(deltas)

        tda, mpsa, norms = self.scores(deltas, g)
        keep = (self._mz(mpsa) < self.lambda_s) & (self._mz(tda) < self.lambda_c)
        kept = np.where(keep)[0]
        self.last_flagged_cids = [cids[i] for i in range(n) if not keep[i]]
        self.last_scores = {"tda": tda.tolist(), "mpsa": mpsa.tolist()}
        if len(kept) == 0:
            return self.pack(self.unflatten(g, self.current_global),
                             {"alignins_kept": 0})

        clip = float(np.median(norms[kept]))
        w = np.array([updates[i][2] for i in kept], dtype=np.float64)
        w = w / w.sum()
        agg = np.zeros_like(g)
        for wi, i in zip(w, kept):
            scale = min(1.0, clip / norms[i]) if norms[i] > 0 else 1.0
            agg += wi * scale * deltas[i]
        return self.pack(self.unflatten(g + agg, self.current_global),
                         {"alignins_kept": int(len(kept)), "alignins_clip": clip})
