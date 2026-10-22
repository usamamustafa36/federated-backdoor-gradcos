"""Unit tests for the engine primitives the paper's claims rest on (iteration 25,
blind review item 5). No data needed; CPU only, a few seconds.
Run: python3 -m pytest -q tests/
"""
from __future__ import annotations

import numpy as np
import torch
from flwr.common import Code, FitRes, Status, ndarrays_to_parameters

from src.fl import torch_utils as tu
from src.models.cnn_lstm import CNNLSTM
from src.defenses.base import DefenseStrategy
from src.defenses.krum import Krum

torch.set_num_threads(1)


def _model(seed=0):
    torch.manual_seed(seed)
    return CNNLSTM(num_features=39, num_classes=8, conv_filters=8, lstm_hidden=8,
                   dense_hidden=8, dropout=0.0)


def _data(n, seed=0):
    rng = np.random.RandomState(seed)
    return rng.randn(n, 39).astype(np.float32), rng.randint(0, 8, n)


def _nbt(model):
    return int(model.state_dict()["conv.2.num_batches_tracked"])


def test_counter_delta_is_the_local_batch_count():
    """The counter's change over a local round is exactly B = epochs * ceil(n / bs)
    (drop_last=False), or the step budget when one is set."""
    for n, bs, ep in ((1000, 256, 1), (1000, 256, 3), (257, 256, 2)):
        m = _model(); x, y = _data(n)
        before = _nbt(m)
        tu.local_train(m, x, y, epochs=ep, lr=1e-3, batch_size=bs, device="cpu")
        assert _nbt(m) - before == ep * int(np.ceil(n / bs))
    m = _model(); x, y = _data(300)
    tu.local_train(m, x, y, epochs=99, lr=1e-3, batch_size=64, device="cpu", steps=7)
    assert _nbt(m) == 7


def test_counter_is_inert_under_default_momentum():
    """With momentum=0.1 (PyTorch's default) BatchNorm never reads the counter:
    outputs and running-statistic updates are identical whatever its value."""
    x = torch.from_numpy(_data(64)[0])
    outs, stats = [], []
    for c in (0, 7, 10**6):
        m = _model(1)
        sd = m.state_dict(); sd["conv.2.num_batches_tracked"].fill_(c)
        m.load_state_dict(sd)
        m.eval(); outs.append(m(x).detach())
        m.train(); m(x)                       # one train-mode pass updates stats
        stats.append(m.conv[2].running_mean.detach().clone())
    for o, s in zip(outs[1:], stats[1:]):
        assert torch.equal(o, outs[0]) and torch.equal(s, stats[0])


def test_counter_is_read_when_momentum_is_none():
    """The documented exception: momentum=None uses a cumulative average, 1/count."""
    bn = torch.nn.BatchNorm1d(4, momentum=None)
    x = torch.randn(32, 4)
    bn.train(); bn(x); a = bn.running_mean.clone()
    bn2 = torch.nn.BatchNorm1d(4, momentum=None)
    bn2.num_batches_tracked.fill_(9)
    bn2.train(); bn2(x); b = bn2.running_mean.clone()
    assert not torch.allclose(a, b)


def test_trainable_mask_marks_exactly_the_parameters():
    m = _model()
    mask = DefenseStrategy.trainable_flat_mask(m)
    flat = DefenseStrategy.flatten(tu.get_weights(m))
    assert mask.size == flat.size
    n_par = sum(p.numel() for p in m.parameters())
    assert int(mask.sum()) == n_par
    # one BatchNorm layer: running_mean + running_var (C each) + one counter
    assert int((~mask).sum()) == 2 * 8 + 1
    # the counter's flat position is a buffer coordinate
    keys = list(m.state_dict().keys())
    off = sum(int(np.asarray(v).size) for v in tu.get_weights(m)[:keys.index("conv.2.num_batches_tracked")])
    assert not mask[off]


def test_get_weights_aliases_storage_and_copy_decouples():
    """Documents the round-one aliasing defect (supplement Sec. S-IV) and its fix:
    get_weights returns views of the model's storage; a copy does not move."""
    m = _model(); x, y = _data(256)
    view = tu.get_weights(m)
    copy = [np.array(w, copy=True) for w in view]
    tu.local_train(m, x, y, epochs=1, lr=1e-2, batch_size=64, device="cpu")
    moved = [not np.array_equal(v, c) for v, c in zip(view, copy)]
    assert any(moved)                      # the "stored" global changed in place
    fresh = tu.get_weights(m)
    assert all(np.array_equal(v, f) for v, f in zip(view, fresh))


def test_set_get_roundtrip_is_exact():
    a, b = _model(0), _model(5)
    tu.set_weights(b, tu.get_weights(a))
    for wa, wb in zip(tu.get_weights(a), tu.get_weights(b)):
        assert np.array_equal(wa, wb)


def test_distance_decomposition_counter_term_is_L_times_dB_squared():
    """Prop. 1 for distances: with equal running statistics, the full squared
    distance is the trainable one plus L (B_i - B_j)^2 (L = 1 here)."""
    g = _model(0); x, y = _data(1200)
    g0 = DefenseStrategy.flatten(tu.get_weights(g)).astype(np.float64)
    mask = DefenseStrategy.trainable_flat_mask(g)
    deltas, B = [], []
    for n in (300, 1200):
        m = _model(0); tu.local_train(m, x[:n], y[:n], epochs=1, lr=1e-3,
                                      batch_size=100, device="cpu")
        deltas.append(DefenseStrategy.flatten(tu.get_weights(m)).astype(np.float64) - g0)
        B.append(int(np.ceil(n / 100)))
    d = deltas[0] - deltas[1]
    full = float(d @ d)
    train = float(d[mask] @ d[mask])
    buf = float(d[~mask] @ d[~mask])
    assert np.isclose(full, train + buf, rtol=1e-12)
    # the counter coordinate contributes exactly (B_i - B_j)^2
    keys = list(g.state_dict().keys())
    off = sum(int(np.asarray(v).size) for v in tu.get_weights(g)[:keys.index("conv.2.num_batches_tracked")])
    assert d[off] ** 2 == (B[0] - B[1]) ** 2


def _fr(vec, cid):
    return (None, FitRes(status=Status(Code.OK, ""),
                         parameters=ndarrays_to_parameters([vec.astype(np.float32)]),
                         num_examples=100, metrics={"cid": cid, "malicious": 0}))


def test_krum_arms_agree_iff_counters_equal():
    """Cor. 2: an identical counter cancels in every pairwise distance, so the
    full-vector and trainable-only Krum select the same client; unequal counters
    can change the selection."""
    rng = np.random.RandomState(3)
    tr = [rng.randn(40) * s for s in (0.01, 0.012, 0.011, 0.05, 0.013, 0.01)]
    tm = np.ones(41, bool); tm[-1] = False

    def chosen(counts, mask):
        k = Krum(num_malicious=1, multi=False)
        k.set_signal_mask(mask)
        res = [_fr(np.concatenate([t, [c]]), i) for i, (t, c) in enumerate(zip(tr, counts))]
        k.aggregate_fit(1, res, [])
        return sorted(set(range(6)) - set(k.last_flagged_cids))

    eq = [16] * 6
    assert chosen(eq, None) == chosen(eq, tm)
    uneq = [5, 40, 9, 22, 60, 13]               # the off-direction client 3 has the median-ish count
    assert chosen(uneq, None) != chosen(uneq, tm)
