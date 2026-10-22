"""R1 (iterations/PREREG_R1.md): a malicious client that controls its norm and its
BatchNorm counter.

Two knobs, both applied to the flat update ``delta = w_client - w_global`` of a
malicious client after local training (and after the variant/boost transforms):

* ``apply_norm_bound``: rescale the TRAINABLE block of the update to at most
  ``b`` times the median honest trainable norm of the round (direction kept;
  buffers as trained). ``b <= 0`` means unbounded.
* ``falsify_counter``: overwrite the ``num_batches_tracked`` increment(s) with a
  value of the attacker's choice (integer, at least 1):

  - ``share``  : the counter coordinates carry the fraction ``q`` of the squared
    norm of the attacker's own full update (Corollary 4: q = 1/2 maximises the
    non-counter step FLTrust gives it under the defect). With k counter
    coordinates and R the squared norm of every other coordinate,
    k c^2 / (k c^2 + R) = q  =>  c = sqrt(q R / ((1 - q) k)).
  - ``median`` : the median honest counter increment of the round, per counter
    coordinate (so the attacker sits in the middle of the honest counters, which
    is what a distance rule reads under the defect, Corollary 2).
  - ``honest`` : leave the counter as trained (no-op).

With BatchNorm's default momentum the counter never enters the forward pass, so
the falsified value does not change the model the attacker helps train. Pure
numpy; no torch, so it is unit-testable in isolation (tests/test_counter_attack.py).
"""
from __future__ import annotations

import numpy as np

POLICIES = ("honest", "share", "median")


def counter_flat_mask(model) -> np.ndarray:
    """Flat mask over the flattened state_dict: True on num_batches_tracked."""
    parts = []
    for k, v in model.state_dict().items():
        size = int(np.asarray(v.detach().cpu().numpy()).size)
        parts.append(np.full(size, k.endswith("num_batches_tracked"), dtype=bool))
    return np.concatenate(parts)


def apply_norm_bound(delta: np.ndarray, tmask: np.ndarray, target: float,
                     b: float) -> tuple[np.ndarray, float]:
    """Shrink the trainable block of ``delta`` to norm <= b * target.

    Returns (new_delta, factor applied). Never enlarges an update."""
    if b is None or b <= 0 or target <= 0:
        return delta, 1.0
    n = float(np.linalg.norm(delta[tmask]))
    cap = float(b) * float(target)
    if n <= cap or n <= 1e-12:
        return delta, 1.0
    out = delta.copy()
    f = cap / n
    out[tmask] *= f
    return out, f


def share_increment(delta: np.ndarray, cmask: np.ndarray, q: float) -> int:
    """Counter increment c such that the k counter coordinates carry the share q
    of ||delta||^2 (others as in delta). Integer, at least 1."""
    if not 0.0 < q < 1.0:
        raise ValueError(f"counter share must be in (0, 1), got {q}")
    k = int(cmask.sum())
    if k == 0:
        return 0
    rest = float(np.dot(delta[~cmask], delta[~cmask]))
    c = np.sqrt(q * rest / ((1.0 - q) * k))
    return max(1, int(round(c)))


def median_increment(honest_deltas: list[np.ndarray], cmask: np.ndarray) -> np.ndarray:
    """Per-coordinate median of the honest counter increments (rounded, >= 1)."""
    if not honest_deltas:
        raise ValueError("median policy needs at least one honest update")
    inc = np.stack([d[cmask] for d in honest_deltas])
    return np.maximum(1, np.rint(np.median(inc, axis=0))).astype(np.float64)


def falsify_counter(delta: np.ndarray, cmask: np.ndarray, policy: str,
                    q: float = 0.5, honest_deltas: list | None = None) -> np.ndarray:
    """Return a copy of ``delta`` whose counter coordinates hold the policy's
    increment. ``honest`` returns delta unchanged."""
    policy = str(policy).lower()
    if policy not in POLICIES:
        raise ValueError(f"unknown counter policy {policy!r}; use one of {POLICIES}")
    if policy == "honest" or int(cmask.sum()) == 0:
        return delta
    out = delta.copy()
    if policy == "share":
        out[cmask] = float(share_increment(delta, cmask, q))
    else:
        out[cmask] = median_increment(honest_deltas or [], cmask)
    return out


def counter_share(delta: np.ndarray, cmask: np.ndarray) -> float:
    """Share of ||delta||^2 carried by the counter coordinates."""
    t = float(np.dot(delta, delta))
    return float(np.dot(delta[cmask], delta[cmask])) / t if t > 0 else float("nan")
