"""Blinding guard for the P3X held-out cells (iterations/PREREG_P3X.md, Amendment 1).

Until every one of the 19 registered pairs exists (both arms, non-empty JSON, 15 rounds),
no generator may read the outcome of a held-out cell: analyse_p3x.py writes only pair
counts, and analyse_postfix.py skips the held-out (rule, partition, seed) cells so that
`make numbers` cannot unblind them through the exploratory tables. Once the set is
complete the guard lifts by itself; nothing here changes a cell, sign or test.
"""
import json
import os

# id, rule, partition, seeds, sigma -- exactly PREREG_P3X.md's table
CELLS = [
    ("h1", "fldetector", "dirichlet", range(47, 52), +1),
    ("h2", "alignins", "dirichlet", range(47, 52), +1),
    ("h3", "alignins", "iid", range(43, 47), -1),
    ("h4", "foolsgold", "iid", range(47, 52), -1),
]
N_REGISTERED = sum(len(c[3]) for c in CELLS)
HELD_OUT = {(rule, part, s) for _, rule, part, seeds, _ in CELLS for s in seeds}


def cell_path(res, mode, part, rule, seed):
    return os.path.join(res, f"p3{mode}_{part}_ciciot2023_{rule}_atk1_m0.2_p0.1_fixed"
                             f"_me15_sm_s{seed}.json")


def cell_complete(path):
    """True iff the cell finished: non-empty JSON with 15 rounds. Reads only the round count."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    try:
        return len(json.load(open(path))["history"]["accuracy"]) >= 15
    except (json.JSONDecodeError, OSError, KeyError):
        return False


def pairs_present(res):
    """Number of registered pairs whose two arms are both complete."""
    return sum(all(cell_complete(cell_path(res, m, part, rule, s)) for m in ("full", "trainable"))
               for _, rule, part, seeds, _ in CELLS for s in seeds)


def unblinded(res):
    return pairs_present(res) == N_REGISTERED


def is_held_out(rule, part, attack, seed):
    return bool(attack) and (rule, part, int(seed)) in HELD_OUT
