#!/usr/bin/env python3
"""Macros (\\kg*) and a figure for the counter-angle identity (iteration 30; exploratory checks).

Proposition (paper Sec. Mechanisms, proof in the supplement): with q_i = |c_i|^2/|d_i|^2 the
counter's share of client i's squared update norm, theta_i = arccos(sqrt(q_i)), and rho_ij the
cosine of the non-counter blocks,
    1 - cos(d_i, d_j) = [1 - cos(theta_i - theta_j)] + sin(theta_i) sin(theta_j) (1 - rho_ij).
With equal counters inside each group (IID shards), k = sin(theta_m)/sin(theta_h) ~ t / E, where
t is the attackers' trainable-norm ratio and E their batch-count ratio, and
    (1 - cos_mm)/(1 - cos_hh)  [defect]  =  k^2 (1 - rho_mm)/(1 - rho_hh).
Check 1 (campaign cells, P3): per paired seed, the defect arm's attacker-pair / honest-pair
cosine-distance ratio (full vector) over the fixed arm's (trainable), against the prediction
(t/E)^2 with t the fixed arm's logged mal_norm_ratio and E = 15. Rounds 2-15, per-seed medians.
P3X held-out cells (iterations/PREREG_P3X.md) are excluded, whether or not they exist.
Check 2 (FLAME probe, results/flame_probe/flame_iid_s42.jsonl): k from per-client norms against
t / (counter ratio); the identity's full-vector distances computed from per-client norms and the
logged trainable cosines against the logged full-vector ones; and the typicality ratio
Lambda = (Phi + k (1 - rho_mh)) / (1 - rho_hh), Phi = [1 - cos(theta_m - theta_h)]/sin^2(theta_h),
against which rounds FLAME's majority cluster admits an attacker. L = 1 BatchNorm layer here.
Missing input -> \\PENDING.
"""
import glob
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RES = os.path.join(ROOT, "results", "postfix_p3")
PROBE = os.path.join(ROOT, "results", "flame_probe", "flame_iid_s42.jsonl")
OUT = os.path.join(HERE, "numbers_kgeom.tex")
FIG = os.path.join(HERE, "figs", "fig_kgeom.pdf")
E = 15.0
HELD_OUT = {("dirichlet", "fldetector", s) for s in range(47, 52)} | \
           {("dirichlet", "alignins", s) for s in range(47, 52)} | \
           {("iid", "alignins", s) for s in range(42, 47)} | \
           {("iid", "foolsgold", s) for s in range(47, 52)}
PAT = re.compile(r"p3(full|trainable)_(iid|dirichlet)_ciciot2023_(\w+?)_atk1_.*_me15_sm_s(\d+)\.json$")
PEND = "\\PENDING"


def cell_stats(path):
    h = json.load(open(path))["history"]
    mm = np.array(h["mal_pair_cos"][1:], float)
    hh = np.array(h["honest_pair_cos"][1:], float)
    nr = np.array(h["mal_norm_ratio"][1:], float)
    return float(np.nanmedian((1 - mm) / (1 - hh))), float(np.nanmedian(nr))


def campaign():
    cells = {}
    for f in glob.glob(os.path.join(RES, "p3*_atk1_*.json")):
        m = PAT.search(os.path.basename(f))
        if not m or os.path.getsize(f) == 0:
            continue
        arm, part, rule, seed = m.group(1), m.group(2), m.group(3), int(m.group(4))
        if (part, rule, seed) in HELD_OUT:
            continue
        try:
            cells[(part, rule, seed, arm)] = cell_stats(f)
        except Exception:
            continue
    pairs = {"iid": [], "dirichlet": []}
    for (part, rule, seed, arm), (r_def, _) in cells.items():
        if arm != "full" or (part, rule, seed, "trainable") not in cells:
            continue
        r_fix, t = cells[(part, rule, seed, "trainable")]
        pairs[part].append((rule, seed, r_def / r_fix, (t / E) ** 2))
    return pairs


def probe():
    if not os.path.exists(PROBE):
        return None
    out = []
    for line in open(PROBE):
        if not line.strip():
            continue
        r = json.loads(line)
        mal = np.array(r["mal"], bool)
        s, B, tr = (np.array(r[k], float) for k in ("buf_share", "counter", "tr_norm"))
        d2 = tr ** 2 / (1 - s)
        th = np.arccos(np.sqrt(B ** 2 / d2))
        tm, th_ = th[mal].mean(), th[~mal].mean()
        k = np.sin(tm) / np.sin(th_)
        k_pred = (np.median(tr[mal]) / np.median(tr[~mal])) / (np.median(B[mal]) / np.median(B[~mal]))
        T, F = r["trainable"], r["full"]
        mis = 1 - np.cos(tm - th_)
        pred = {"hh": np.sin(th_) ** 2 * (1 - T["hh"]),
                "mh": mis + np.sin(tm) * np.sin(th_) * (1 - T["mh"]),
                "mm": np.sin(tm) ** 2 * (1 - T["mm"])}
        rel = {g: (1 - F[g]) / pred[g] - 1 for g in pred}
        lam = (mis / np.sin(th_) ** 2 + k * (1 - T["mh"])) / (1 - T["hh"])
        adm = any(mal[i] for i in F["admitted"])
        out.append(dict(rnd=r["round"], k=k, k_pred=k_pred, rel=rel, lam=lam, adm=adm))
    return out


def fig(pairs):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_, ax = plt.subplots(figsize=(3.4, 2.5))
    for part, mk, col, lab in (("iid", "o", "C0", "IID"), ("dirichlet", "s", "C1", "Dirichlet")):
        if pairs[part]:
            x = [p[3] for p in pairs[part]]
            y = [p[2] for p in pairs[part]]
            ax.scatter(x, y, s=10, marker=mk, color=col, alpha=0.7, label=f"{lab} ({len(x)} pairs)")
    lo, hi = 3e-3, 0.4
    ax.plot([lo, hi], [lo, hi], "k-", lw=0.8, label=r"observed $=(t/E)^2$")
    ax.fill_between([lo, hi], [lo / 2, hi / 2], [lo * 2, hi * 2], color="0.85", zorder=0,
                    label="within a factor 2")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(0.02, 0.4); ax.set_ylim(3e-3, 0.4)
    ax.set_xlabel(r"predicted $k^2=(t/E)^2$ (fixed arm's $t$, $E=15$)")
    ax.set_ylabel("defect / fixed attacker\nmutual-distance ratio")
    ax.legend(fontsize=6, loc="lower right", frameon=False)
    ax.tick_params(labelsize=7); ax.xaxis.label.set_size(7); ax.yaxis.label.set_size(7)
    fig_.tight_layout()
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig_.savefig(FIG)


def main():
    m = {}
    P = m.__setitem__
    pairs = campaign()
    for part, tag in (("iid", "Iid"), ("dirichlet", "Dir")):
        ps = pairs[part]
        if not ps:
            for k in ("N", "Rules", "ObsMed", "PredMed", "QMed", "QMin", "QMax", "InTwo", "Below"):
                P(tag + k, PEND)
            continue
        q = np.array([p[2] / p[3] for p in ps])
        P(tag + "N", str(len(ps)))
        P(tag + "Rules", str(len({p[0] for p in ps})))
        P(tag + "ObsMed", f"{np.median([p[2] for p in ps]):.3f}")
        P(tag + "PredMed", f"{np.median([p[3] for p in ps]):.3f}")
        P(tag + "QMed", f"{np.median(q):.2f}")
        P(tag + "QMin", f"{q.min():.2f}")
        P(tag + "QMax", f"{q.max():.2f}")
        P(tag + "InTwo", str(int(((q >= 0.5) & (q <= 2)).sum())))
        P(tag + "Below", str(int((q < 1).sum())))
    pr = probe()
    keys = ("PrRounds", "PrKErr", "PrRelMax", "PrRelMaxHh", "PrAdmN", "PrLamAdmMax", "PrLamNoMin",
            "PrLamFirst", "PrSep")
    if not pr:
        for k in keys:
            P(k, PEND)
    else:
        late = [r for r in pr if r["rnd"] >= 2]  # round 1: round-one aliasing (Sec. setup)
        P("PrRounds", str(len(late)))
        P("PrKErr", f"{100 * max(abs(r['k_pred'] / r['k'] - 1) for r in late):.0f}")
        P("PrRelMax", f"{100 * max(max(abs(r['rel']['mh']), abs(r['rel']['mm'])) for r in late):.0f}")
        P("PrRelMaxHh", f"{100 * max(abs(r['rel']['hh']) for r in late):.0f}")
        adm = [r for r in late if r["adm"]]
        no = [r for r in late if not r["adm"]]
        P("PrAdmN", str(len(adm)))
        P("PrLamAdmMax", f"{max(r['lam'] for r in adm):.2f}" if adm else "--")
        P("PrLamNoMin", f"{min(r['lam'] for r in no):.2f}" if no else "--")
        P("PrLamFirst", f"{late[0]['lam']:.1f}")
        P("PrSep", "yes" if adm and no and max(r['lam'] for r in adm) < min(r['lam'] for r in no) else "no")
    fig(pairs)
    lines = ["% generated by paper/make_numbers_kgeom.py -- do not edit"]
    lines += [f"\\providecommand{{\\kg{k}}}{{{v}}}" for k, v in sorted(m.items())]
    open(OUT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
