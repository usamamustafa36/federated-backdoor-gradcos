#!/usr/bin/env python3
"""Figure: what the server's rules see, per round, in the P1 runs (iteration 3).

Reads the per-round defect diagnostics that src/fl/engine.py logs in every P1
run (results/postfix_p1/*.json; both arms, every rule: the diagnostics describe
the transmitted vector, not a rule's decision) and plots, per partition,
  left : median over runs of the mean pairwise client cosine, full transmitted
         vector vs trainable coordinates only;
  right: median over runs of the buffer share of the squared update norm and of
         the pairwise squared distances.
Shaded bands are the inter-quartile range over runs.

Output: paper/figs/fig_p1_geometry.pdf. Generated; nothing typed by hand.
Usage:  python3 paper/make_fig_p1.py
"""
from __future__ import annotations

import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "postfix_p1")
OUT = os.path.join(ROOT, "paper", "figs", "fig_p1_geometry.pdf")
KEYS = ["pair_cos_full", "pair_cos_sig", "buffer_norm_share", "buffer_dist_share"]


def load():
    by_part = {}
    for path in sorted(glob.glob(os.path.join(RES, "*.json"))):
        try:
            d = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue
        h = d.get("history", {})
        if not all(k in h for k in KEYS):
            continue
        part = d["config"]["federated"]["partition"]
        by_part.setdefault(part, []).append(
            {k: np.array([np.nan if v is None else v for v in h[k]], float) for k in KEYS})
    return by_part


FIRST = 2  # round 1 omitted: its diagnostics record the round-1 aliasing defect
           # (src/fl/engine.py `copy_initial_global`, iteration 5), not the geometry.


def band(runs, key):
    R = min(len(r[key]) for r in runs)
    M = np.stack([r[key][FIRST - 1:R] for r in runs])
    return (np.arange(FIRST, R + 1), np.nanmedian(M, 0),
            np.nanpercentile(M, 25, 0), np.nanpercentile(M, 75, 0))


def main():
    data = load()
    if not data:
        raise SystemExit("no P1 runs with diagnostics yet")
    parts = [p for p in ("dirichlet", "iid") if p in data]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
    styles = {"dirichlet": "-", "iid": "--"}
    pname = {"dirichlet": "Dirichlet(0.5)", "iid": "IID"}
    for part in parts:
        runs, ls = data[part], styles[part]
        for key, col, lab in (("pair_cos_full", "C3", "full vector"),
                              ("pair_cos_sig", "C0", "trainable only")):
            x, m, lo, hi = band(runs, key)
            axes[0].plot(x, m, ls, color=col, label=f"{lab}, {pname[part]}")
            axes[0].fill_between(x, lo, hi, color=col, alpha=0.15, lw=0)
        for key, col, lab in (("buffer_norm_share", "C2", r"buffer share of $\|d_i\|^2$"),
                              ("buffer_dist_share", "C1", r"buffer share of $\|d_i-d_j\|^2$")):
            x, m, lo, hi = band(runs, key)
            axes[1].plot(x, m, ls, color=col, label=f"{lab}, {pname[part]}")
            axes[1].fill_between(x, lo, hi, color=col, alpha=0.15, lw=0)
    axes[0].set_ylabel("mean pairwise cosine")
    axes[1].set_ylabel("share")
    for ax in axes:
        ax.set_xlabel("round")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(alpha=0.3, lw=0.5)
        ax.legend(fontsize=6.5, loc="center right", frameon=False)
    n = ", ".join(f"{pname[p]}: {len(data[p])} runs" for p in parts)
    fig.suptitle(f"P1 per-round defect diagnostics ({n})", fontsize=8)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT)
    print(f"wrote {OUT} ({n})")


if __name__ == "__main__":
    main()
