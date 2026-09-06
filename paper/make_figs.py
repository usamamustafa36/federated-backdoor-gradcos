"""Generate the paper figures directly from the committed result files.

Reads results/summary.csv and a handful of per-round result JSONs and writes
publication-ready PDFs into paper/figs/. No pandas dependency (csv module only).
"""
import csv
import json
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "paper", "figs")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.size": 9,
    "font.family": "serif",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.5,
    "axes.axisbelow": True,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "figure.dpi": 300,
})

# --- figure widths -------------------------------------------------------
# These figures were originally drawn for a 3.4 in IEEE two-column layout. The
# manuscript is now Elsevier elsarticle [3p]: single column, \textwidth = 6.5 in.
# Each figure is generated at the width it is actually included at in main.tex,
# so \includegraphics never has to scale it and the label sizes set in rcParams
# above are the sizes that reach the page. Change a width here and the matching
# \includegraphics fraction in main.tex, together.
TEXT_W = 6.5                    # \textwidth of the [3p] layout, inches
W_COL = round(0.68 * TEXT_W, 2)   # single-panel figures   -> 0.68\linewidth
W_WIDE = round(0.88 * TEXT_W, 2)  # bar / multi-seed figures -> 0.88\linewidth
W_PAIR = round(0.95 * TEXT_W, 2)  # two-panel dose-response  -> 0.95\linewidth

DEFENSES = ["fedavg", "krum", "flame", "fltrust", "gradcos"]
LABELS = {"fedavg": "FedAvg", "krum": "Krum", "flame": "FLAME",
          "fltrust": "FLTrust", "gradcos": "GradCos"}
TRIGGERS = ["fixed", "statistical", "temporal"]
# Colour-blind-safe palette (Wong).
COL = {"fedavg": "#555555", "krum": "#E69F00", "flame": "#56B4E9",
       "fltrust": "#009E73", "gradcos": "#D55E00"}


def load_rows():
    with open(os.path.join(RES, "summary.csv"), newline="") as f:
        return list(csv.DictReader(f))


def fnum(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return float("nan")


rows = load_rows()


def cells(dataset, partition, defense, trigger=None, attacked=True):
    out = []
    for r in rows:
        if r["dataset"] != dataset or r["partition"] != partition:
            continue
        if r["defense"] != defense:
            continue
        if (r["attack"] == "True") != attacked:
            continue
        if r["variant"] != "simple":
            continue
        if trigger is not None and r["trigger"] != trigger:
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Figure 1: mean BSR per (defense x trigger), CICIoT2023 IID.
# ---------------------------------------------------------------------------
def fig_bsr_bars():
    fig, ax = plt.subplots(figsize=(W_WIDE, 2.9))
    x = np.arange(len(TRIGGERS))
    w = 0.16
    for i, d in enumerate(DEFENSES):
        vals = []
        for t in TRIGGERS:
            bsr = [fnum(r["BSR"]) for r in cells("ciciot2023", "iid", d, t)]
            vals.append(np.nanmean(bsr) if bsr else np.nan)
        ax.bar(x + (i - 2) * w, vals, w, label=LABELS[d], color=COL[d],
               edgecolor="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels([t.capitalize() for t in TRIGGERS])
    ax.set_ylabel("Mean backdoor success rate")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Trigger type")
    ax.legend(ncol=5, fontsize=7, loc="upper center",
              bbox_to_anchor=(0.5, 1.22), columnspacing=1.0, handlelength=1.2)
    fig.savefig(os.path.join(OUT, "fig_bsr_bars.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2: clean-accuracy vs attacked BSR trade-off (fixed trigger), CICIoT IID.
# ---------------------------------------------------------------------------
def fig_tradeoff():
    fig, ax = plt.subplots(figsize=(W_COL, 3.2))
    for d in DEFENSES:
        clean = cells("ciciot2023", "iid", d, attacked=False)
        ca = np.nanmean([fnum(r["CA"]) for r in clean])
        bsr = np.nanmean([fnum(r["BSR"]) for r in cells("ciciot2023", "iid", d, "fixed")])
        ax.scatter(ca, bsr, s=70, color=COL[d], edgecolor="black",
                   linewidth=0.6, zorder=3)
        dx, dy = 0.006, 0.02
        if d == "gradcos":
            dx, dy = 0.006, -0.05
        if d == "krum":
            dx, dy = -0.02, 0.03
        ax.annotate(LABELS[d], (ca, bsr), (ca + dx, bsr + dy), fontsize=8)
    ax.set_xlabel("Clean accuracy (no attack)")
    ax.set_ylabel("Mean BSR, fixed trigger")
    ax.set_xlim(0.45, 0.78)
    ax.set_ylim(-0.05, 0.75)
    ax.axvspan(0.66, 0.78, alpha=0.06, color="green")
    ax.text(0.72, 0.68, "usable\nmodel", fontsize=6.5, color="green",
            ha="center", va="top")
    fig.savefig(os.path.join(OUT, "fig_tradeoff.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3: BSR vs malicious ratio, fixed trigger, CICIoT IID (avg over poison).
# ---------------------------------------------------------------------------
def fig_ratio():
    fig, ax = plt.subplots(figsize=(W_COL, 3.0))
    ratios = [0.1, 0.2, 0.3]
    for d in DEFENSES:
        ys = []
        for m in ratios:
            vv = [fnum(r["BSR"]) for r in cells("ciciot2023", "iid", d, "fixed")
                  if abs(fnum(r["malicious_ratio"]) - m) < 1e-6]
            ys.append(np.nanmean(vv) if vv else np.nan)
        ax.plot(ratios, ys, "-o", color=COL[d], label=LABELS[d], markersize=4,
                linewidth=1.3)
    ax.set_xlabel("Malicious-client fraction")
    ax.set_ylabel("Mean BSR, fixed trigger")
    ax.set_xticks(ratios)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=7, loc="center left")
    fig.savefig(os.path.join(OUT, "fig_ratio.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4: BSR over training rounds, fixed m0.2 p0.1, CICIoT IID.
# ---------------------------------------------------------------------------
def fig_curves():
    fig, ax = plt.subplots(figsize=(W_COL, 3.0))
    for d in DEFENSES:
        p = os.path.join(RES, f"sweep_ciciot2023_{d}_atk1_m0.2_p0.1_fixed.json")
        if not os.path.exists(p):
            continue
        h = json.load(open(p))["history"]
        ax.plot(h["rounds"], h["bsr"], color=COL[d], label=LABELS[d],
                linewidth=1.2)
    ax.set_xlabel("Communication round")
    ax.set_ylabel("Backdoor success rate")
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=7, loc="center right")
    fig.savefig(os.path.join(OUT, "fig_curves.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5: GradCos detection rate by trigger (why it fails on low-salience).
# ---------------------------------------------------------------------------
def fig_detection():
    fig, ax = plt.subplots(figsize=(W_COL, 3.0))
    x = np.arange(len(TRIGGERS))
    dr = [np.nanmean([fnum(r["DR"]) for r in cells("ciciot2023", "iid", "gradcos", t)])
          for t in TRIGGERS]
    bsr = [np.nanmean([fnum(r["BSR"]) for r in cells("ciciot2023", "iid", "gradcos", t)])
           for t in TRIGGERS]
    ax.bar(x - 0.2, dr, 0.4, label="Detection rate", color="#009E73",
           edgecolor="black", linewidth=0.4)
    ax.bar(x + 0.2, bsr, 0.4, label="Backdoor success", color="#D55E00",
           edgecolor="black", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels([t.capitalize() for t in TRIGGERS])
    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Trigger type (GradCos)")
    ax.legend(fontsize=7, loc="center left")
    fig.savefig(os.path.join(OUT, "fig_detection.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6 (multi-seed): mean BSR +/- std per defense x trigger at the headline
# operating point (m=0.2, p=0.1). Only renders if summary_multiseed.csv exists.
# ---------------------------------------------------------------------------
def load_multiseed():
    p = os.path.join(RES, "summary_multiseed.csv")
    if not os.path.exists(p):
        return None
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def fig_multiseed_headline():
    ms = load_multiseed()
    if not ms:
        print("  (skip fig_multiseed: no summary_multiseed.csv yet)")
        return
    order = ["fedavg", "krum", "flame", "fltrust", "gradcos", "foolsgold"]
    present = [d for d in order if any(
        r["defense"] == d and r["dataset"] == "ciciot2023" and r["partition"] == "iid"
        and r["attack"] in ("True", "true") for r in ms)]
    if not present:
        print("  (skip fig_multiseed: no ciciot iid attack cells yet)")
        return
    fig, ax = plt.subplots(figsize=(W_WIDE, 3.0))
    x = np.arange(len(TRIGGERS))
    w = 0.8 / max(len(present), 1)
    palette = {**COL, "foolsgold": "#CC79A7"}
    for i, d in enumerate(present):
        means, stds = [], []
        for t in TRIGGERS:
            row = [r for r in ms if r["defense"] == d and r["trigger"] == t
                   and r["dataset"] == "ciciot2023" and r["partition"] == "iid"
                   and abs(fnum(r["malicious_ratio"]) - 0.2) < 1e-6
                   and abs(fnum(r["poison_rate"]) - 0.1) < 1e-6
                   and r["attack"] in ("True", "true")]
            means.append(fnum(row[0]["BSR_mean"]) if row else np.nan)
            stds.append(fnum(row[0]["BSR_std"]) if row else 0.0)
        off = (i - (len(present) - 1) / 2) * w
        ax.bar(x + off, means, w, yerr=stds, capsize=2, label=LABELS.get(d, d.capitalize()),
               color=palette.get(d, "#999999"), edgecolor="black", linewidth=0.4,
               error_kw=dict(lw=0.7))
    ax.set_xticks(x)
    ax.set_xticklabels([t.capitalize() for t in TRIGGERS])
    ax.set_ylabel("BSR (mean $\\pm$ s.d.)")
    ax.set_ylim(0, 1.08)
    ax.set_xlabel("Trigger type  (CICIoT2023, IID, $m{=}0.2$, $p{=}0.1$)")
    nseed = max((int(r.get("n_seeds", 0) or 0) for r in ms), default=0)
    ax.legend(ncol=3, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, 1.24),
              columnspacing=1.0, handlelength=1.2, title=f"{nseed} seeds")
    fig.savefig(os.path.join(OUT, "fig_multiseed_headline.pdf"))
    plt.close(fig)




# ---------------------------------------------------------------------------
# Figure 7: detection rate against FALSE-POSITIVE rate, per defense x trigger.
# The paper's tables previously reported DR alone. Plotted against FPR the
# picture changes: FLAME buys its low BSR by flagging ~40% of honest clients,
# and on low-salience triggers GradCos sits on the diagonal, i.e. it flags
# honest and malicious clients at about the same rate.
# ---------------------------------------------------------------------------
def fig_dr_fpr():
    ms = load_multiseed()
    if not ms:
        print("  (skip fig_dr_fpr: no summary_multiseed.csv yet)")
        return
    palette = {**COL, "foolsgold": "#CC79A7"}
    marker = {"fixed": "o", "statistical": "s", "temporal": "^"}
    fig, ax = plt.subplots(figsize=(W_COL, 3.6))
    ax.plot([0, 1], [0, 1], ls=":", lw=0.8, color="#999999", zorder=1)
    ax.annotate("chance", (0.62, 0.58), fontsize=6.5, color="#777777",
                rotation=38)
    seen = set()
    for r in ms:
        if (r["dataset"] != "ciciot2023" or r["partition"] != "iid"
                or r["attack"] not in ("True", "true")
                or abs(fnum(r["malicious_ratio"]) - 0.2) > 1e-6
                or abs(fnum(r["poison_rate"]) - 0.1) > 1e-6):
            continue
        dr, fpr = fnum(r.get("DR_mean")), fnum(r.get("FPR_mean"))
        if np.isnan(dr) or np.isnan(fpr):
            continue          # FedAvg and the coordinate-wise rules never flag
        d, t = r["defense"], r["trigger"]
        ax.scatter(fpr, dr, s=52, marker=marker.get(t, "o"),
                   color=palette.get(d, "#999999"), edgecolor="black",
                   linewidth=0.5, zorder=3,
                   label=LABELS.get(d, d.capitalize()) if d not in seen else None)
        seen.add(d)
    ax.set_xlabel("False-positive rate (honest clients flagged)")
    ax.set_ylabel("Detection rate (malicious flagged)")
    ax.set_xlim(-0.03, 0.55)
    ax.set_ylim(-0.03, 1.05)
    h, l = ax.get_legend_handles_labels()
    shapes = [plt.Line2D([], [], ls="", marker=marker[t], color="#444444",
                         markersize=5, label=t.capitalize()) for t in TRIGGERS]
    ax.legend(h + shapes, l + [t.capitalize() for t in TRIGGERS],
              fontsize=6.2, ncol=2, loc="lower right", handlelength=1.0,
              columnspacing=0.8, labelspacing=0.25)
    fig.savefig(os.path.join(OUT, "fig_dr_fpr.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 8: dose-response along the MEASURED salience axis. Each point is one
# trigger-magnitude cell; x is the salience gap the server actually observed
# (Eq. 1), not the trigger's nominal sigma. This is what turns the salience
# claim from a two-group contrast into an identified axis.
# ---------------------------------------------------------------------------
def fig_dose():
    # The point of this figure is that magnitude is swept at a FIXED feature set
    # and a fixed operating point, so the only thing moving is how hard the trigger
    # pushes. Letting the breadth grid in -- which varies m and p as well -- would
    # scatter several different experiments along one axis and put back exactly the
    # confound the sweep exists to remove.
    pts = [r for r in rows
           if r["dataset"] == "ciciot2023" and r["partition"] == "iid"
           and r["attack"] == "True" and r.get("variant", "simple") == "simple"
           and r.get("seed") == "42"
           and fnum(r.get("malicious_ratio")) == 0.2
           and fnum(r.get("poison_rate")) == 0.1
           and not np.isnan(fnum(r.get("salience_gap")))]
    scales = {r.get("trigger_scale") for r in pts}
    if len(scales) < 3:
        print(f"  (skip fig_dose: only {len(scales)} trigger magnitude(s) on disk -- "
              "run lane 2 of run_remediation.sh)")
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W_PAIR, 2.6), sharex=True)
    # Trigger families touch different features, so they are separate curves: the
    # sweep identifies magnitude *within* a family, not across families.
    MARK = {"fixed": "o", "statistical": "s", "temporal": "^"}
    for d in ["fedavg", "gradcos", "fltrust", "flame"]:
        for t in TRIGGERS:
            sel = sorted((r for r in pts if r["defense"] == d and r["trigger"] == t),
                         key=lambda r: fnum(r["salience_gap"]))
            if len(sel) < 2:
                continue
            xs = [fnum(r["salience_gap"]) for r in sel]
            lab = LABELS.get(d, d) if t == "fixed" else None
            a1.plot(xs, [fnum(r["BSR"]) for r in sel], MARK[t] + "-", ms=3.5, lw=1.2,
                    color=COL.get(d, "#999999"), label=lab)
            drs = [fnum(r["DR"]) for r in sel]
            if not all(np.isnan(v) for v in drs):
                a2.plot(xs, drs, MARK[t] + "-", ms=3.5, lw=1.2,
                        color=COL.get(d, "#999999"))
    a1.set_ylabel("BSR")
    a2.set_ylabel("Detection rate")
    for a in (a1, a2):
        a.set_xlabel("Measured salience gap $S$")
        a.set_ylim(-0.05, 1.05)
    a1.legend(fontsize=7, handlelength=1.2)
    fig.savefig(os.path.join(OUT, "fig_dose.pdf"))
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 9: the adaptive attack's dose-response. x is the decorrelation scale
# lambda; the right panel shows the collusion signal the defenses read
# collapsing as lambda grows, which is the mechanism behind the left panel.
# ---------------------------------------------------------------------------
def fig_evasion():
    pts = [r for r in rows
           if r["dataset"] == "ciciot2023" and r["partition"] == "iid"
           and r["attack"] == "True" and r.get("seed") == "42"
           and fnum(r.get("malicious_ratio")) == 0.2
           and fnum(r.get("poison_rate")) == 0.1
           and r.get("variant") in ("adaptive", "decorrelated", "simple")]
    adaptive = [r for r in pts if r.get("variant") in ("adaptive", "decorrelated")]
    if not adaptive:
        print("  (skip fig_evasion: need the adaptive sweep -- run lane 1 of "
              "run_remediation.sh)")
        return
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W_PAIR, 2.6), sharex=True)
    for d in ["gradcos", "foolsgold", "flame"]:
        sel = [r for r in pts if r["defense"] == d and r["trigger"] == "fixed"]
        # lambda 0 is the static attack
        xy = sorted(((0.0 if r.get("variant") == "simple"
                      else fnum(r.get("evasion_noise"))), r["source_file"], r)
                    for r in sel)
        xy = [(x, r) for x, _, r in xy]
        if len(xy) < 2:
            continue
        xs = [x for x, _ in xy]
        a1.plot(xs, [fnum(r["BSR"]) for _, r in xy], "o-", ms=3.5, lw=1.2,
                color=COL.get(d, "#CC79A7"), label=LABELS.get(d, d.capitalize()))
        a2.plot(xs, [fnum(r.get("mal_pair_cos")) for _, r in xy], "o-", ms=3.5,
                lw=1.2, color=COL.get(d, "#CC79A7"))
    a1.set_ylabel("BSR")
    a1.set_ylim(-0.05, 1.05)
    a2.set_ylabel("Mean pairwise cosine\namong colluders")
    for a in (a1, a2):
        a.set_xlabel("Decorrelation scale $\\lambda$")
    a1.legend(fontsize=7, handlelength=1.2)
    fig.savefig(os.path.join(OUT, "fig_evasion.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig_bsr_bars()
    fig_tradeoff()
    fig_ratio()
    fig_curves()
    fig_detection()
    fig_multiseed_headline()
    # Figures added for the reviewer-remediation pass. Those needing experiments
    # that have not run yet skip themselves with a message naming the lane of
    # run_remediation.sh that produces the data.
    fig_dr_fpr()
    fig_dose()
    fig_evasion()
    print("figures written to", OUT)
