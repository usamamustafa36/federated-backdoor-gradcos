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
