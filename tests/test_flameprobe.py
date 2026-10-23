"""Iteration 29: the FLAME mechanism probe's macro generator (paper/make_numbers_flameprobe.py)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "paper"))
import make_numbers_flameprobe as fp  # noqa: E402


def _row(rnd, adm_full, adm_tr, mh=0.9, hh=0.99):
    mal = [False, False, True, True, False, False]
    side = lambda adm, a, b: {"hh": b, "mh": a, "mm": 1.0, "admitted": adm, "typicality": [0] * 6}
    return {"round": rnd, "mal": mal, "buf_share": [0.9, 0.9, 0.99, 0.99, 0.9, 0.9],
            "counter": [16, 16, 240, 240, 16, 16], "tr_norm": [1] * 6,
            "full": side(adm_full, mh, hh), "trainable": side(adm_tr, 0.2, 0.5)}


def test_admission_counts(tmp_path, monkeypatch):
    src, out = tmp_path / "p.jsonl", tmp_path / "n.tex"
    rows = [_row(r, [0, 1, 4, 5] if r < 3 else [2, 3, 4, 5], [0, 1, 4, 5]) for r in range(1, 8)]
    src.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(fp, "SRC", str(src))
    monkeypatch.setattr(fp, "OUT", str(out))
    fp.main()
    tex = out.read_text()
    assert "\\providecommand{\\fpFirstAdmit}{3}" in tex
    assert "\\providecommand{\\fpFullAdmitRounds}{5}" in tex
    assert "\\providecommand{\\fpTrAdmitRounds}{0}" in tex
    assert "\\providecommand{\\fpRounds}{7}" in tex


def test_missing_input_is_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(fp, "SRC", str(tmp_path / "absent.jsonl"))
    monkeypatch.setattr(fp, "OUT", str(tmp_path / "n.tex"))
    fp.main()
    assert "\\PENDING" in (tmp_path / "n.tex").read_text()
