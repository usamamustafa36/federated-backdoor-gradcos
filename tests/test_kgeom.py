"""Iteration 30: the counter-angle identity (Proposition prop:angle) and its macro generator."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "paper"))
import make_numbers_kgeom as kg  # noqa: E402


def _cos(a, b):
    return float(a @ b / np.linalg.norm(a) / np.linalg.norm(b))


def test_identity_exact_on_random_updates():
    rng = np.random.default_rng(0)
    for _ in range(200):
        L = int(rng.integers(1, 6))
        e = rng.normal(size=(2, 50)) * rng.uniform(0.1, 5, size=(2, 1))
        B = rng.uniform(1, 300, size=2)
        d = [np.concatenate([e[i], B[i] * np.ones(L)]) for i in range(2)]
        th = [np.arccos(np.sqrt(L * B[i] ** 2 / (d[i] @ d[i]))) for i in range(2)]
        rhs = 1 - np.cos(th[0] - th[1]) + np.sin(th[0]) * np.sin(th[1]) * (1 - _cos(e[0], e[1]))
        assert abs((1 - _cos(d[0], d[1])) - rhs) < 1e-12


def test_k_squared_law_with_equal_angles():
    # attackers m, m' share one angle, honest h, h' another: ratio (a) is k^2 (1-rho_mm)/(1-rho_hh)
    rng = np.random.default_rng(1)
    em = rng.normal(size=(2, 40)); eh = rng.normal(size=(2, 40))
    em *= 3.0 / np.linalg.norm(em, axis=1, keepdims=True)
    eh *= 1.0 / np.linalg.norm(eh, axis=1, keepdims=True)
    Bm, Bh = 240.0, 16.0
    dm = [np.append(x, Bm) for x in em]; dh = [np.append(x, Bh) for x in eh]
    k = np.sin(np.arccos(Bm / np.linalg.norm(dm[0]))) / np.sin(np.arccos(Bh / np.linalg.norm(dh[0])))
    lhs = (1 - _cos(*dm)) / (1 - _cos(*dh))
    assert abs(lhs - k ** 2 * (1 - _cos(*em)) / (1 - _cos(*eh))) < 1e-9
    assert abs(k - (3.0 / 1.0) / (Bm / Bh)) < 0.01


def test_probe_macros_without_campaign(tmp_path, monkeypatch):
    mal = [False, False, True, True, False, False]
    rows = []
    for r, (mh, adm) in enumerate([(0.5, []), (0.4, []), (0.2, [2]), (0.2, [2, 3])], start=1):
        side = {"hh": 0.99, "mh": 0.99, "mm": 0.999, "admitted": adm}
        rows.append({"round": r, "mal": mal, "buf_share": [0.99, 0.99, 0.999, 0.999, 0.99, 0.99],
                     "counter": [15, 15, 239, 239, 15, 15], "tr_norm": [1, 1, 4, 4, 1, 1],
                     "full": side, "trainable": {"hh": 0.5 if r > 2 else 0.9, "mh": mh, "mm": 0.6}})
    src, out = tmp_path / "p.jsonl", tmp_path / "n.tex"
    src.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(kg, "PROBE", str(src))
    monkeypatch.setattr(kg, "OUT", str(out))
    monkeypatch.setattr(kg, "RES", str(tmp_path / "none"))
    monkeypatch.setattr(kg, "FIG", str(tmp_path / "f.pdf"))
    kg.main()
    tex = out.read_text()
    assert "\\providecommand{\\kgPrRounds}{3}" in tex
    assert "\\providecommand{\\kgPrAdmN}{2}" in tex
    assert "\\providecommand{\\kgIidN}{\\PENDING}" in tex
