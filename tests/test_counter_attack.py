"""Unit tests for the R1 attacker (src/attacks/counter.py) and the defense rules it
targets. Run: python3 -m pytest -q tests/  (no data needed; CPU only)."""
from __future__ import annotations

import numpy as np
import pytest

from src.attacks import counter as ca
from src.defenses.krum import Krum
from flwr.common import Code, FitRes, Status, ndarrays_to_parameters


def _vec(rest, counter):
    v = np.concatenate([np.asarray(rest, float), [float(counter)]])
    cm = np.zeros(v.size, bool); cm[-1] = True
    tm = ~cm
    return v, cm, tm


def test_share_increment_hits_target_share():
    rng = np.random.RandomState(0)
    for q in (0.1, 0.5, 0.9):
        d, cm, _ = _vec(rng.randn(1000) * 0.01, 7)
        out = ca.falsify_counter(d, cm, "share", q=q)
        assert out[cm][0] >= 1 and float(out[cm][0]).is_integer()
        # rounding to an integer moves the share by little when c >> 1
        if out[cm][0] > 20:
            assert abs(ca.counter_share(out, cm) - q) < 0.02
        assert np.array_equal(out[~cm], d[~cm])


def test_share_increment_floor_is_one():
    d, cm, _ = _vec(np.full(10, 1e-6), 3)
    assert ca.share_increment(d, cm, 0.5) == 1


def test_median_policy_uses_honest_median():
    hon = [_vec(np.zeros(4), c)[0] for c in (10, 30, 20, 50, 40)]
    d, cm, _ = _vec(np.ones(4), 450)
    out = ca.falsify_counter(d, cm, "median", honest_deltas=hon)
    assert out[cm][0] == 30.0


def test_honest_policy_is_identity_and_bad_policy_raises():
    d, cm, _ = _vec(np.ones(4), 5)
    assert ca.falsify_counter(d, cm, "honest") is d
    with pytest.raises(ValueError):
        ca.falsify_counter(d, cm, "bogus")


def test_norm_bound_shrinks_only_trainables_and_never_enlarges():
    d, cm, tm = _vec([3.0, 4.0], 99)           # trainable norm 5
    out, f = ca.apply_norm_bound(d, tm, target=1.0, b=2.0)
    assert np.isclose(np.linalg.norm(out[tm]), 2.0) and np.isclose(f, 0.4)
    assert out[cm][0] == 99                     # counter untouched by the bound
    same, f1 = ca.apply_norm_bound(d, tm, target=10.0, b=1.0)
    assert same is d and f1 == 1.0
    off, f0 = ca.apply_norm_bound(d, tm, target=1.0, b=0.0)
    assert off is d and f0 == 1.0


def _fr(vec, cid, mal):
    return (None, FitRes(status=Status(Code.OK, ""),
                         parameters=ndarrays_to_parameters([vec.astype(np.float32)]),
                         num_examples=100, metrics={"cid": cid, "malicious": int(mal)}))


def test_krum_full_vector_is_ruled_by_counter_median_policy_buys_selection():
    """Cor. 2 in miniature: with heterogeneous honest counters and a full-vector Krum,
    an attacker whose trainable block is far off but whose counter is the honest
    median wins single Krum; with the counter masked out it loses."""
    rng = np.random.RandomState(1)
    counts = [20, 40, 60, 80, 100, 120, 140, 160]
    hon = [np.concatenate([rng.randn(50) * 0.01, [c]]) for c in counts]
    mal = np.concatenate([np.full(50, 0.5), [np.median(counts)]])
    res = [_fr(v, i, False) for i, v in enumerate(hon)] + [_fr(mal, 99, True)]
    full = Krum(num_malicious=1, multi=False)
    full.set_signal_mask(None)
    full.aggregate_fit(1, res, [])
    assert 99 not in full.last_flagged_cids     # attacker selected under the defect
    tm = np.ones(51, bool); tm[-1] = False
    fixed = Krum(num_malicious=1, multi=False)
    fixed.set_signal_mask(tm)
    fixed.aggregate_fit(1, res, [])
    assert 99 in fixed.last_flagged_cids        # and rejected under the fix
