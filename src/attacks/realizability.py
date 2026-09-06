"""Is a trigger-stamped flow a flow that could actually exist?

The threat model claims the statistical and temporal triggers are stealthy
because they are "in-distribution", and the evidence offered for that is
marginal: every stamped feature sits about 1.5-2 sigma from its own mean, and the
clean model's BSR on the pattern is near zero. Neither check is sufficient. Flow
features are jointly constrained -- rate, duration, total size, packet count and
inter-arrival times are functions of one another -- so a vector whose every
coordinate is individually ordinary can still be a combination the network could
never produce. A trigger that is not realizable as traffic weakens the threat
model, because a defender could reject it at the feature-validation stage before
any aggregation rule is involved (the problem-space point made by Pierazzi et
al.).

This module measures realizability instead of asserting it, on four axes:

  marginal      per-feature |sigma| of the stamped values -- what was reported
                before, kept for comparison.
  mahalanobis   joint distance of the stamped sub-vector under the benign
                covariance restricted to the trigger columns, reported as a
                percentile of the same statistic computed on real benign flows.
                A trigger at the 99.9th percentile is jointly extreme even when
                every marginal is unremarkable.
  knn           distance from the stamped sub-vector to its nearest real flow,
                in units of the typical nearest-neighbour distance between real
                flows. Roughly 1 means the pattern sits where real traffic sits.
  stamped_knn   the same nearest-real-flow distance computed over ALL features
                for fully stamped attack flows, against the same statistic for
                the unstamped originals. This is the end-to-end question: does
                stamping move an attack flow off the data manifold?

Everything is computed in normalized feature space on a subsample, and travels
with each result file via ``trigger_report``.
"""
from __future__ import annotations

import numpy as np

_MAX_ROWS = 20000     # subsample cap: these are diagnostics, not the experiment
_KNN_QUERY = 2000
_REF_ROWS = 8000      # reference pool of real flows for nearest-neighbour work


def _rng():
    return np.random.RandomState(20260827)


def _subsample_idx(n_rows: int, n: int) -> np.ndarray:
    if n_rows <= n:
        return np.arange(n_rows)
    return _rng().choice(n_rows, size=n, replace=False)


def _subsample(x: np.ndarray, n: int) -> np.ndarray:
    return x[_subsample_idx(len(x), n)]


def _mahalanobis(points: np.ndarray, mu: np.ndarray, prec: np.ndarray) -> np.ndarray:
    d = points - mu
    return np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", d, prec, d), 0.0))


def _nn_dist(queries: np.ndarray, reference: np.ndarray, exclude_self: bool) -> np.ndarray:
    """Distance from each query row to its nearest row in ``reference``."""
    out = np.empty(len(queries))
    step = 256
    for i in range(0, len(queries), step):
        q = queries[i:i + step]
        d = np.linalg.norm(q[:, None, :] - reference[None, :, :], axis=2)
        if exclude_self:
            # queries are drawn from reference, so the zero self-match must go
            np.put_along_axis(d, np.argmin(d, axis=1)[:, None], np.inf, axis=1)
        out[i:i + step] = d.min(axis=1)
    return out


def realizability_stats(trigger, dataset) -> dict:
    """Joint-plausibility summary for ``trigger`` against ``dataset``."""
    cols = trigger.columns
    vals = np.asarray(trigger.values, dtype=np.float64)
    x, y = dataset.x_train, dataset.y_train
    benign_index = dataset.benign_index

    benign = _subsample(x[y == benign_index][:, cols].astype(np.float64), _MAX_ROWS)
    if len(benign) < 8:
        return {"error": "too few benign rows for a realizability check"}

    # ---- joint Mahalanobis, as a percentile of real benign flows -------------
    mu = benign.mean(axis=0)
    cov = np.atleast_2d(np.cov(benign, rowvar=False)) + 1e-6 * np.eye(len(cols))
    try:
        prec = np.linalg.inv(cov)
    except np.linalg.LinAlgError:
        prec = np.linalg.pinv(cov)

    ref_m = _mahalanobis(benign, mu, prec)
    trig_m = float(_mahalanobis(vals[None, :], mu, prec)[0])
    pct = float((ref_m < trig_m).mean() * 100.0)

    # ---- nearest real flow, on the trigger columns --------------------------
    q = _subsample(benign, _KNN_QUERY)
    typical_nn = float(np.median(_nn_dist(q, benign, exclude_self=True)))
    trig_nn = float(_nn_dist(vals[None, :], benign, exclude_self=False)[0])

    # ---- end-to-end: does stamping push an attack flow off the manifold? ----
    # One reference set of real flows, with the query rows drawn FROM it, so the
    # unstamped baseline is a genuine "nearest other real flow" distance and the
    # two numbers are measured against the same reference.
    ref_idx = _subsample_idx(len(x), _REF_ROWS)
    real_full = x[ref_idx].astype(np.float64)
    is_attack = y[ref_idx] != benign_index
    attack_rows = real_full[is_attack][:_KNN_QUERY]
    if len(attack_rows) == 0:
        plain_nn = stamped_nn = float("nan")
    else:
        stamped = attack_rows.copy()
        stamped[:, cols] = vals
        plain_nn = float(np.median(_nn_dist(attack_rows, real_full, exclude_self=True)))
        stamped_nn = float(np.median(_nn_dist(stamped, real_full, exclude_self=False)))

    return {
        "marginal_abs_sigma_max": float(np.max(np.abs(vals))),
        "marginal_abs_sigma_mean": float(np.mean(np.abs(vals))),
        "joint_mahalanobis": trig_m,
        "joint_mahalanobis_pctile_vs_benign": pct,
        "benign_mahalanobis_p50": float(np.median(ref_m)),
        "benign_mahalanobis_p99": float(np.percentile(ref_m, 99)),
        "nn_dist_trigger_block": trig_nn,
        "nn_dist_typical_block": typical_nn,
        # >> 1 means the stamped block sits far from anything real
        "nn_ratio_block": float(trig_nn / (typical_nn + 1e-12)),
        "nn_dist_stamped_full": stamped_nn,
        "nn_dist_unstamped_full": plain_nn,
        "nn_ratio_full": float(stamped_nn / (plain_nn + 1e-12)),
        "n_trigger_features": int(len(cols)),
    }
