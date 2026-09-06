"""Emit paper/numbers.tex: every number the manuscript quotes, as a LaTeX macro
computed from the committed result files.

The paper states in Sec. "Experimental Setup" that nothing is hand-entered. This
script is what makes that true. Run it after any sweep, then rebuild:

    python3 paper/aggregate_multiseed.py      # per-seed JSONs -> summary_multiseed.csv
    python3 -m experiments.make_tables        # single-seed JSONs -> summary.csv
    python3 paper/make_numbers.py             # both CSVs -> paper/numbers.tex
    cd paper && pdflatex main

A cell that has not been run yet emits \PENDING rather than a number, so an
unfinished claim is loud in the PDF instead of silently wrong. `--strict` exits
non-zero if any macro is still \PENDING, which is the submission gate.

Macro naming is `\<family><Metric><Defense><Axis>`, letters only (TeX csnames
cannot contain digits or underscores):

    \msBSRgradcosFixed        multi-seed headline BSR, GradCos, fixed trigger
    \msBSRsdgradcosFixed      ... and its standard deviation
    \msCleanCAgradcos         clean (no-attack) accuracy
    \adBSRgradcosAdaptive     adaptive-attacker lane
    \mgBSRmedianStatistical   magnitude/order-statistic defenses
    \gridBSRgradcosFixed      mean over the single-seed breadth grid
    \ratBSRkrumThirty         malicious-ratio sweep
    \flBSRgradcosFixed        FLNET2023
    \niBSRgradcosFixed        non-IID (Dirichlet)
"""
import argparse
import re
import csv
import json
import math
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "paper", "numbers.tex")

MULTI = os.path.join(RES, "summary_multiseed.csv")
SINGLE = os.path.join(RES, "summary.csv")

DIRECTION = ["fedavg", "krum", "flame", "fltrust", "foolsgold", "gradcos"]
MAGNITUDE = ["median", "trimmedmean", "rfa", "bulyan", "normclip"]
TRIGGERS = ["fixed", "statistical", "temporal"]
VARIANTS = ["simple", "decorrelated", "adaptive"]

# TeX csnames take letters only, so every axis value needs a spelled-out form.
WORD = {
    "fixed": "Fixed", "statistical": "Statistical", "temporal": "Temporal",
    "simple": "Simple", "decorrelated": "Decorrelated", "adaptive": "Adaptive",
    "trimmedmean": "trimmedmean",
    "0.1": "Ten", "0.2": "Twenty", "0.3": "Thirty",
    "0.05": "Five",
    "0.25": "Quarter", "0.5": "Half", "1.0": "One", "1.5": "OneHalf",
    "2.0": "Two", "3.0": "Three",
}


def w(x):
    """Axis value -> a TeX-safe word."""
    s = str(x)
    if s in WORD:
        return WORD[s]
    return "".join(ch for ch in s.title() if ch.isalpha()) or "X"


def fnum(v, places=3):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f):
        return None
    return f"{f:.{places}f}"


def fpct(v, places=0):
    f = fnum(v, 6)
    if f is None:
        return None
    return f"{float(f) * 100:.{places}f}"


def load(path):
    if not os.path.exists(path):
        print(f"  ! missing {os.path.relpath(path, ROOT)} — its macros will be \\PENDING")
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def truthy(v):
    return str(v).strip().lower() in ("true", "1", "yes")


def approx(v, target):
    """Float-tolerant match for the numeric axis columns."""
    if target is None:
        return True
    try:
        return abs(float(v) - float(target)) < 1e-9
    except (TypeError, ValueError):
        return str(v).strip() == str(target)


def blank_or(v, default):
    """Sweep columns are empty for cells predating the axis; treat empty as default."""
    s = str(v).strip()
    return default if s in ("", "nan", "None") else s


class Emitter:
    def __init__(self):
        self.lines = []
        self.pending = []
        self.defined = set()

    def macro(self, name, value, note=""):
        if name in self.defined:
            raise SystemExit(f"duplicate macro \\{name} — naming collision, fix make_numbers.py")
        self.defined.add(name)
        if value is None:
            self.pending.append(name)
            body = r"\PENDING{}"
        else:
            body = value
        comment = f"  % {note}" if note else ""
        self.lines.append(rf"\newcommand{{\{name}}}{{{body}}}{comment}")

    def section(self, title):
        self.lines.append("")
        self.lines.append(f"% ---- {title} " + "-" * max(0, 66 - len(title)))


def pick(rows, **crit):
    """First row matching every criterion; None if the cell has not been run."""
    for r in rows:
        ok = True
        for k, v in crit.items():
            if v is None:
                continue
            cell = r.get(k)
            if k in ("attack",):
                ok = truthy(cell) == bool(v)
            elif k in ("malicious_ratio", "poison_rate", "trigger_scale", "evasion_noise"):
                default = "1.0" if k == "trigger_scale" else "0.0"
                ok = approx(blank_or(cell, default), v)
            elif k == "variant":
                ok = blank_or(cell, "simple") == v
            elif k == "trigger_mode":
                ok = blank_or(cell, "sigma") == v
            else:
                ok = str(cell).strip() == str(v)
            if not ok:
                break
        if ok:
            return r
    return None


def mean_over(rows, field, **crit):
    """Mean of `field` over every row matching the criteria (grid aggregates)."""
    vals = []
    for r in rows:
        ok = True
        for k, v in crit.items():
            if v is None:
                continue
            cell = r.get(k)
            if k == "attack":
                ok = truthy(cell) == bool(v)
            elif k in ("malicious_ratio", "poison_rate", "trigger_scale", "evasion_noise"):
                default = "1.0" if k == "trigger_scale" else "0.0"
                ok = approx(blank_or(cell, default), v)
            elif k == "variant":
                ok = blank_or(cell, "simple") == v
            elif k == "trigger_mode":
                ok = blank_or(cell, "sigma") == v
            else:
                ok = str(cell).strip() == str(v)
            if not ok:
                break
        if not ok:
            continue
        f = fnum(r.get(field), 9)
        if f is not None:
            vals.append(float(f))
    if not vals:
        return None, 0
    return sum(vals) / len(vals), len(vals)


GRID_SEED = "42"      # the canonical seed for every single-seed cell
GRID_TAG = "sweep"    # breadth-grid runs; "ms" is the multi-seed campaign


# Which run a cell is taken from when several ran the same configuration at the
# canonical seed. `sweep` is the breadth grid and stays authoritative; `rem` is
# the remediation campaign and is the current code, so it outranks the older
# multi-seed replicate `ms`. Lower is better.
TAG_RANK = {GRID_TAG: 0, "rem": 1, "ms": 2}


def _tag_rank(row) -> int:
    return TAG_RANK.get(str(row.get("run_tag")), 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any macro is still \\PENDING (submission gate)")
    args = ap.parse_args()

    print("reading result summaries")
    ms = load(MULTI)
    ss = load(SINGLE)
    e = Emitter()

    # The five per-seed replicates of the headline point sit in results/ alongside
    # the single-seed breadth grid, so every lookup against summary.csv pins the
    # canonical seed; otherwise a grid mean quietly averages the replicates in.
    # The multi-seed campaign re-runs the headline configuration at seed 42, so
    # results/ holds two files for that one cell and `seed` alone cannot tell them
    # apart. Deduplicate on the configuration key, preferring the breadth-grid run
    # and falling back to the campaign's seed-42 file where the grid never ran the
    # cell -- same config, same seed, same code, so it is the same experiment, and
    # dropping it would leave one defense averaged over 8 cells and the rest over 9.
    ss_grid = {}
    for r in ss:
        if str(r.get("seed")) != GRID_SEED:
            continue
        key = tuple(str(r.get(k)) for k in
                    ("dataset", "partition", "defense", "defense_variant", "attack",
                     "trigger", "malicious_ratio", "poison_rate", "variant",
                     "trigger_scale", "trigger_mode", "evasion_noise"))
        # Preference must be explicit. It used to be "take the grid tag, else
        # whatever arrived first", and load_results yields files in filename
        # order -- so where a cell had both an `ms` replicate and a `rem`
        # remediation run and no `sweep` row, `ms_` won on alphabetical order
        # alone and silently discarded the only row carrying update geometry.
        # That left adMalCos*/adHonCos*/adNormRatio*/msSal* PENDING even after
        # the lane that produces them had run. Rank the tags instead, newest
        # code last-resort-first, and never let sort order decide.
        if key not in ss_grid or _tag_rank(r) < _tag_rank(ss_grid[key]):
            ss_grid[key] = r
    ss_grid = list(ss_grid.values())
    print(f"  single-seed view: {len(ss_grid)} cells "
          f"(from {len(ss)} rows, seed {GRID_SEED}, deduplicated)")

    def spick(**crit):
        return pick(ss_grid, **crit)

    def smean(field, **crit):
        return mean_over(ss_grid, field, **crit)

    e.lines.append("% GENERATED FILE — DO NOT EDIT. Regenerate with: python3 paper/make_numbers.py")
    e.lines.append("% Source: results/summary_multiseed.csv, results/summary.csv")
    e.lines.append(r"% Any \PENDING below is a cell that has not been run yet.")

    # `evasion_noise` is recorded from the config default (1.0) on every run, so it
    # only identifies a cell when the variant actually uses it; it is therefore not
    # part of the static-cell key.
    HEAD = dict(dataset="ciciot2023", partition="iid",
                malicious_ratio="0.2", poison_rate="0.1",
                variant="simple", trigger_scale="1.0", trigger_mode="sigma")

    # ---- multi-seed headline -------------------------------------------------
    e.section("multi-seed headline (CICIoT2023, IID, m=0.2, p=0.1, seeds 42-46)")
    for d in DIRECTION:
        clean = pick(ms, defense=d, attack=False, dataset="ciciot2023", partition="iid")
        e.macro(f"msCleanCA{d}", fnum(clean and clean.get("CA_mean")), f"{d} clean accuracy")
        e.macro(f"msCleanFone{d}", fnum(clean and clean.get("macro_f1_mean")), f"{d} clean macro-F1")
        for t in TRIGGERS:
            r = pick(ms, defense=d, attack=True, trigger=t, **HEAD)
            for metric, key in (("BSR", "BSR"), ("DR", "DR"), ("FPR", "FPR"), ("CA", "CA")):
                places = 2 if metric in ("DR", "FPR") else 3
                e.macro(f"ms{metric}{d}{w(t)}", fnum(r and r.get(f"{key}_mean"), places))
                e.macro(f"ms{metric}sd{d}{w(t)}", fnum(r and r.get(f"{key}_std"), places))
            # Seed range, not just dispersion. Sec. 7.11 argues from the spread
            # of a bimodal cell ("BSR range 0.003-0.926"), and that range was
            # hand-typed; generate it so the argument cannot drift from the data.
            # The abstract quotes FLAME's false-positive rate as a percentage.
            e.macro(f"ms{'FPR'}pct{d}{w(t)}", fpct(r and r.get("FPR_mean")))
            e.macro(f"msBSRmin{d}{w(t)}", fnum(r and r.get("BSR_min")))
            e.macro(f"msBSRmax{d}{w(t)}", fnum(r and r.get("BSR_max")))
            e.macro(f"msSal{d}{w(t)}", fnum(r and r.get("salience_gap_mean")),
                    "measured salience gap")
            e.macro(f"msNseeds{d}{w(t)}", (r or {}).get("n_seeds") or None)

    # The "+0.15 clean accuracy" the abstract, the introduction and Sec. 7.9 all
    # quote is GradCos's clean CA minus FLTrust's -- a derived number that was
    # hand-typed in three places. Derive it once.
    _ca_g = pick(ms, defense="gradcos", attack=False, dataset="ciciot2023", partition="iid")
    _ca_f = pick(ms, defense="fltrust", attack=False, dataset="ciciot2023", partition="iid")
    try:
        _adv = float(_ca_g["CA_mean"]) - float(_ca_f["CA_mean"])
    except (TypeError, KeyError, ValueError):
        _adv = None
    e.macro("msCAadvGradcos", fnum(_adv, 2), "gradcos clean CA over fltrust")

    # FLAME's clean-accuracy deficit against undefended FedAvg, quoted in the
    # abstract. Derived, so it cannot drift from the headline table.
    _ca_a = pick(ms, defense="fedavg", attack=False, dataset="ciciot2023", partition="iid")
    _ca_l = pick(ms, defense="flame", attack=False, dataset="ciciot2023", partition="iid")
    try:
        _def = float(_ca_a["CA_mean"]) - float(_ca_l["CA_mean"])
    except (TypeError, KeyError, ValueError):
        _def = None
    e.macro("msCAdeficitFlame", fnum(_def, 2), "flame clean CA below fedavg")

    # ---- adaptive attacker (lane 1a/1b) --------------------------------------
    e.section("adaptive attacker: static vs decorrelated vs adaptive")
    for d in DIRECTION:
        for v in VARIANTS:
            crit = dict(HEAD)
            crit["variant"] = v
            if v != "simple":
                crit["evasion_noise"] = "1.0"
            # Fall back per FIELD, not per row. The multi-seed campaign predates
            # the per-round geometry logging, so its row exists but carries NaN
            # for mal_pair_cos / honest_pair_cos / mal_norm_ratio / salience_gap.
            # A row-level `or` short-circuits on that row and reports PENDING for
            # geometry that the single-seed remediation run does have on disk.
            cand = [pick(ms, defense=d, attack=True, trigger="fixed", **crit),
                    spick(defense=d, attack=True, trigger="fixed", **crit)]

            def g(field, cand=cand):
                for row in cand:
                    if row is None:
                        continue
                    v = row.get(f"{field}_mean", row.get(field))
                    if v is None:
                        continue
                    try:
                        if float(v) != float(v):      # NaN
                            continue
                    except (TypeError, ValueError):
                        if str(v).strip() == "":
                            continue
                    return v
                return None
            e.macro(f"adBSR{d}{w(v)}", fnum(g("BSR")))
            e.macro(f"adDR{d}{w(v)}", fnum(g("DR"), 2))
            e.macro(f"adFPR{d}{w(v)}", fnum(g("FPR"), 2))
            e.macro(f"adCA{d}{w(v)}", fnum(g("CA")))
            e.macro(f"adMalCos{d}{w(v)}", fnum(g("mal_pair_cos")))
            e.macro(f"adHonCos{d}{w(v)}", fnum(g("honest_pair_cos")))
            e.macro(f"adNormRatio{d}{w(v)}", fnum(g("mal_norm_ratio"), 2))
        # evasion-noise dose-response
        for lam in ("0.25", "0.5", "1.0", "2.0"):
            crit = dict(HEAD)
            crit["variant"] = "adaptive"
            crit["evasion_noise"] = lam
            r = pick(ms, defense=d, attack=True, trigger="fixed", **crit) \
                or spick(defense=d, attack=True, trigger="fixed", **crit)
            e.macro(f"evBSR{d}{w(lam)}", fnum(r and (r.get("BSR_mean", r.get("BSR")))))
            e.macro(f"evMalCos{d}{w(lam)}",
                    fnum(r and (r.get("mal_pair_cos_mean", r.get("mal_pair_cos")))))

    # ---- GradCos residual variant (lane 1c) ----------------------------------
    e.section("GradCos residual variant, static vs adaptive")
    for v in ("simple", "adaptive"):
        crit = dict(HEAD)
        crit["variant"] = v
        if v != "simple":
            crit["evasion_noise"] = "1.0"
        for t in TRIGGERS:
            r = pick(ms, defense="gradcos", defense_variant="residual",
                     attack=True, trigger=t, **crit) \
                or spick(defense="gradcos", defense_variant="residual",
                         attack=True, trigger=t, **crit)

            def g(field, r=r):
                if r is None:
                    return None
                return r.get(f"{field}_mean", r.get(field))

            def sd(field, r=r):
                # Only the multi-seed rows carry dispersion; a single-seed
                # fallback has none to report, and must not silently read 0.
                return None if r is None else r.get(f"{field}_std")
            e.macro(f"resBSR{w(v)}{w(t)}", fnum(g("BSR")))
            e.macro(f"resBSRsd{w(v)}{w(t)}", fnum(sd("BSR")))
            e.macro(f"resDR{w(v)}{w(t)}", fnum(g("DR"), 2))
            e.macro(f"resFPR{w(v)}{w(t)}", fnum(g("FPR"), 2))
            e.macro(f"resCA{w(v)}{w(t)}", fnum(g("CA")))

    # ---- magnitude / order-statistic defenses (lane 3) -----------------------
    e.section("magnitude and order-statistic rules (the non-cosine control family)")
    for d in MAGNITUDE:
        clean = spick(defense=d, attack=False, dataset="ciciot2023", partition="iid")
        e.macro(f"mgCleanCA{d}", fnum(clean and clean.get("CA")))
        for t in TRIGGERS:
            r = spick(defense=d, attack=True, trigger=t, **HEAD)
            e.macro(f"mgBSR{d}{w(t)}", fnum(r and r.get("BSR")))
            e.macro(f"mgCA{d}{w(t)}", fnum(r and r.get("CA")))
            e.macro(f"mgSal{d}{w(t)}", fnum(r and r.get("salience_gap")))

    # ---- trigger realizability audit ----------------------------------------
    # Table 3 and the whole of Sec. 4.1 were hand-typed from
    # results/realizability_ciciot2023.json. The file is committed, so generate
    # them: these are the numbers behind the paper's claim that marginal sigma
    # says nothing about joint plausibility, and a transcription slip there would
    # undercut the section that corrects the field's premise.
    RZ = os.path.join(RES, "realizability_ciciot2023.json")
    rz_rows = []
    if os.path.exists(RZ):
        try:
            with open(RZ) as fh:
                rz_rows = json.load(fh)
        except (OSError, ValueError):
            rz_rows = []
    e.section("trigger realizability audit (CICIoT2023)")
    RZ_CELLS = [("sigma", 0.25, "Qtr"), ("sigma", 1.0, "One"),
                ("sigma", 3.0, "Three"), ("donor", None, "Donor")]
    for t in TRIGGERS:
        for mode, scale, tag in RZ_CELLS:
            row = next((r for r in rz_rows
                        if r.get("trigger") == t and r.get("mode") == mode
                        and (scale is None or float(r.get("scale") or 0) == scale)), None)
            e.macro(f"rzSig{w(t)}{tag}", fnum(row and row.get("marginal_abs_sigma_max"), 2))
            dm = row and row.get("joint_mahalanobis")
            # d_M spans 0.5 to 1826; two decimals below 100, none above.
            e.macro(f"rzDM{w(t)}{tag}",
                    fnum(dm, 2 if (dm is None or dm < 100) else 0))
            e.macro(f"rzNN{w(t)}{tag}", fnum(row and row.get("nn_dist_stamped_full"), 2))
        base = next((r for r in rz_rows if r.get("trigger") == t), None)
        e.macro(f"rzPnn{w(t)}", fnum(base and base.get("benign_mahalanobis_p99"), 2),
                "benign 99th-pctile joint Mahalanobis")
    any_row = rz_rows[0] if rz_rows else None
    e.macro("rzUnstamped", fnum(any_row and any_row.get("nn_dist_unstamped_full"), 3),
            "nearest-real-neighbour distance for a real attack flow")
    # The percentile is computed against a 20,000-row benign subsample
    # (realizability.py:39, _MAX_ROWS), so 99.974% means ~5 rows exceeded the
    # trigger. Two decimal places imply a precision that 5 observations do not
    # support (Poisson 95% CI on the count is [1.6, 11.7], i.e. 99.94-99.99%).
    # Emit the coarse percentile the sample can carry, and the raw count, which
    # is both defensible and more vivid than any percentile.
    _rz_ref_rows = 20000
    _pq = next((r.get("joint_mahalanobis_pctile_vs_benign") for r in rz_rows
                if r.get("trigger") == "fixed" and r.get("mode") == "sigma"
                and float(r.get("scale") or 0) == 0.25), None)
    e.macro("rzExceedFixedQtr",
            str(int(round(_rz_ref_rows * (1 - _pq / 100.0)))) if _pq else None,
            "benign rows further from the benign mean than the 0.25x fixed trigger")
    e.macro("rzRefRows", f"{_rz_ref_rows:,}".replace(",", "{,}"),
            "benign reference rows in the audit")
    e.macro("rzPctileFixedQtr",
            fnum(next((r.get("joint_mahalanobis_pctile_vs_benign") for r in rz_rows
                       if r.get("trigger") == "fixed" and r.get("mode") == "sigma"
                       and float(r.get("scale") or 0) == 0.25), None), 2),
            "where the 0.5-sigma fixed trigger sits in benign joint variation")

    # ---- single-seed breadth grid -------------------------------------------
    e.section("breadth grid: mean BSR over the 9 attack cells of each trigger")
    for d in DIRECTION:
        for t in TRIGGERS:
            m, n = smean("BSR", defense=d, attack=True, trigger=t,
                             dataset="ciciot2023", partition="iid",
                             variant="simple", trigger_scale="1.0",
                             trigger_mode="sigma")
            e.macro(f"gridBSR{d}{w(t)}", fnum(m), f"mean of {n} cells")
            e.macro(f"gridN{d}{w(t)}", str(n) if n else None)

    # The prose claims a floor over the whole undefended attack grid ("every one
    # of the N attack cells has BSR >= X"). That was hand-typed and wrong: the
    # weakest cell is 0.8992, just under the 0.90 it claimed. Generate both the
    # count and the actual minimum so the sentence cannot drift again.
    fedavg_attack = [r for r in ss_grid
                     if r.get("defense") == "fedavg"
                     and str(r.get("attack")) == "True"
                     and r.get("dataset") == "ciciot2023"
                     and r.get("partition") == "iid"
                     and r.get("variant") == "simple"
                     and str(r.get("trigger_mode")) == "sigma"
                     and str(r.get("trigger_scale")) in ("1.0", "1")]
    bsrs = []
    for r in fedavg_attack:
        try:
            v = float(r["BSR"])
        except (KeyError, TypeError, ValueError):
            continue
        if v == v:
            bsrs.append(v)
    e.macro("gridAttackCells", str(len(bsrs)) if bsrs else None,
            "undefended attack cells in the breadth grid")
    e.macro("gridMinBSRfedavg", fnum(min(bsrs)) if bsrs else None,
            "weakest undefended cell")

    # ---- malicious-ratio sweep ----------------------------------------------
    e.section("malicious-ratio sweep (fixed trigger, mean over poison rates)")
    for d in DIRECTION:
        for mr in ("0.1", "0.2", "0.3"):
            axis = dict(defense=d, attack=True, trigger="fixed",
                        dataset="ciciot2023", partition="iid",
                        malicious_ratio=mr, variant="simple",
                        trigger_scale="1.0", trigger_mode="sigma")
            m, n = smean("BSR", **axis)
            e.macro(f"ratBSR{d}{w(mr)}", fnum(m, 2), f"mean of {n} poison rates")
            dr, _ = smean("DR", **axis)
            e.macro(f"ratDR{d}{w(mr)}", fnum(dr, 2))
            e.macro(f"ratN{d}{w(mr)}", str(n) if n else None)

    # ---- donor (realizable) triggers ----------------------------------------
    e.section("donor triggers (jointly realizable by construction)")
    for d in ["fedavg", "krum", "flame", "fltrust", "gradcos"]:
        for t in TRIGGERS:
            crit = dict(HEAD)
            crit["trigger_mode"] = "donor"
            r = spick(defense=d, attack=True, trigger=t, **crit)
            e.macro(f"dnBSR{d}{w(t)}", fnum(r and r.get("BSR")))
            e.macro(f"dnDR{d}{w(t)}", fnum(r and r.get("DR"), 2))

    # ---- FLNET2023 -----------------------------------------------------------
    e.section("FLNET2023 (single-seed OAT sweep)")
    for d in DIRECTION:
        clean = spick(defense=d, attack=False, dataset="flnet2023", partition="iid")
        # Near-separable task: three places round every strong defense to 1.000.
        e.macro(f"flCleanCA{d}", fnum(clean and clean.get("CA"), 4))
        e.macro(f"flCleanFone{d}", fnum(clean and clean.get("macro_f1"), 4))
        for t in TRIGGERS:
            r = spick(defense=d, attack=True, trigger=t, dataset="flnet2023",
                     partition="iid", malicious_ratio="0.2", poison_rate="0.1",
                     variant="simple", trigger_scale="1.0", trigger_mode="sigma")
            e.macro(f"flBSR{d}{w(t)}", fnum(r and r.get("BSR")))
            e.macro(f"flDR{d}{w(t)}", fnum(r and r.get("DR"), 2))

    # ---- non-IID -------------------------------------------------------------
    e.section("non-IID (Dirichlet)")
    for d in DIRECTION:
        clean = spick(defense=d, attack=False, dataset="ciciot2023", partition="dirichlet")
        e.macro(f"niCleanCA{d}", fnum(clean and clean.get("CA")))
        e.macro(f"niCleanFone{d}", fnum(clean and clean.get("macro_f1")))
        for t in TRIGGERS:
            r = spick(defense=d, attack=True, trigger=t, dataset="ciciot2023",
                     partition="dirichlet", malicious_ratio="0.2", poison_rate="0.1",
                     variant="simple", trigger_scale="1.0", trigger_mode="sigma")
            e.macro(f"niBSR{d}{w(t)}", fnum(r and r.get("BSR")))
            e.macro(f"niCA{d}{w(t)}", fnum(r and r.get("CA")))
            e.macro(f"niDR{d}{w(t)}", fnum(r and r.get("DR"), 2))

    # ---- provenance counts ---------------------------------------------------
    e.section("cell counts (provenance)")
    grid_rows = ss_grid
    e.macro("numCellsSingle", str(len(grid_rows)) if grid_rows else None,
            "single-seed cells in summary.csv")
    e.macro("numCellsMulti", str(len(ms)) if ms else None, "grouped cells in summary_multiseed.csv")
    nseeds = {int(s) for r in ms for s in str(r.get("seeds", "")).split(";") if s.isdigit()}
    e.macro("numSeeds", str(len(nseeds)) if nseeds else None)

    with open(OUT, "w") as f:
        f.write("\n".join(e.lines) + "\n")

    total = len(e.defined)
    done = total - len(e.pending)
    print(f"wrote {os.path.relpath(OUT, ROOT)}  ({done}/{total} macros resolved, "
          f"{len(e.pending)} still \\PENDING)")
    if e.pending:
        by_family = defaultdict(int)
        for name in e.pending:
            for fam in ("ms", "ad", "ev", "res", "mg", "grid", "rat", "dn", "fl", "ni", "num"):
                if name.startswith(fam):
                    by_family[fam] += 1
                    break
        print("  pending by family: " +
              ", ".join(f"{k}={v}" for k, v in sorted(by_family.items())))
    # The submission criterion is that no [PENDING RUN] marker reaches the page,
    # which is about the macros main.tex actually quotes -- not about every macro
    # the generator can emit. The generator deliberately emits more than the paper
    # uses (a full grid per family), so failing on all of them would demand
    # experiments whose numbers appear nowhere in the manuscript. --strict
    # therefore gates on the referenced subset, and reports the rest for
    # information.
    referenced = set()
    try:
        tex = open(os.path.join(ROOT, "paper", "main.tex"), encoding="utf-8").read()
        body = tex[tex.index(r"\begin{document}"):]
        body = re.sub(r"(?m)^\s*%.*$", "", body)
        referenced = {m for m in re.findall(r"\\([A-Za-z]+)", body)} & set(e.defined)
    except (OSError, ValueError):
        pass
    blocking = sorted(set(e.pending) & referenced) if referenced else sorted(e.pending)
    if referenced:
        print(f"  referenced by main.tex: {len(referenced)} macros, "
              f"{len(blocking)} of them unresolved")
    if args.strict and blocking:
        print(f"\nSTRICT: {len(blocking)} macro(s) quoted by main.tex are unresolved "
              f"— not submittable.", file=sys.stderr)
        for name in blocking:
            print(f"    \\{name}", file=sys.stderr)
        return 1
    if args.strict:
        print("\nSTRICT: every macro the manuscript quotes is resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
