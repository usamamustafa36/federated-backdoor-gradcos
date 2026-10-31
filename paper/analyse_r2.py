"""R2 analysis (iterations/PREREG_R2.md): byzantineFL with and without the counter mask.

Applies the registered tests mechanically:
  Y = minimum test error rate over rounds = 1 - max_t acc_t / 100 (the paper's Fig. 3).
  H1: Krum, each (c_frac, p): Y_full - Y_nonbt != 0, exact two-sided paired sign-flip,
      Holm across the 6.  H2: trimmed_mean and fang, Holm across the 12.
  M1: per-seed median counter share of pairwise squared distances (full arm) > 0.5.
  M2: fraction of rounds in which Krum's / trimmed mean's choice on the same received
      models differs between full and nonbt (counterfactual, logged by the harness).
Only runs with "complete": true and no "error" enter; plumbing runs (plumb_*, smoke_*)
never do. Writes results/r2_exposed/summary.json and paper/numbers_r2.tex (\\rTwo...).
"""
from __future__ import annotations

import glob, itertools, json, os, re, sys
from math import comb
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(ROOT, "results", "r2_exposed")
OUT_TEX = os.path.join(ROOT, "paper", "numbers_r2.tex")
PAT = re.compile(r"byzfl_(krum|trimmed_mean|fang|fedavg)_(target|untarget)_c([0-9.]+)_(full|nonbt|trainable)_s(\d+)\.json$")


def signflip_p(d):
    d = np.asarray([x for x in d if x != 0.0], float)
    n = len(d)
    if n == 0:
        return 1.0
    obs = abs(d.sum())
    cnt = 0
    for signs in itertools.product((1, -1), repeat=n):
        if abs((d * signs).sum()) >= obs - 1e-15:
            cnt += 1
    return cnt / 2 ** n


def holm(ps):
    order = np.argsort(ps); m = len(ps); out = [1.0] * m; run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (m - k) * ps[i])); out[i] = run
    return out


def load():
    runs = {}
    for f in glob.glob(os.path.join(RES, "byzfl_*.json")):
        m = PAT.search(os.path.basename(f))
        if not m:
            continue
        try:
            j = json.load(open(f))
        except Exception:
            continue
        if not j.get("complete") or j.get("error") or not j.get("rounds"):
            continue
        meth, p, c, arm, s = m.groups()
        runs[(meth, p, c, arm, int(s))] = j
    return runs


def Y(j):
    return 1.0 - max(r["test_acc"] for r in j["rounds"]) / 100.0


FAMILY_RUNS = {"H1": 120, "H2": 240}   # full + nonbt runs per family (10 seeds x 6 cells x 2 arms)


def main():
    runs = load()
    # Blinding guard (PREREG_R2 Amendment 3): a family's cells are scored, written and printed only
    # when all of its runs are complete; until then only the run counts are reported.
    have = {"H1": sum(1 for k in runs if k[0] == "krum" and k[3] in ("full", "nonbt")),
            "H2": sum(1 for k in runs if k[0] != "krum" and k[0] != "fedavg" and k[3] in ("full", "nonbt"))}
    open_fam = {f for f, n in FAMILY_RUNS.items() if have[f] >= n or "--final" in sys.argv}
    print(f"R2: complete runs H1 {have['H1']}/120, H2 {have['H2']}/240; scored: {sorted(open_fam) or 'none (blinded)'}")
    runs = {k: v for k, v in runs.items()
            if k[0] == "fedavg" or ("H1" if k[0] == "krum" else "H2") in open_fam}
    cells, fam = [], {"H1": [], "H2": []}
    for meth in ("krum", "trimmed_mean", "fang"):
        for c in ("0.1", "0.2", "0.3"):
            for p in ("target", "untarget"):
                seeds = sorted(s for (m_, p_, c_, a, s) in runs
                               if (m_, p_, c_, a) == (meth, p, c, "full")
                               and (meth, p, c, "nonbt", s) in runs)
                yf = [Y(runs[(meth, p, c, "full", s)]) for s in seeds]
                yn = [Y(runs[(meth, p, c, "nonbt", s)]) for s in seeds]
                d = [a - b for a, b in zip(yf, yn)]
                share = [np.median([r["counter_share_dist"] for r in runs[(meth, p, c, "full", s)]["rounds"]
                                    if r.get("counter_share_dist") is not None] or [np.nan]) for s in seeds]
                key = "krum" if meth == "krum" else "tm"
                chg = []
                for s in seeds:
                    rr = runs[(meth, p, c, "full", s)]["rounds"]
                    ok = [r for r in rr if f"{key}_full" in r and f"{key}_nonbt" in r]
                    if ok:
                        chg.append(np.mean([r[f"{key}_full"] != r[f"{key}_nonbt"] for r in ok]))
                cell = dict(method=meth, p=p, c=c, n=len(seeds), seeds=seeds,
                            Y_full=float(np.mean(yf)) if yf else None,
                            Y_nonbt=float(np.mean(yn)) if yn else None,
                            diff=float(np.mean(d)) if d else None,
                            pos=int(sum(x > 0 for x in d)), neg=int(sum(x < 0 for x in d)),
                            p_value=signflip_p(d) if d else None,
                            counter_share_median=float(np.nanmedian(share)) if share else None,
                            decision_change_rate=float(np.mean(chg)) if chg else None)
                cells.append(cell)
                fam["H1" if meth == "krum" else "H2"].append(cell)
    for name, cs in fam.items():
        ps = [c["p_value"] if c["p_value"] is not None else 1.0 for c in cs]
        for c, ph in zip(cs, holm(ps)):
            c["p_holm"] = ph; c["family"] = name
    json.dump({"cells": cells, "n_runs": len(runs)}, open(os.path.join(RES, "summary.json"), "w"), indent=1)

    def mac(name, val, fmt="{:.3f}"):
        v = r"\PENDING" if val is None or (isinstance(val, float) and np.isnan(val)) else (
            fmt.format(val) if isinstance(val, float) else str(val))
        return "\\providecommand{\\rTwo%s}{%s}\n" % (name, v)

    tex = ["% generated by paper/analyse_r2.py -- do not edit\n", mac("Runs", len(runs), "{}")]
    tag = {"krum": "Krum", "trimmed_mean": "Tm", "fang": "Fang"}
    word = {"0.1": "One", "0.2": "Two", "0.3": "Three"}
    for c in cells:
        b = f"{tag[c['method']]}{'Tgt' if c['p'] == 'target' else 'Utg'}{word[c['c']]}"
        has = c["n"] > 0
        tex += [mac(b + "N", c["n"], "{}"),
                mac(b + "Yfull", c["Y_full"] if has else None),
                mac(b + "Ynonbt", c["Y_nonbt"] if has else None),
                mac(b + "Diff", c["diff"] if has else None, "{:+.3f}"),
                mac(b + "P", c["p_value"] if has else None, "{:.3g}"),
                mac(b + "Ph", c["p_holm"] if has else None, "{:.3g}"),
                mac(b + "Share", c["counter_share_median"] if has else None),
                mac(b + "Chg", c["decision_change_rate"] if has else None, "{:.2f}")]
    sup = sum(1 for c in fam["H1"] if c["n"] > 0 and c["p_holm"] <= 0.05)
    tex.append(mac("HOneSupported", sup if any(c["n"] for c in fam["H1"]) else None, "{}"))
    h1 = [c for c in fam["H1"] if c["n"]]
    for p, b in (("target", "Tgt"), ("untarget", "Utg")):
        cs = [c for c in h1 if c["p"] == p]
        tex += [mac(f"Krum{b}ShareMin", min(c["counter_share_median"] for c in cs) if cs else None, "{:.2f}"),
                mac(f"Krum{b}ShareMax", max(c["counter_share_median"] for c in cs) if cs else None, "{:.2f}"),
                mac(f"Krum{b}ChgMin", min(c["decision_change_rate"] for c in cs) if cs else None, "{:.2f}"),
                mac(f"Krum{b}ChgMax", max(c["decision_change_rate"] for c in cs) if cs else None, "{:.2f}")]
    # Exploratory (not registered; iteration 35): whom Krum picks, read through the counter each
    # received model reports (nbt_first_layer). Closed loop: each arm's own choice in its own runs.
    ex = {}
    for (m_, p, c, a, s), j in runs.items():
        if m_ != "krum" or a not in ("full", "nonbt"):
            continue
        for r in j["rounds"]:
            mo, nb, k = r.get("mal_order"), r.get("nbt_first_layer"), r.get(f"krum_{a}")
            if not mo or not nb or k is None:
                continue
            hon = [x for x, mal in zip(nb, mo) if not mal]
            d = ex.setdefault((p, a), {"mal": [], "top": [], "ratio": []})
            d["mal"].append(mo[k])
            d["top"].append(float(not mo[k] and nb[k] == max(hon)))
            if any(mo):
                d["ratio"].append(np.median([x for x, mal in zip(nb, mo) if mal]) / np.median(hon))
    for p, b in (("target", "Tgt"), ("untarget", "Utg")):
        for a, A in (("full", "Full"), ("nonbt", "Nonbt")):
            d = ex.get((p, a))
            tex += [mac(f"Krum{b}PickMal{A}", 100 * float(np.mean(d["mal"])) if d else None, "{:.0f}"),
                    mac(f"Krum{b}TopB{A}", 100 * float(np.mean(d["top"])) if d else None, "{:.0f}")]
        d = ex.get((p, "full"))
        tex.append(mac(f"Krum{b}CtrRatio", float(np.median(d["ratio"])) if d and d["ratio"] else None, "{:.1f}"))
    fam2 = [c for c in fam["H2"] if c["n"]]
    tex.append(mac("HTwoSupported", sum(1 for c in fam2 if c["p_holm"] <= 0.05) if fam2 else None, "{}"))
    # M1 (registered): one-sided sign test over seeds of the per-seed median share against 0.5.
    for m_, b in (("krum", "Krum"), ("trimmed_mean", "Tm")):
        pm = []
        for c in fam[("H1" if m_ == "krum" else "H2")]:
            if c["method"] != m_ or c["p"] != "target" or not c["n"]:
                continue
            v = [np.median([r["counter_share_dist"] for r in runs[(m_, "target", c["c"], "full", s)]["rounds"]
                            if r.get("counter_share_dist") is not None]) for s in c["seeds"]]
            k = sum(x > 0.5 for x in v)
            pm.append(sum(comb(len(v), i) for i in range(k, len(v) + 1)) / 2 ** len(v))
        tex.append(mac(f"MOne{b}P", max(pm) if pm else None, "{:.3g}"))
    # Exploratory (not registered; iteration 36): trimmed mean's kept set, each arm's own choice in
    # its own runs, and how often the full arm's set is the one the counters alone would give.
    # Fang's final set is not logged (its tm_* fields are the inner rule), so Fang is not read here.
    kept, same = {}, []
    for (m_, p, c, a, s), j in runs.items():
        if m_ != "trimmed_mean" or a not in ("full", "nonbt"):
            continue
        for r in j["rounds"]:
            mo, k = r.get("mal_order"), r.get(f"tm_{a}")
            if not mo or not k or not any(mo):
                continue
            kept.setdefault((p, a), []).append(sum(mo[i] for i in k) / sum(mo))
            if a == "full" and p == "target":
                nb = np.asarray(r["nbt_first_layer"], float)
                d = ((nb[:, None] - nb[None, :]) ** 2).sum(axis=1)
                order = np.argsort(np.abs(d - np.sort(d)[(len(d) - 1) // 2]), kind="stable")
                same.append(set(int(i) for i in order[:len(k)]) == set(k))
    for p, b in (("target", "Tgt"), ("untarget", "Utg")):
        for a, A in (("full", "Full"), ("nonbt", "Nonbt")):
            d = kept.get((p, a))
            tex.append(mac(f"Tm{b}Kept{A}", 100 * float(np.mean(d)) if d else None, "{:.0f}"))
    tex.append(mac("TmTgtSameCtr", 100 * float(np.mean(same)) if same else None, "{:.0f}"))
    fu = [(a, s, j) for (m_, p, c, a, s), j in runs.items() if m_ == "fang" and p == "untarget" and a in ("full", "nonbt")]
    tex.append(mac("FangUtgNanRuns", sum(1 for _, _, j in fu if any(
        r.get("counter_share_dist") is None or r["counter_share_dist"] != r["counter_share_dist"] for r in j["rounds"])) if fu else None, "{}"))
    tex.append(mac("FangUtgRuns", len(fu) if fu else None, "{}"))
    open(OUT_TEX, "w").write("".join(tex))
    print(f"R2: {len(runs)} runs; H1 supported {sup}/6 -> {OUT_TEX}")
    for c in cells:
        if c["n"]:
            print(f"  {c['method']:12s} {c['p']:8s} c={c['c']} n={c['n']} dY={c['diff']:+.3f} "
                  f"p={c['p_value']:.3g} pH={c['p_holm']:.3g} share={c['counter_share_median']:.3f} "
                  f"chg={c['decision_change_rate']}")


if __name__ == "__main__":
    main()
