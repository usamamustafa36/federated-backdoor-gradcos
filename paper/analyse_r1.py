"""R1 analysis, exactly as registered in iterations/PREREG_R1.md (iteration 24).

Reads results/r1_falsify, applies the pre-registered tests and writes
paper/numbers_r1.tex (\\rO... macros; \\PENDING where a cell is missing) and
results/r1_falsify/summary.json.

Tests: exact ONE-sided paired sign-flip of the mean seed-paired difference
(defect - fixed) in the predicted direction (+), Holm within each family.
  primary   (variant A): final-round BSR, FLTrust / Multi-Krum / Krum
  mechanism (variant A): FLTrust mean mal_step_share; Multi-Krum, Krum admission
                         rate (1 - mean DR over rounds)
Exploratory (no tests): A-defect vs B-defect (BSR and the mechanism quantity), variant
C defect vs fixed (BSR, CA, mechanism quantity), FPR, FedAvg reference.
The primary family is flagged uninformative if the pilot rule took its b* = 2 branch
(no b reached mean pilot BSR 0.5; Amendment 3 item 1) or if the FedAvg reference's
median final BSR (campaign seeds) is < 0.2, whatever its p-values.

    python3 paper/analyse_r1.py [--res results/r1_falsify] [--out paper/numbers_r1.tex]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyse_postfix import holm, signflip_p_one  # noqa: E402

SEEDS = list(range(42, 52))
RULES = [("fltrust", "Flt", "share"), ("krum", "Mk", "median"), ("krum1", "Kr", "median")]
PEND = r"\PENDING"


def fname(res, arm, d, pol, nb, seed):
    cp = "" if pol == "honest" else f"_cp{pol}"
    nbs = "" if not nb else f"_nb{nb:g}"
    return os.path.join(res, f"r1{arm}_dirichlet_ciciot2023_{d}_atk1_m0.2_p0.1_fixed"
                             f"_me15_sm{cp}{nbs}_s{seed}.json")


def load(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return None
    h = json.load(open(path))["history"]
    dr = [x for x in h.get("detection_rate", []) if x is not None and not math.isnan(x)]
    fpr = [x for x in h.get("false_positive_rate", []) if x is not None and not math.isnan(x)]
    ms = [r.get("mal_step_share") for r in h.get("counter_attack", [])]
    ms = [x for x in ms if x is not None and not math.isnan(x)]
    return {"bsr": float(h["bsr"][-1]), "ca": float(h["accuracy"][-1]),
            "adm": (1.0 - float(np.mean(dr))) if dr else float("nan"),
            "fpr": float(np.mean(fpr)) if fpr else float("nan"),
            "mss": float(np.mean(ms)) if ms else float("nan")}


def b_star(res):
    try:
        out = subprocess.run([sys.executable, "experiments/r1_falsify/choose_b.py", res],
                             capture_output=True, text=True, check=False)
    except OSError:
        return None, ""
    lines = out.stdout.strip().splitlines()
    if out.returncode != 0 or not lines or not lines[-1].startswith("B="):
        return None, out.stdout
    return float(lines[-1][2:]), out.stdout


def paired(res, d, pol, nb, key, arm_a=("full", None), arm_b=("trainable", None)):
    """-> (diffs, values_a, values_b) over the seeds where both cells exist."""
    da, va, vb = [], [], []
    for s in SEEDS:
        a = load(fname(res, arm_a[0], d, arm_a[1] or pol, nb, s))
        b = load(fname(res, arm_b[0], d, arm_b[1] or pol, nb, s))
        if a is None or b is None or math.isnan(a[key]) or math.isnan(b[key]):
            continue
        va.append(a[key]); vb.append(b[key]); da.append(a[key] - b[key])
    return np.array(da), np.array(va), np.array(vb)


def fmt(x, nd=3):
    return PEND if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="results/r1_falsify")
    ap.add_argument("--out", default="paper/numbers_r1.tex")
    a = ap.parse_args()
    B, sel = b_star(a.res)
    mac, summ = {}, {"b_star": B, "choose_b": sel, "families": {}}
    mac["rOneBstar"] = PEND if B is None else f"{B:g}"
    n_present = sum(1 for f in os.listdir(a.res) if f.startswith("r1full_") or
                    f.startswith("r1trainable_")) if os.path.isdir(a.res) else 0
    mac["rOneCellsDone"] = str(n_present)
    mac["rOneCellsTarget"] = "160"
    fams = {"prim": [], "mech": []}
    for d, tag, pol in RULES:
        for fam, key in (("prim", "bsr"), ("mech", "mss" if d == "fltrust" else "adm")):
            if B is None:
                diffs = np.array([]); va = vb = diffs
            else:
                diffs, va, vb = paired(a.res, d, pol, B, key)
            n = len(diffs)
            p = signflip_p_one(diffs, +1) if n >= 1 else float("nan")
            fams[fam].append(dict(rule=d, tag=tag, key=key, n=n, p=p,
                                  pos=int((diffs > 0).sum()), neg=int((diffs < 0).sum()),
                                  defect=float(va.mean()) if n else float("nan"),
                                  fixed=float(vb.mean()) if n else float("nan"),
                                  diff=float(diffs.mean()) if n else float("nan")))
    for fam, rows in fams.items():
        # untested hypotheses enter with p = 1 (as for P3), so Holm's multiplier is 3
        ph = holm([r["p"] if not math.isnan(r["p"]) else 1.0 for r in rows])
        F = "Prim" if fam == "prim" else "Mech"
        for r, h in zip(rows, ph):
            r["p_holm"] = h if r["n"] else float("nan")
            r["supported"] = bool(r["n"] and h < 0.05)
            k = f"rOne{F}{r['tag']}"
            mac[k + "Def"] = fmt(r["defect"]); mac[k + "Fix"] = fmt(r["fixed"])
            mac[k + "Diff"] = fmt(r["diff"]); mac[k + "N"] = str(r["n"])
            mac[k + "Pos"] = str(r["pos"]); mac[k + "Neg"] = str(r["neg"])
            mac[k + "P"] = fmt(r["p"], 4); mac[k + "Ph"] = fmt(r["p_holm"], 4)
        summ["families"][fam] = rows
    # FedAvg reference (fixed arm, b*, honest counter): informativeness gate
    ref = [] if B is None else [x["bsr"] for x in
                                 (load(fname(a.res, "trainable", "fedavg", "honest", B, s))
                                  for s in SEEDS) if x is not None]
    med = float(np.median(ref)) if ref else float("nan")
    mac["rOneRefN"] = str(len(ref)); mac["rOneRefBSRmed"] = fmt(med)
    summ["fedavg_ref"] = {"n": len(ref), "median_bsr": med,
                          "primary_uninformative": bool(ref and med < 0.2)}
    # pilot rule (PREREG_R1, Amendment 3 item 1): if no b in {1,2} reached a mean pilot
    # FedAvg BSR of 0.5, the primary (BSR) family is uninformative whatever the gate says
    pil = {}
    for ln in sel.splitlines():
        if ln.startswith("b=") and "mean" in ln:
            pil[float(ln[2:ln.index(":")])] = float(ln.rsplit("mean", 1)[1])
    unin_pilot = bool(pil) and max(pil.values()) < 0.5
    mac["rOnePilotBSRbOne"] = fmt(pil.get(1.0)); mac["rOnePilotBSRbTwo"] = fmt(pil.get(2.0))
    summ["primary_uninformative_pilot"] = unin_pilot
    summ["primary_uninformative"] = unin_pilot or summ["fedavg_ref"]["primary_uninformative"]
    mac["rOnePrimUninf"] = "uninformative" if summ["primary_uninformative"] else "informative"
    # exploratory (Amendment 3 item 3; no tests): sign counts and mean paired differences
    summ["exploratory"] = {}
    for d, tag, pol in RULES:
        mk = "mss" if d == "fltrust" else "adm"
        for lab, key, kw in (
                ("AvB", "bsr", dict(arm_a=("full", pol), arm_b=("full", "honest"))),
                ("AvBMech", mk, dict(arm_a=("full", pol), arm_b=("full", "honest"))),
                ("C", "bsr", dict(nb_override=0)),
                ("CMech", mk, dict(nb_override=0)),
                ("CCa", "ca", dict(nb_override=0))):
            if B is None:
                mac[f"rOne{lab}{tag}Diff"] = PEND; mac[f"rOne{lab}{tag}N"] = "0"; continue
            nb = 0 if kw.pop("nb_override", None) == 0 else B
            diffs, va, vb = paired(a.res, d, pol, nb, key, **kw)
            n = len(diffs)
            row = dict(n=n, pos=int((diffs > 0).sum()), neg=int((diffs < 0).sum()),
                       a=float(va.mean()) if n else float("nan"),
                       b=float(vb.mean()) if n else float("nan"),
                       diff=float(diffs.mean()) if n else float("nan"))
            summ["exploratory"][f"{lab}_{d}"] = row
            mac[f"rOne{lab}{tag}Diff"] = fmt(row["diff"]); mac[f"rOne{lab}{tag}N"] = str(n)
            mac[f"rOne{lab}{tag}A"] = fmt(row["a"]); mac[f"rOne{lab}{tag}B"] = fmt(row["b"])
            mac[f"rOne{lab}{tag}Pos"] = str(row["pos"]); mac[f"rOne{lab}{tag}Neg"] = str(row["neg"])
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        f.write("% Generated by paper/analyse_r1.py from results/r1_falsify "
                "(iterations/PREREG_R1.md). Do not edit.\n")
        for k, v in sorted(mac.items()):
            f.write(f"\\providecommand{{\\{k}}}{{{v}}}\n")
    if os.path.isdir(a.res):
        json.dump(summ, open(os.path.join(a.res, "summary.json"), "w"), indent=2, default=str)
    for fam, rows in fams.items():
        for r in rows:
            print(f"  R1 {fam:4s} {r['rule']:7s} {r['key']:3s} n={r['n']:2d} "
                  f"{r['pos']}/{r['neg']} def={r['defect']:.3f} fix={r['fixed']:.3f} "
                  f"p1={r['p']:.4g} holm={r['p_holm']:.4g}")
    print(f"R1: primary family {mac['rOnePrimUninf']} (pilot rule {unin_pilot}, gate "
          f"{summ['fedavg_ref']['primary_uninformative']})")
    print(f"R1: b*={B}, {n_present}/160 cells, FedAvg ref n={len(ref)} median BSR {med:.3f}"
          f" -> {a.out}")


if __name__ == "__main__":
    main()
