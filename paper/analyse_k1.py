#!/usr/bin/env python3
"""K1 (iterations/PREREG_K1.md): the registered k > 1 reversal test of Proposition prop:angle.

Reads the K1 cells (results/kgt_k1; settings KA = E_m 1, boost 4 and KB = E_m 15, boost 10; IID,
attacked; FLAME, FoolsGold, FLDetector, GradCos; defect arm = full, fixed arm = trainable; seeds
42-46) and the k < 1 baseline (results/postfix_p3, the same rules/seeds at E_m 15, boost 1), and
computes exactly what PREREG_K1 registers:
  M0  median k_hat > 1 per setting, k_hat = sin(atan((t/E) tan th_h)) / sin th_h,
      t = fixed arm's median mal_norm_ratio (rounds 2-15), cos^2 th_h = defect arm's median
      buffer_norm_share (rounds 2-15), E = E_m;
  H1  T = sum tau_r [G_K - G_P3] > 0 over FLAME (tau +1) and FoolsGold (tau -1), G = DR_def - DR_fix,
      exact one-sided sign-flip test, Holm over the settings passing M0;
  H2  T2 = sum tau_r G_K > 0, pooled over the settings passing M0, one exact sign-flip test;
  M1  Q_obs = defect / fixed median (1 - mal_pair_cos)/(1 - honest_pair_cos), Q_pred = k_hat^2,
      pooled: median Q_obs/Q_pred in [0.5, 2] and Q_obs > 1 in >= 80% of pairs.
DR/FPR/BSR/CA = mean of the last five rounds. Writes numbers_k1.tex (\\ko*); \\PENDING when missing.
"""
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results", "kgt_k1")
P3 = os.path.join(ROOT, "results", "postfix_p3")
OUT = os.path.join(HERE, "numbers_k1.tex")
PEND = "\\PENDING"
SETTINGS = {"A": (1, 4), "B": (15, 10)}          # E_m, boost
RULES = ("flame", "foolsgold", "fldetector", "gradcos")
TAU = {"flame": +1, "foolsgold": -1}
SEEDS = range(42, 47)
ROUNDS = 15
N_CELLS = len(SETTINGS) * len(RULES) * 2 * len(SEEDS)


def k1_path(res, mode, rule, me, b, s):
    return os.path.join(res, f"kgt{mode}_iid_ciciot2023_{rule}_atk1_m0.2_p0.1_fixed_b{b}_me{me}_sm_s{s}.json")


def p3_path(p3, mode, rule, s):
    return os.path.join(p3, f"p3{mode}_iid_ciciot2023_{rule}_atk1_m0.2_p0.1_fixed_me15_sm_s{s}.json")


def load(path):
    """History of a finished cell (15 rounds), else None (the registered missing-data rule)."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    try:
        h = json.load(open(path))["history"]
    except Exception:
        return None
    if len(h.get("detection_rate", [])) < ROUNDS:
        return None
    return h


def last5(h, key):
    return float(np.nanmean(np.asarray(h[key][-5:], float)))


def med(h, key):
    return float(np.nanmedian(np.asarray(h[key][1:], float)))


def khat(h_def, h_fix, E):
    t = med(h_fix, "mal_norm_ratio")
    s = med(h_def, "buffer_norm_share")
    tan_h = np.sqrt((1 - s) / s)
    th_h = np.arctan(tan_h)
    return float(np.sin(np.arctan(t / E * tan_h)) / np.sin(th_h))


def qratio(h):
    mm = np.asarray(h["mal_pair_cos"][1:], float)
    hh = np.asarray(h["honest_pair_cos"][1:], float)
    return float(np.nanmedian((1 - mm) / (1 - hh)))


def signflip_p(x):
    """Exact one-sided p of sum(x) >= observed under random sign flips of the nonzero terms."""
    x = np.asarray(x, float)
    if x.size == 0:
        return float("nan")
    obs = x.sum()
    a = np.abs(x[x != 0])          # zero terms flip to themselves: same p over the nonzero ones
    if a.size == 0:
        return 1.0
    cnt = 0
    for signs in itertools.product((1, -1), repeat=len(a)):
        if np.dot(a, signs) >= obs - 1e-12:
            cnt += 1
    return cnt / 2 ** len(a)


def holm(ps):
    """Holm-adjusted p-values for a dict name -> p (NaN entries are left out)."""
    items = sorted([(p, k) for k, p in ps.items() if p == p])
    m, out, run = len(items), {}, 0.0
    for i, (p, k) in enumerate(items):
        run = max(run, min(1.0, (m - i) * p))
        out[k] = run
    return out


def analyse(res=RES, p3=P3):
    cells = {}
    for X, (me, b) in SETTINGS.items():
        for r in RULES:
            for s in SEEDS:
                for mode in ("full", "trainable"):
                    cells[(X, r, s, mode)] = load(k1_path(res, mode, r, me, b, s))
    base = {(r, s, mode): load(p3_path(p3, mode, r, s))
            for r in TAU for s in SEEDS for mode in ("full", "trainable")}
    n_on_disk = sum(v is not None for v in cells.values())
    out = {"n_cells": n_on_disk, "settings": {}}
    m1 = []
    h1p, h2 = {}, []
    for X, (me, b) in SETTINGS.items():
        ks, d1, d2, desc = [], [], [], {}
        for r in RULES:
            for s in SEEDS:
                hd, hf = cells[(X, r, s, "full")], cells[(X, r, s, "trainable")]
                if hd is None or hf is None:
                    continue
                k = khat(hd, hf, me)
                ks.append(k)
                m1.append((X, r, s, qratio(hd) / qratio(hf), k ** 2))
                g = last5(hd, "detection_rate") - last5(hf, "detection_rate")
                desc.setdefault(r, []).append(dict(
                    dr_def=last5(hd, "detection_rate"), dr_fix=last5(hf, "detection_rate"),
                    fpr_def=last5(hd, "false_positive_rate"), fpr_fix=last5(hf, "false_positive_rate"),
                    bsr_def=last5(hd, "bsr"), bsr_fix=last5(hf, "bsr"),
                    ca_def=last5(hd, "accuracy"), ca_fix=last5(hf, "accuracy")))
                if r in TAU:
                    bd, bf = base[(r, s, "full")], base[(r, s, "trainable")]
                    d2.append(TAU[r] * g)
                    if bd is not None and bf is not None:
                        g0 = last5(bd, "detection_rate") - last5(bf, "detection_rate")
                        d1.append(TAU[r] * (g - g0))
        k_med = float(np.median(ks)) if ks else float("nan")
        m0 = None if not ks else bool(k_med > 1)
        st = dict(k_med=k_med, m0=m0, n_h1=len(d1), n_h2=len(d2), desc=desc,
                  p1=signflip_p(d1) if d1 else float("nan"))
        if m0:
            h1p[X] = st["p1"]
            h2.extend(d2)
        out["settings"][X] = st
    adj = holm(h1p)
    for X in SETTINGS:
        out["settings"][X]["p1_holm"] = adj.get(X, float("nan"))
    out["h2"] = dict(n=len(h2), p=signflip_p(h2) if h2 else float("nan"))
    if m1:
        ratio = np.array([q / p for (_, _, _, q, p) in m1])
        above = int(sum(q > 1 for (_, _, _, q, _) in m1))
        out["m1"] = dict(n=len(m1), q_med=float(np.median(ratio)), above=above,
                         sup=bool(0.5 <= np.median(ratio) <= 2 and above >= 0.8 * len(m1)))
    else:
        out["m1"] = None
    return out


def fmt_p(p):
    return PEND if p != p else (f"{p:.3f}" if p >= 0.001 else f"{p:.1e}")


def macros(a):
    m = {"koCellsTotal": str(N_CELLS), "koCells": str(a["n_cells"]),
         "koStatus": "final" if a["n_cells"] == N_CELLS else "interim"}
    for X, st in a["settings"].items():
        P = f"ko{X}"
        have = st["n_h2"] > 0
        m[P + "Khat"] = f"{st['k_med']:.1f}" if have else PEND
        m[P + "Mzero"] = PEND if st["m0"] is None else ("passed" if st["m0"] else "failed")
        m[P + "HOneN"] = str(st["n_h1"]) if have else PEND
        m[P + "HOneP"] = fmt_p(st["p1_holm"])
        nt = "not tested (manipulation failed)" if st["m0"] is False else None
        m[P + "HOneSup"] = nt or PEND if st["p1_holm"] != st["p1_holm"] else (
            "supported" if st["p1_holm"] <= 0.05 else "not supported")
        for r, tag in (("flame", "Flame"), ("foolsgold", "Fg"), ("fldetector", "Fld"), ("gradcos", "Gc")):
            rows = st["desc"].get(r, [])
            m[P + tag + "DRdef"] = f"{np.mean([x['dr_def'] for x in rows]):.2f}" if rows else PEND
            m[P + tag + "DRfix"] = f"{np.mean([x['dr_fix'] for x in rows]):.2f}" if rows else PEND
    h2 = a["h2"]
    m["koHTwoN"] = str(h2["n"]) if h2["n"] else PEND
    m["koHTwoP"] = fmt_p(h2["p"])
    m["koHTwoSup"] = PEND if h2["p"] != h2["p"] else ("supported" if h2["p"] <= 0.05 else "not supported")
    m1 = a["m1"]
    m["koMOneN"] = str(m1["n"]) if m1 else PEND
    m["koMOneQ"] = f"{m1['q_med']:.2f}" if m1 else PEND
    m["koMOneAbove"] = str(m1["above"]) if m1 else PEND
    m["koMOneSup"] = ("supported" if m1["sup"] else "not supported") if m1 else PEND
    return m


def main():
    a = analyse()
    m = macros(a)
    with open(OUT, "w") as f:
        f.write("% Generated by paper/analyse_k1.py (iterations/PREREG_K1.md). Do not edit.\n")
        for k in sorted(m):
            f.write(f"\\newcommand{{\\{k}}}{{{m[k]}}}\n")
    print(f"K1: {a['n_cells']}/{N_CELLS} cells; wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
