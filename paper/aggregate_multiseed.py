"""Collapse per-seed sweep JSONs (the `--seeds` runs, filenames ending _s{seed})
into a mean +/- std summary, one row per (dataset, partition, defense, attack,
trigger, malicious_ratio, poison_rate, variant).

Writes results/summary_multiseed.csv. Every number is computed from the committed
per-seed result files via the same last-10-round `summarize_history` used for the
single-seed tables, so multi-seed and single-seed numbers are directly comparable.
Nothing is hand-entered.
"""
import csv
import glob
import json
import os
from collections import defaultdict

import numpy as np

# Reuse the project's own metric extraction so the numbers match the rest of the
# pipeline exactly (last-10-round mean of each metric).
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.metrics.aggregate import summarize_history  # noqa: E402

RES = os.path.join(ROOT, "results")
OUT = os.path.join(RES, "summary_multiseed.csv")

# trigger_scale / trigger_mode / evasion_noise are part of the cell identity:
# two runs that differ only in trigger magnitude or in the attacker's evasion
# noise are different experiments and must never be averaged together.
KEYCOLS = ["dataset", "partition", "defense", "defense_variant", "attack", "trigger",
           "malicious_ratio", "poison_rate", "variant",
           "trigger_scale", "trigger_mode", "evasion_noise"]
METRICS = ["CA", "macro_f1", "BSR", "DR", "FPR", "stealthiness",
           "salience_gap", "mal_pair_cos", "honest_pair_cos", "mal_norm_ratio"]


def seed_files():
    """Every per-seed result file, including the ones in live subdirectories.

    Campaigns that need a non-default config are written to their own directory
    -- results/residual/ holds the five-seed GradCos residual-variant run -- and
    a top-level-only glob silently dropped them, which is why the residual table
    was hand-filled for a while.

    Subdirectories whose name starts with "_" are archived or superseded runs
    (_flame_buggy_backup, _pre_trigger_redesign_backup, and the dated reboot
    backups). They hold per-seed files from code that has since been fixed, so
    pulling them in would quietly average buggy cells into a reported mean.
    They are excluded by name, deliberately and permanently.
    """
    paths = glob.glob(os.path.join(RES, "*_s*.json"))
    for entry in sorted(os.listdir(RES)):
        if entry.startswith("_"):
            continue
        # results/postfix_*/ hold the post-fix A/B campaigns, in which the ONLY
        # difference between paired runs is defense.signal_subspace -- a field
        # not in KEYCOLS. Pooling them here would average the defect arm and the
        # fixed arm into one mean. They have their own analysis
        # (paper/analyse_postfix.py) and are excluded here deliberately.
        if entry.startswith("postfix"):
            continue
        sub = os.path.join(RES, entry)
        if os.path.isdir(sub):
            paths += glob.glob(os.path.join(sub, "*_s*.json"))
    return sorted(paths)


def collect():
    groups = defaultdict(lambda: defaultdict(list))
    seeds = defaultdict(set)
    # Per-seed files carry a _s{seed}.json suffix; only those are multi-seed cells.
    for path in seed_files():
        base = os.path.basename(path)
        # must end _s<digits>.json
        stem = base[:-5]
        tail = stem.rsplit("_s", 1)
        if len(tail) != 2 or not tail[1].isdigit():
            continue
        seed = int(tail[1])
        try:
            payload = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue
        if "history" not in payload:
            continue
        s = summarize_history(payload)
        key = tuple(s.get(k) for k in KEYCOLS)
        seeds[key].add(seed)
        for m in METRICS:
            v = s.get(m)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                groups[key][m].append(v)
    return groups, seeds


def main():
    groups, seeds = collect()
    if not groups:
        print("No per-seed (_s*) result files found yet. Run e.g.:\n"
              "  run_sweep.py --seeds 42 43 44 45 46 ...")
        return
    rows = []
    for key, metricvals in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        row = dict(zip(KEYCOLS, key))
        row["n_seeds"] = len(seeds[key])
        row["seeds"] = ";".join(str(s) for s in sorted(seeds[key]))
        for m in METRICS:
            vals = metricvals.get(m, [])
            if vals:
                a = np.array(vals, dtype=float)
                row[f"{m}_mean"] = float(a.mean())
                row[f"{m}_std"] = float(a.std(ddof=1)) if len(a) > 1 else 0.0
                row[f"{m}_min"] = float(a.min())
                row[f"{m}_max"] = float(a.max())
            else:
                row[f"{m}_mean"] = row[f"{m}_std"] = float("nan")
                row[f"{m}_min"] = row[f"{m}_max"] = float("nan")
        rows.append(row)

    cols = KEYCOLS + ["n_seeds", "seeds"]
    for m in METRICS:
        cols += [f"{m}_mean", f"{m}_std", f"{m}_min", f"{m}_max"]
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"wrote {OUT}  ({len(rows)} grouped cells)")
    # quick console view of the headline attack cells
    for r in rows:
        if r["attack"] in ("True", True):
            print(f"  {r['dataset']:10s} {r['partition']:9s} {r['defense']:9s} "
                  f"{r['trigger']:11s} m{r['malicious_ratio']} p{r['poison_rate']} "
                  f"n={r['n_seeds']}  BSR={r['BSR_mean']:.3f}+/-{r['BSR_std']:.3f}  "
                  f"CA={r['CA_mean']:.3f}")


if __name__ == "__main__":
    main()
