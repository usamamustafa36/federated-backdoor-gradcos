"""Iteration 28: the P3X pooled sign-flip test (paper/analyse_p3x.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "paper"))
from analyse_p3x import CELLS, N_REGISTERED, signflip_p  # noqa: E402


def test_signflip_exact():
    assert signflip_p([1, 1, 1]) == 1 / 8
    assert signflip_p([1, -1]) == 0.75
    assert signflip_p([0, 0]) == 1.0
    assert abs(signflip_p([0.5, 0.5, 0.0, 0.5]) - 1 / 8) < 1e-12  # zeros dropped


def test_registered_cells():
    assert N_REGISTERED == 19
    assert [c[4] for c in CELLS] == [1, 1, -1, -1]


def _write_cell(res, mode, part, rule, seed, dr):
    import json
    import p3x_blind
    h = {k: [dr] * 15 for k in ("detection_rate",)}
    h.update({"false_positive_rate": [0.0] * 15, "bsr": [0.1] * 15, "accuracy": [0.7] * 15})
    with open(p3x_blind.cell_path(res, mode, part, rule, seed), "w") as f:
        json.dump({"history": h}, f)


def test_blinded_until_complete_then_scored(tmp_path):
    """Iteration 32 (Amendment 1): no outcome macro before all 19 pairs; scored after."""
    import subprocess
    res, out = str(tmp_path), str(tmp_path / "n.tex")
    script = os.path.join(os.path.dirname(__file__), "..", "paper", "analyse_p3x.py")
    cells = [(r, p, s, sg) for _, r, p, ss, sg in CELLS for s in ss]
    for r, p, s, sg in cells[:-1]:  # one pair short
        _write_cell(res, "full", p, r, s, 0.5 - 0.4 * sg)
        _write_cell(res, "trainable", p, r, s, 0.5 + 0.4 * sg)
    subprocess.run([sys.executable, script, "--res", res, "--out", out], check=True)
    txt = open(out).read()
    assert r"\pxXOneP}{\PENDING}" in txt and r"\pxFinal}{blinded}" in txt
    assert r"\pxXOneN}{18}" in txt and "0.90" not in txt
    r, p, s, sg = cells[-1]
    _write_cell(res, "full", p, r, s, 0.5 - 0.4 * sg)
    _write_cell(res, "trainable", p, r, s, 0.5 + 0.4 * sg)
    subprocess.run([sys.executable, script, "--res", res, "--out", out], check=True)
    txt = open(out).read()
    assert r"\pxFinal}{final}" in txt and r"\pxXOneSup}{supported}" in txt
    assert r"\pxXOneN}{19}" in txt


def test_postfix_skips_held_out_while_blinded(tmp_path):
    import p3x_blind
    assert p3x_blind.is_held_out("fldetector", "dirichlet", True, 47)
    assert not p3x_blind.is_held_out("fldetector", "dirichlet", False, 47)  # clean cells are not held out
    assert not p3x_blind.is_held_out("alignins", "iid", True, 42)  # excluded from the test, not held out
    assert not p3x_blind.unblinded(str(tmp_path))
