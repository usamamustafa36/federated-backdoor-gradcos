"""Iteration 31: the registered K1 analysis (iterations/PREREG_K1.md) on synthetic cells."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "paper"))
import analyse_k1 as k1  # noqa: E402


def _hist(dr, nr=5.0, share=0.996, mm=0.99, hh=0.999, rounds=15):
    return {"history": {"detection_rate": [dr] * rounds, "false_positive_rate": [0.0] * rounds,
                        "bsr": [0.1] * rounds, "accuracy": [0.7] * rounds,
                        "mal_norm_ratio": [nr] * rounds, "buffer_norm_share": [share] * rounds,
                        "mal_pair_cos": [mm] * rounds, "honest_pair_cos": [hh] * rounds}}


def _write(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)


def _baseline(p3):
    # k < 1 as observed: FLAME defect 0 / fixed 0.86, FoolsGold defect 1 / fixed 0
    for s in k1.SEEDS:
        _write(k1.p3_path(p3, "full", "flame", s), _hist(0.0))
        _write(k1.p3_path(p3, "trainable", "flame", s), _hist(0.86))
        _write(k1.p3_path(p3, "full", "foolsgold", s), _hist(1.0))
        _write(k1.p3_path(p3, "trainable", "foolsgold", s), _hist(0.0))


def test_signflip_and_holm():
    assert k1.signflip_p([1, 1, 1]) == 1 / 8
    assert k1.signflip_p([0, 0]) == 1.0
    adj = k1.holm({"A": 0.01, "B": 0.04})
    assert abs(adj["A"] - 0.02) < 1e-12 and abs(adj["B"] - 0.04) < 1e-12


def test_khat_small_angle_is_t_over_E():
    hd, hf = _hist(0, share=0.9999)["history"], _hist(0, nr=3.0)["history"]
    assert abs(k1.khat(hd, hf, 15) - 0.2) < 1e-3


def test_predicted_reversal_is_supported(tmp_path):
    res, p3 = tmp_path / "k1", tmp_path / "p3"
    res.mkdir(); p3.mkdir()
    _baseline(str(p3))
    for X, (me, b) in k1.SETTINGS.items():
        for r in k1.RULES:
            for s in k1.SEEDS:
                dr_def = {"flame": 1.0, "foolsgold": 0.0}.get(r, 1.0)
                dr_fix = {"flame": 0.8, "foolsgold": 0.0}.get(r, 1.0)
                t = 6.0 if me == 1 else 50.0
                _write(k1.k1_path(str(res), "full", r, me, b, s), _hist(dr_def, mm=0.9, hh=0.999))
                _write(k1.k1_path(str(res), "trainable", r, me, b, s), _hist(dr_fix, nr=t, mm=0.5, hh=0.5))
    a = k1.analyse(str(res), str(p3))
    assert a["n_cells"] == k1.N_CELLS
    for X in k1.SETTINGS:
        st = a["settings"][X]
        assert st["m0"] and st["k_med"] > 1 and st["n_h1"] == 10
        assert st["p1_holm"] <= 0.05
    assert a["h2"]["n"] == 20 and a["h2"]["p"] <= 0.05   # FoolsGold ties at G = 0 carry no sign
    m = k1.macros(a)
    assert m["koAHOneSup"] == "supported" and m["koStatus"] == "final"


def test_missing_cells_are_pending(tmp_path):
    a = k1.analyse(str(tmp_path), str(tmp_path))
    m = k1.macros(a)
    assert a["n_cells"] == 0 and m["koAHOneP"] == k1.PEND and m["koMOneSup"] == k1.PEND
    assert m["koStatus"] == "interim"
