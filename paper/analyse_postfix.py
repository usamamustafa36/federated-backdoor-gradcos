#!/usr/bin/env python3
"""Analyse the post-fix controlled A/B campaign (results/postfix_p1/).

Each run in P1 has a twin that is identical in every respect -- config, seed,
data partition, attacker -- except ``defense.signal_subspace``:

    full      : decisions computed over the whole flattened state_dict
                (BatchNorm num_batches_tracked included) -- the defect
    trainable : decisions computed over trainable parameters only -- the fix

so the per-seed difference trainable - full is the causal effect of the
defect on that defense, with training stochasticity matched by the seed.

Outputs (all generated, nothing typed by hand):
    results/postfix_p1/summary_pairs.csv   one row per (defense, partition, attack, metric)
    results/postfix_p1/summary_pairs.md    the same as a readable table
    paper/numbers_postfix.tex              LaTeX macros; missing cells -> \\PENDING

Statistics per (defense, partition, attack, metric), over seeds present in BOTH arms:
    mean of each arm, seed s.d. of each arm, paired mean difference (fixed - defect),
    its 95% t-interval, the paired t-test p and the Wilcoxon signed-rank p.
A difference is reported as significant only by the paired test at alpha=0.05,
with Holm correction across the defenses within a (partition, attack, metric).

Usage:  python3 paper/analyse_postfix.py [--min-seeds 3]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from src.metrics.aggregate import summarize_history  # noqa: E402

RES = os.path.join(ROOT, "results", "postfix_p1")
OUT_TEX = os.path.join(ROOT, "paper", "numbers_postfix.tex")
TAIL = 5  # report the mean of the last 5 of 15 rounds

METRICS = ["CA", "macro_f1", "BSR", "DR", "FPR"]
DIAG = ["buffer_norm_share", "buffer_dist_share", "pair_cos_full", "pair_cos_sig"]
DEFENSES = ["fedavg", "krum", "bulyan", "rfa", "normclip", "median", "trimmedmean",
            "flame", "fltrust", "foolsgold", "gradcos", "fldetector"]
# LaTeX macro names cannot contain digits or underscores.
DNAME = {"fedavg": "Fedavg", "krum": "Krum", "bulyan": "Bulyan", "rfa": "Rfa",
         "normclip": "Normclip", "median": "Median", "trimmedmean": "Trimmed",
         "flame": "Flame", "fltrust": "Fltrust", "foolsgold": "Foolsgold",
         "gradcos": "Gradcos", "fldetector": "Fldetector"}
PNAME = {"iid": "Iid", "dirichlet": "Dir"}
MNAME = {"CA": "CA", "macro_f1": "Fone", "BSR": "BSR", "DR": "DR", "FPR": "FPR"}
ANAME = {False: "Clean", True: "Atk"}


def tail_mean(xs, k=TAIL):
    xs = [x for x in xs[-k:] if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else float("nan")


def load(res=RES):
    """-> runs[(defense, partition, attack)][mode][seed] = dict of metrics."""
    runs = defaultdict(lambda: defaultdict(dict))
    for path in glob.glob(os.path.join(res, "*.json")):
        try:
            payload = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue  # a cell still being written
        if "history" not in payload:
            continue
        cfg = payload["config"]
        mode = str(cfg["defense"].get("signal_subspace", "trainable")).lower()
        s = summarize_history(payload, tail=TAIL)
        h = payload["history"]
        for k in DIAG:  # every round counts here: it is a property of the pipeline
            v = [x for x in h.get(k, []) if x is not None and not math.isnan(x)]
            s[k] = float(np.mean(v)) if v else float("nan")
        key = (s["defense"], s["partition"], bool(s["attack"]))
        runs[key][mode][int(cfg["seed"])] = s
    return runs


def fmt(x, nd=3):
    return "\\PENDING" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def holm(ps):
    """Holm step-down adjusted p-values (nan passes through)."""
    idx = [i for i, p in enumerate(ps) if not math.isnan(p)]
    order = sorted(idx, key=lambda i: ps[i])
    adj = [float("nan")] * len(ps)
    running = 0.0
    m = len(order)
    for r, i in enumerate(order):
        running = max(running, min(1.0, (m - r) * ps[i]))
        adj[i] = running
    return adj


def main():
    global RES
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-seeds", type=int, default=3,
                    help="paired seeds required before a cell's statistics are reported")
    ap.add_argument("--res", default=RES, help="results directory (default results/postfix_p1)")
    ap.add_argument("--no-tex", action="store_true", help="do not write numbers_postfix.tex")
    ap.add_argument("--atk-res", default=None,
                    help="take the ATTACKED cells from this directory instead (e.g. "
                         "results/postfix_p2: the iteration-4 attack that implants), "
                         "keeping the clean cells from --res")
    args = ap.parse_args()
    RES = args.res
    runs = load(RES)
    if args.atk_res:
        for k in [k for k in runs if k[2]]:
            del runs[k]
        for k, v in load(args.atk_res).items():
            if k[2]:
                runs[k] = v
    rows = []
    for d in DEFENSES:
        for part in ("dirichlet", "iid"):
            for atk in (False, True):
                arms = runs.get((d, part, atk), {})
                full, fix = arms.get("full", {}), arms.get("trainable", {})
                seeds = sorted(set(full) & set(fix))
                for m in METRICS + DIAG:
                    a = np.array([full[s][m] for s in seeds], dtype=float)
                    b = np.array([fix[s][m] for s in seeds], dtype=float)
                    ok = ~(np.isnan(a) | np.isnan(b))
                    a, b = a[ok], b[ok]
                    n = len(a)
                    r = dict(defense=d, partition=part, attack=atk, metric=m, n=n,
                             full_mean=float("nan"), full_sd=float("nan"),
                             fix_mean=float("nan"), fix_sd=float("nan"),
                             diff=float("nan"), ci_lo=float("nan"), ci_hi=float("nan"),
                             p_t=float("nan"), p_w=float("nan"))
                    if n >= args.min_seeds:
                        dd = b - a
                        r.update(full_mean=a.mean(), full_sd=a.std(ddof=1),
                                 fix_mean=b.mean(), fix_sd=b.std(ddof=1),
                                 diff=dd.mean())
                        se = dd.std(ddof=1) / math.sqrt(n)
                        if se > 0:
                            tq = stats.t.ppf(0.975, n - 1)
                            r.update(ci_lo=dd.mean() - tq * se, ci_hi=dd.mean() + tq * se,
                                     p_t=float(stats.ttest_rel(b, a).pvalue))
                            if np.any(dd != 0):
                                r["p_w"] = float(stats.wilcoxon(b, a).pvalue)
                        else:
                            r.update(ci_lo=dd.mean(), ci_hi=dd.mean(), p_t=1.0, p_w=1.0)
                    rows.append(r)
    # Holm across defenses within (partition, attack, metric)
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[(r["partition"], r["attack"], r["metric"])].append(i)
    for idxs in groups.values():
        adj = holm([rows[i]["p_t"] for i in idxs])
        for i, p in zip(idxs, adj):
            rows[i]["p_holm"] = p

    os.makedirs(RES, exist_ok=True)
    cols = ["defense", "partition", "attack", "metric", "n", "full_mean", "full_sd",
            "fix_mean", "fix_sd", "diff", "ci_lo", "ci_hi", "p_t", "p_w", "p_holm"]
    with open(os.path.join(RES, "summary_pairs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(RES, "summary_pairs.md"), "w") as f:
        f.write("| defense | part | atk | metric | n | defect | fixed | diff [95% CI] | p_t | p_holm |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            if r["metric"] in METRICS and r["n"] > 0:
                f.write(f"| {r['defense']} | {r['partition']} | {int(r['attack'])} | {r['metric']} "
                        f"| {r['n']} | {r['full_mean']:.3f}+/-{r['full_sd']:.3f} "
                        f"| {r['fix_mean']:.3f}+/-{r['fix_sd']:.3f} "
                        f"| {r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] "
                        f"| {r['p_t']:.3g} | {r['p_holm']:.3g} |\n")

    # Macros: \pf<Metric><Defense><Part><Atk><Field>, Field in
    # Def (defect arm mean), Fix (fixed arm mean), DefSd, FixSd, Diff, Lo, Hi, P, Ph, N
    lines = ["% Generated by paper/analyse_postfix.py from results/postfix_p1/. DO NOT EDIT.",
             f"% Paired full-vs-trainable A/B; metric = mean of last {TAIL} of 15 rounds."]
    n_res = n_tot = 0
    for r in rows:
        if r["metric"] not in MNAME:
            continue
        stem = (f"pf{MNAME[r['metric']]}{DNAME[r['defense']]}"
                f"{PNAME[r['partition']]}{ANAME[r['attack']]}")
        vals = {"Def": fmt(r["full_mean"]), "Fix": fmt(r["fix_mean"]),
                "DefSd": fmt(r["full_sd"]), "FixSd": fmt(r["fix_sd"]),
                "Diff": ("\\PENDING" if math.isnan(r["diff"]) else f"{r['diff']:+.3f}"),
                "Lo": fmt(r["ci_lo"]), "Hi": fmt(r["ci_hi"]),
                "P": fmt(r["p_t"]), "Ph": fmt(r.get("p_holm", float("nan"))),
                "N": str(r["n"]) if r["n"] >= args.min_seeds else "\\PENDING"}
        for k, v in vals.items():
            lines.append(f"\\providecommand{{\\{stem}{k}}}{{{v}}}")
            n_tot += 1
            n_res += v != "\\PENDING"
    # Pipeline diagnostics pooled over every run of a partition (both arms, all
    # defenses): they describe the transmitted vector, not a defense's choice.
    for part in ("dirichlet", "iid"):
        for k, nm in zip(DIAG, ["BufNormShare", "BufDistShare", "CosFull", "CosSig"]):
            vals = [s[k] for (d, p, a), arms in runs.items() if p == part
                    for mode in arms.values() for s in mode.values()
                    if not math.isnan(s[k])]
            v = fmt(float(np.median(vals)) if vals else float("nan"))
            lines.append(f"\\providecommand{{\\pfDiag{nm}{PNAME[part]}}}{{{v}}}")
            lines.append(f"\\providecommand{{\\pfDiag{nm}{PNAME[part]}Runs}}"
                         f"{{{len(vals) if vals else chr(92) + 'PENDING'}}}")
            if nm == "BufNormShare":
                # Corollary 1 of the paper: every pairwise cosine lies within
                # 2(1-s) of the buffer cosine; evaluated at the median share s.
                band = 2.0 * (1.0 - float(np.median(vals))) if vals else float("nan")
                lines.append(f"\\providecommand{{\\pfDiagCosBand{PNAME[part]}}}{{{fmt(band)}}}")
                # Eq. (norm): ||d_i|| / ||u_i|| = 1/sqrt(1-s). A rule that clips to, or
                # adds noise proportional to, a norm statistic over the full vector
                # sets it this many times larger than the trainable update's norm.
                infl = 1.0 / math.sqrt(1.0 - float(np.median(vals))) if vals else float("nan")
                lines.append(f"\\providecommand{{\\pfDiagNormInfl{PNAME[part]}}}"
                             f"{{{'%.1f' % infl if vals else chr(92) + 'PENDING'}}}")
    # Campaign progress, so the manuscript can say how much of P1 it rests on.
    n_cells = sum(len(s) for arms in runs.values() for s in arms.values())
    lines.append(f"\\providecommand{{\\pfCellsDone}}{{{n_cells}}}")
    lines.append("\\providecommand{\\pfCellsTarget}{960}")
    if not args.no_tex:
        with open(OUT_TEX, "w") as f:
            f.write("\n".join(lines) + "\n")
    total_runs = sum(len(s) for arms in runs.values() for s in arms.values())
    print(f"postfix P1: {total_runs} runs loaded; {n_res}/{n_tot} macros resolved"
          + ("" if args.no_tex else f" -> {OUT_TEX}"))
    for r in rows:
        if r["metric"] in ("CA", "BSR") and r["n"] >= args.min_seeds:
            sig = "*" if r.get("p_holm", 1) < 0.05 else " "
            print(f"  {r['defense']:11s} {r['partition']:9s} atk={int(r['attack'])} {r['metric']:3s} "
                  f"n={r['n']:2d} defect {r['full_mean']:.3f} fixed {r['fix_mean']:.3f} "
                  f"diff {r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] "
                  f"p={r['p_t']:.3g} holm={r['p_holm']:.3g}{sig}")


if __name__ == "__main__":
    main()
