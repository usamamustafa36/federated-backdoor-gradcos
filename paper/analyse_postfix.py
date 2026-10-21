#!/usr/bin/env python3
"""Analyse the post-fix controlled A/B campaign (P1: results/postfix_p1/; the
campaign of record since iteration 10 is P3: --res results/postfix_p3
--atk-res results/postfix_p3 --target 1040, with the pre-registered implant rule
--implant-bsr 0.5 applied to attacked BSR).

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
    the exact paired sign-flip permutation test of that mean difference (all 2^n
    sign assignments of the per-seed differences; Fisher/Pitman, see Ernst 2004),
    and its 95% confidence interval obtained by inverting the same test (the set of
    shifts delta in [-1, 1] that the test does not reject, resolved on a 0.001 grid).
Iteration 13: this replaces the paired t-interval, which left [-1, 1] for bounded
rates at n = 4-5 (FLTrust FPR [0.383, 1.049]). The inverted-test interval can never
leave the feasible range, needs no normality, and agrees with the reported p by
construction (it excludes 0 iff p <= 0.05). Its price is honest: with n paired
seeds whose differences are nonzero the smallest attainable two-sided p is
2^(1-n), so n <= 5 cannot reach p < 0.05 and its interval is the whole feasible
range; the generator emits that floor (Pmin) and the sign counts (Pos/Neg: seeds
on which fixed > defect / fixed < defect) as an effect-consistency measure.
A difference is reported as significant only by that test at alpha=0.05, with
Holm correction across the 13 defenses within a (partition, attack, metric); a
second, global Holm over every tested (defense, partition, attack, metric) is
emitted as a count for robustness. The paired t-test p and Wilcoxon p stay in the
CSV for reference only.

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
DIAG_FIRST_ROUND = 2  # diagnostics skip round 1 (aliasing defect; see load())

METRICS = ["CA", "macro_f1", "BSR", "DR", "FPR"]
DIAG = ["buffer_norm_share", "buffer_dist_share", "pair_cos_full", "pair_cos_sig"]
DEFENSES = ["fedavg", "krum", "bulyan", "rfa", "normclip", "median", "trimmedmean",
            "flame", "fltrust", "foolsgold", "gradcos", "fldetector", "alignins"]
# LaTeX macro names cannot contain digits or underscores.
DNAME = {"fedavg": "Fedavg", "krum": "Krum", "bulyan": "Bulyan", "rfa": "Rfa",
         "normclip": "Normclip", "median": "Median", "trimmedmean": "Trimmed",
         "flame": "Flame", "fltrust": "Fltrust", "foolsgold": "Foolsgold",
         "gradcos": "Gradcos", "fldetector": "Fldetector",
         "alignins": "Alignins"}
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
        # Diagnostics are a property of the pipeline, so every round counts --
        # except round 1. Iteration 5: in round 1 the engine's global weights
        # alias the model (src/fl/engine.py, `copy_initial_global`), clients
        # train sequentially and the logged deltas are referenced to the round-1
        # aggregate, so round 1's diagnostics describe the aliasing defect, not
        # the transmitted geometry. Rounds 2..R are unaffected.
        for k in DIAG:
            v = [x for x in h.get(k, [])[DIAG_FIRST_ROUND - 1:]
                 if x is not None and not math.isnan(x)]
            s[k] = float(np.mean(v)) if v else float("nan")
        key = (s["defense"], s["partition"], bool(s["attack"]))
        runs[key][mode][int(cfg["seed"])] = s
    return runs


def fmt(x, nd=3):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "\\PENDING"
    out = f"{x:.{nd}f}"
    # no negative zero ("-0.000") for a value that rounds to zero
    return out[1:] if out.startswith("-") and float(out) == 0 else out


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


def _signs(n):
    """All 2^n sign vectors as an (2^n, n) array (n <= 16 here: ten seeds)."""
    if n > 16:
        raise ValueError("exact enumeration limited to 16 paired seeds")
    idx = np.arange(2 ** n)[:, None]
    return 1.0 - 2.0 * ((idx >> np.arange(n)[None, :]) & 1)


def signflip_p(d, signs=None):
    """Exact two-sided paired sign-flip permutation p of the mean difference."""
    d = np.asarray(d, dtype=float)
    signs = _signs(len(d)) if signs is None else signs
    null = np.abs(signs @ d)
    return float(np.mean(null >= abs(d.sum()) - 1e-12))


def signflip_ci(d, alpha=0.05, lo=-1.0, hi=1.0, step=0.001):
    """95% CI for the location shift by inverting the sign-flip test: the shifts
    delta on a grid over the feasible range [lo, hi] with p(d - delta) > alpha.
    Returns the outermost accepted grid points (so the interval is inside
    [lo, hi] by construction). If no shift is rejected (n too small to reach
    alpha), the interval is the whole feasible range."""
    d = np.asarray(d, dtype=float)
    signs = _signs(len(d))
    grid = np.round(np.arange(lo, hi + step / 2, step), 6)
    grid = np.union1d(grid, [round(float(d.mean()), 6)])  # the point estimate is always accepted
    shifted = d[None, :] - grid[:, None]                     # (G, n)
    obs = np.abs(shifted.sum(axis=1))                        # (G,)
    null = np.abs(shifted @ signs.T)                         # (G, 2^n)
    p = np.mean(null >= obs[:, None] - 1e-12, axis=1)
    acc = grid[p > alpha]
    return float(acc.min()), float(acc.max())


def signflip_p_one(d, direction=1):
    """Exact ONE-sided paired sign-flip p in the registered direction (+1: the
    alternative is mean(d) > 0): share of sign vectors whose signed sum is at
    least the observed one. Used only for the pre-registered hypotheses."""
    d = direction * np.asarray(d, dtype=float)
    null = _signs(len(d)) @ d
    return float(np.mean(null >= d.sum() - 1e-12))


def read_prereg(path):
    """Parse the ```prereg block of iterations/PREREG_P3.md (iteration 14).
    -> list of dicts: id, family, defense, partition, attack, metric, direction, blind."""
    out, inside = [], False
    for line in open(path):
        t = line.strip()
        if t.startswith("```prereg"):
            inside = True
            continue
        if inside and t.startswith("```"):
            break
        if inside and t:
            f = [x.strip() for x in t.split("|")]
            out.append(dict(id=f[0], family=f[1], defense=f[2], partition=f[3],
                            attack=f[4] == "1", metric=f[5],
                            direction=1 if f[6] == "+" else -1, blind=f[7], source=f[8]))
    if not out:
        raise SystemExit(f"no ```prereg block in {path}")
    return out


PRE_NUM = {"1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five", "6": "Six"}


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
    ap.add_argument("--prefix", default="pf",
                    help="macro prefix (default pf). Iteration 6: the stopped P1/P2 "
                         "campaign (defective engine) is kept as \\pa... macros in "
                         "numbers_postfix_p1.tex; P3 is the campaign of record (\\pf...)")
    ap.add_argument("--out", default=None, help="output .tex (default numbers_postfix.tex)")
    ap.add_argument("--target", type=int, default=960,
                    help="cells in the campaign (P1: 12 rules x 80 = 960; P3 adds alignins: 1040)")
    ap.add_argument("--implant-bsr", type=float, default=0.5,
                    help="pre-registered inclusion rule (iteration 9, before any defended "
                         "attacked cell of P3 ran): a rule's ATTACKED BSR is read only on "
                         "seeds where FedAvg's attacked cell implants, i.e. last-5-round BSR "
                         "above this value. 0 disables the filter.")
    ap.add_argument("--prereg", default=None,
                    help="pre-registration file with a ```prereg block (iteration 14: "
                         "iterations/PREREG_P3.md). Its hypotheses are tested one-sided in "
                         "the registered direction with Holm within each family, and "
                         "reported apart from the exploratory two-sided analysis.")
    ap.add_argument("--final-n", type=int, default=10,
                    help="seeds per cell in the finished campaign; a confirmatory result "
                         "computed with fewer is labelled interim")
    args = ap.parse_args()
    RES = args.res
    runs = load(RES)
    if args.atk_res:
        for k in [k for k in runs if k[2]]:
            del runs[k]
        for k, v in load(args.atk_res).items():
            if k[2]:
                runs[k] = v
    # Pre-registered implant set per partition. FedAvg reads no decision statistic,
    # so its two arms run the same computation (clean s42: identical CA and BSR in
    # both); a seed is in the set iff every FedAvg attacked cell present for it
    # (either arm) implants. Seeds with no FedAvg attacked cell yet are undecided
    # and are not read.
    implant, excluded = {}, {}
    for part in ("dirichlet", "iid"):
        arms = runs.get(("fedavg", part, True), {})
        per_seed = defaultdict(list)
        for mode in arms.values():
            for sd, s in mode.items():
                per_seed[sd].append(s["BSR"])
        implant[part] = sorted(sd for sd, v in per_seed.items()
                               if all(x > args.implant_bsr for x in v))
        excluded[part] = sorted(sd for sd in per_seed if sd not in implant[part])
    rows = []
    for d in DEFENSES:
        for part in ("dirichlet", "iid"):
            for atk in (False, True):
                arms = runs.get((d, part, atk), {})
                full, fix = arms.get("full", {}), arms.get("trainable", {})
                seeds_all = sorted(set(full) & set(fix))
                for m in METRICS + DIAG:
                    seeds = seeds_all
                    if atk and m == "BSR" and args.implant_bsr > 0:
                        seeds = [s for s in seeds_all if s in implant[part]]
                    a = np.array([full[s][m] for s in seeds], dtype=float)
                    b = np.array([fix[s][m] for s in seeds], dtype=float)
                    ok = ~(np.isnan(a) | np.isnan(b))
                    a, b = a[ok], b[ok]
                    n = len(a)
                    r = dict(defense=d, partition=part, attack=atk, metric=m, n=n,
                             full_mean=float("nan"), full_sd=float("nan"),
                             fix_mean=float("nan"), fix_sd=float("nan"),
                             diff=float("nan"), ci_lo=float("nan"), ci_hi=float("nan"),
                             p_perm=float("nan"), p_t=float("nan"), p_w=float("nan"),
                             n_pos=0, n_neg=0, p_min=float("nan"), d_z=float("nan"))
                    if n >= args.min_seeds:
                        dd = b - a
                        r.update(full_mean=a.mean(), full_sd=a.std(ddof=1),
                                 fix_mean=b.mean(), fix_sd=b.std(ddof=1),
                                 diff=dd.mean(),
                                 n_pos=int(np.sum(dd > 0)), n_neg=int(np.sum(dd < 0)))
                        nz = int(np.sum(dd != 0))
                        r["p_min"] = 2.0 ** (1 - nz) if nz else 1.0
                        r["p_perm"] = signflip_p(dd)
                        if m in METRICS:  # rates and accuracies: difference lies in [-1, 1]
                            r["ci_lo"], r["ci_hi"] = signflip_ci(dd)
                        sd_d = dd.std(ddof=1)
                        if sd_d > 0:
                            r["d_z"] = float(dd.mean() / sd_d)
                            r["p_t"] = float(stats.ttest_rel(b, a).pvalue)
                            if np.any(dd != 0):
                                r["p_w"] = float(stats.wilcoxon(b, a).pvalue)
                        elif dd.mean() == 0:
                            r.update(p_t=1.0, p_w=1.0)  # identical arms on every seed
                    rows.append(r)
    # Holm across defenses within (partition, attack, metric), on the exact test
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[(r["partition"], r["attack"], r["metric"])].append(i)
    for idxs in groups.values():
        adj = holm([rows[i]["p_perm"] for i in idxs])
        for i, p in zip(idxs, adj):
            rows[i]["p_holm"] = p
    # Global Holm over every tested reported-metric hypothesis (robustness count)
    gidx = [i for i, r in enumerate(rows) if r["metric"] in METRICS]
    for i, p in zip(gidx, holm([rows[i]["p_perm"] for i in gidx])):
        rows[i]["p_holm_global"] = p

    os.makedirs(RES, exist_ok=True)
    cols = ["defense", "partition", "attack", "metric", "n", "full_mean", "full_sd",
            "fix_mean", "fix_sd", "diff", "ci_lo", "ci_hi", "n_pos", "n_neg", "d_z",
            "p_perm", "p_min", "p_holm", "p_holm_global", "p_t", "p_w"]
    with open(os.path.join(RES, "summary_pairs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(RES, "summary_pairs.md"), "w") as f:
        f.write("| defense | part | atk | metric | n | defect | fixed | diff [95% CI, sign-flip inversion] "
                "| +/- | p_perm | p_holm |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            if r["metric"] in METRICS and r["n"] > 0:
                f.write(f"| {r['defense']} | {r['partition']} | {int(r['attack'])} | {r['metric']} "
                        f"| {r['n']} | {r['full_mean']:.3f}+/-{r['full_sd']:.3f} "
                        f"| {r['fix_mean']:.3f}+/-{r['fix_sd']:.3f} "
                        f"| {r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] "
                        f"| {r['n_pos']}/{r['n_neg']} | {r['p_perm']:.3g} | {r['p_holm']:.3g} |\n")

    # Macros: \pf<Metric><Defense><Part><Atk><Field>, Field in
    # Def (defect arm mean), Fix (fixed arm mean), DefSd, FixSd, Diff, Lo, Hi (95% CI by
    # inverting the exact sign-flip test), P (exact sign-flip p), Ph (Holm within the
    # 13 rules), Pos/Neg (seeds with fixed > / < defect), Pmin (smallest attainable p), N
    lines = [f"% Generated by paper/analyse_postfix.py from {os.path.relpath(RES, ROOT)}"
             f" (attacked: {args.atk_res or os.path.relpath(RES, ROOT)}). DO NOT EDIT.",
             f"% Paired full-vs-trainable A/B; metric = mean of last {TAIL} of 15 rounds."]
    n_res = n_tot = 0
    for r in rows:
        if r["metric"] not in MNAME:
            continue
        stem = (f"pf{MNAME[r['metric']]}{DNAME[r['defense']]}"
                f"{PNAME[r['partition']]}{ANAME[r['attack']]}")
        vals = {"Def": fmt(r["full_mean"]), "Fix": fmt(r["fix_mean"]),
                "DefSd": fmt(r["full_sd"]), "FixSd": fmt(r["fix_sd"]),
                "Diff": ("\\PENDING" if math.isnan(r["diff"])
                         else ("0.000" if round(r["diff"], 3) == 0 else f"{r['diff']:+.3f}")),
                "Lo": fmt(r["ci_lo"]), "Hi": fmt(r["ci_hi"]),
                "P": fmt(r["p_perm"]), "Ph": fmt(r.get("p_holm", float("nan"))),
                "Pos": str(r["n_pos"]) if r["n"] >= args.min_seeds else "\\PENDING",
                "Neg": str(r["n_neg"]) if r["n"] >= args.min_seeds else "\\PENDING",
                "Pmin": fmt(r["p_min"], 4),
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
    # The implant set (pre-registered rule above), so the manuscript can say which
    # seeds the attacked BSR columns rest on and which were excluded.
    for part in ("dirichlet", "iid"):
        inc, exc = implant[part], excluded[part]
        lines.append(f"\\providecommand{{\\pfImplantN{PNAME[part]}}}"
                     f"{{{len(inc) if (inc or exc) else chr(92) + 'PENDING'}}}")
        lines.append(f"\\providecommand{{\\pfImplantDecided{PNAME[part]}}}"
                     f"{{{len(inc) + len(exc) if (inc or exc) else chr(92) + 'PENDING'}}}")
        # FedAvg's attacked BSR over EVERY decided seed (unfiltered): the ceiling the
        # attack reaches undefended, including the seeds the rule excludes.
        ps = defaultdict(list)
        for mode in runs.get(("fedavg", part, True), {}).values():
            for sd, s in mode.items():
                ps[sd].append(s["BSR"])
        allv = [float(np.mean(v)) for v in ps.values()]  # one value per seed
        lines.append(f"\\providecommand{{\\pfBSRFedavgAllSeeds{PNAME[part]}}}"
                     f"{{{fmt(float(np.mean(allv)) if allv else float('nan'))}}}")
        lines.append(f"\\providecommand{{\\pfImplantExcl{PNAME[part]}}}"
                     f"{{{', '.join(map(str, exc)) if exc else ('none' if inc else chr(92) + 'PENDING')}}}")
    # Multiple-comparison bookkeeping over the reported metrics: tests run, and how
    # many survive Holm within their family of rules and Holm over all of them.
    tested = [r for r in rows if r["metric"] in METRICS and not math.isnan(r["p_perm"])]
    lines.append(f"\\providecommand{{\\pfTestsRun}}{{{len(tested)}}}")
    lines.append(f"\\providecommand{{\\pfSigFamily}}"
                 f"{{{sum(r['p_holm'] <= 0.05 for r in tested)}}}")
    lines.append(f"\\providecommand{{\\pfSigGlobal}}"
                 f"{{{sum(r['p_holm_global'] <= 0.05 for r in tested)}}}")
    lines.append(f"\\providecommand{{\\pfSigRaw}}"
                 f"{{{sum(r['p_perm'] <= 0.05 for r in tested)}}}")
    lines.append(f"\\providecommand{{\\pfTestableTen}}"
                 f"{{{fmt(2.0 ** (1 - 10), 4)}}}")  # smallest attainable p at 10 seeds
    # Confirmatory analysis (iteration 14): only the hypotheses registered in
    # --prereg, one-sided in their registered direction, Holm within each family.
    # Everything above is the exploratory analysis and is labelled so in the paper.
    if args.prereg:
        hyps = read_prereg(args.prereg)
        byk = {(r["defense"], r["partition"], r["attack"], r["metric"]): r for r in rows}
        for h in hyps:
            r = byk[(h["defense"], h["partition"], h["attack"], h["metric"])]
            h["n"], h["n_pos"], h["n_neg"], h["diff"] = r["n"], r["n_pos"], r["n_neg"], r["diff"]
            h["p1"] = float("nan")
            if r["n"] >= args.min_seeds:
                arms = runs[(h["defense"], h["partition"], h["attack"])]
                seeds = sorted(set(arms["full"]) & set(arms["trainable"]))
                dd = np.array([arms["trainable"][sd][h["metric"]] - arms["full"][sd][h["metric"]]
                               for sd in seeds], dtype=float)
                dd = dd[~np.isnan(dd)]
                h["p1"] = signflip_p_one(dd, h["direction"])
                if h["direction"] < 0:  # sign counts in the registered direction
                    h["n_pos"], h["n_neg"] = h["n_neg"], h["n_pos"]
        final = all(h["n"] >= args.final_n for h in hyps)
        fams = sorted({h["family"] for h in hyps})
        for fam in fams:
            hs = [h for h in hyps if h["family"] == fam]
            # Holm over the REGISTERED family size: an untested hypothesis enters
            # with p = 1, so an interim result is never corrected for fewer tests
            # than the final one will be.
            p1 = lambda hh: 1.0 if math.isnan(hh["p1"]) else hh["p1"]  # noqa: E731
            for h, ph in zip(hs, holm([p1(h) for h in hs])):
                h["ph"] = ph
            blind = [h for h in hs if h["blind"] == "yes"]
            for h, ph in zip(blind, holm([p1(h) for h in blind])):
                h["ph_blind"] = ph
            FN = fam.capitalize()
            done = [h for h in hs if not math.isnan(h["p1"])]
            lines.append(f"\\providecommand{{\\pfPre{FN}Total}}{{{len(hs)}}}")
            lines.append(f"\\providecommand{{\\pfPre{FN}Tested}}{{{len(done)}}}")
            lines.append(f"\\providecommand{{\\pfPre{FN}Supported}}"
                         f"{{{sum(h['ph'] <= 0.05 for h in done)}}}")
            lines.append(f"\\providecommand{{\\pfPre{FN}BlindTotal}}{{{len(blind)}}}")
            lines.append(f"\\providecommand{{\\pfPre{FN}BlindSupported}}"
                         f"{{{sum(h.get('ph_blind', 1) <= 0.05 for h in blind if not math.isnan(h['p1']))}}}")
        lines.append(f"\\providecommand{{\\pfPrePartialN}}"
                     f"{{{sum(h['blind'] != 'yes' for h in hyps)}}}")
        lines.append(f"\\providecommand{{\\pfPreBlindN}}"
                     f"{{{sum(h['blind'] == 'yes' for h in hyps)}}}")
        man = os.path.splitext(args.prereg)[0] + "_manifest.txt"
        nman = sum(1 for l in open(man) if l.strip()) if os.path.exists(man) else None
        lines.append(f"\\providecommand{{\\pfPreManifestN}}"
                     f"{{{nman if nman is not None else chr(92) + 'PENDING'}}}")
        lines.append(f"\\providecommand{{\\pfPreFinal}}{{{'final' if final else 'interim'}}}")
        lines.append(f"\\providecommand{{\\pfPreFloorTen}}{{{fmt(2.0 ** -10, 4)}}}")
        for h in hyps:
            stem = "pfPre" + h["id"][0] + PRE_NUM[h["id"][1:]]
            ok = h["n"] >= args.min_seeds
            verdict = ("\\PENDING" if not ok else
                       ("supported" if h["ph"] <= 0.05 else "not supported")
                       + ("" if final else " (interim)"))
            vals = {"N": str(h["n"]) if ok else "\\PENDING",
                    "Pos": str(h["n_pos"]) if ok else "\\PENDING",
                    "Neg": str(h["n_neg"]) if ok else "\\PENDING",
                    "Diff": ("\\PENDING" if not ok else
                             ("0.000" if round(h["diff"], 3) == 0 else f"{h['diff']:+.3f}")),
                    "P": fmt(h["p1"], 4), "Ph": fmt(h.get("ph", float("nan")), 4),
                    "Verdict": verdict}
            for k, v in vals.items():
                lines.append(f"\\providecommand{{\\{stem}{k}}}{{{v}}}")
        with open(os.path.join(RES, "prereg_results.md"), "w") as f:
            f.write(f"# Confirmatory hypotheses ({args.prereg}); "
                    f"{'final' if final else 'INTERIM'}: one-sided exact sign-flip, Holm per family\n\n")
            f.write("| id | family | rule | part | atk | metric | dir | blind | n | +/- | diff | p (1-sided) | p_Holm | p_Holm blind-only |\n")
            f.write("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
            for h in hyps:
                f.write(f"| {h['id']} | {h['family']} | {h['defense']} | {h['partition']} | "
                        f"{int(h['attack'])} | {h['metric']} | {'+' if h['direction'] > 0 else '-'} | "
                        f"{h['blind']} | {h['n']} | {h['n_pos']}/{h['n_neg']} | {h['diff']:+.3f} | "
                        f"{h['p1']:.4g} | {h.get('ph', float('nan')):.4g} | "
                        f"{h.get('ph_blind', float('nan')):.4g} |\n")
        print(f"confirmatory ({'final' if final else 'INTERIM'}):")
        for h in hyps:
            print(f"  {h['id']} {h['family']:9s} {h['defense']:8s} {h['partition']:9s} "
                  f"atk={int(h['attack'])} {h['metric']:3s} blind={h['blind']:7s} n={h['n']:2d} "
                  f"signs {h['n_pos']}/{h['n_neg']} p1={h['p1']:.4g} holm={h.get('ph', float('nan')):.4g}")
    # Campaign progress, so the manuscript can say how much of P1 it rests on.
    n_cells = sum(len(s) for arms in runs.values() for s in arms.values())
    lines.append(f"\\providecommand{{\\pfCellsDone}}{{{n_cells}}}")
    lines.append(f"\\providecommand{{\\pfCellsTarget}}{{{args.target}}}")
    out_tex = args.out or OUT_TEX
    if args.prefix != "pf":
        lines = [l.replace("\\providecommand{\\pf", "\\providecommand{\\" + args.prefix)
                 for l in lines]
    if not args.no_tex:
        with open(out_tex, "w") as f:
            f.write("\n".join(lines) + "\n")
    total_runs = sum(len(s) for arms in runs.values() for s in arms.values())
    print(f"implant set (FedAvg attacked last-5 BSR > {args.implant_bsr}): "
          + "; ".join(f"{p}: in {implant[p]} out {excluded[p]}" for p in implant))
    print(f"postfix: {total_runs} runs loaded; {n_res}/{n_tot} macros resolved"
          + ("" if args.no_tex else f" -> {out_tex}"))
    for r in rows:
        if r["metric"] in ("CA", "BSR") and r["n"] >= args.min_seeds:
            sig = "*" if r.get("p_holm", 1) <= 0.05 else " "
            print(f"  {r['defense']:11s} {r['partition']:9s} atk={int(r['attack'])} {r['metric']:3s} "
                  f"n={r['n']:2d} defect {r['full_mean']:.3f} fixed {r['fix_mean']:.3f} "
                  f"diff {r['diff']:+.3f} [{r['ci_lo']:+.3f},{r['ci_hi']:+.3f}] "
                  f"signs {r['n_pos']}+/{r['n_neg']}- p={r['p_perm']:.3g} holm={r['p_holm']:.3g}{sig}")


if __name__ == "__main__":
    main()
