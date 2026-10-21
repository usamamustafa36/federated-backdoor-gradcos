#!/usr/bin/env python3
"""Macros for the generality probe (ResNet-20 / CIFAR-10, iteration 19).

Reads results/generality_cifar/*.json (experiments/generality/cifar_resnet20.py)
and writes paper/numbers_generality.tex (\\gc... macros; generated, DO NOT EDIT).
A quantity whose runs are not on disk yet is \\PENDING.

Decision-level counterfactual (FedAvg trajectory; every rule scored on the same
client updates, once on the full state_dict and once on parameters() only):
  counter / buffer share of each client's squared update norm, the server root
  update's counter share q0, how often Krum's pick and Multi-Krum's kept set
  differ, mean pairwise cosine, FLTrust trust cosines, attackers kept / trusted.
Closed loop (exploratory, n = seeds): final test accuracy of FLTrust and
Multi-Krum driven by the full vs the trainable vector, Dirichlet partition.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "generality_cifar")
OUT = os.path.join(ROOT, "paper", "numbers_generality.tex")
PART = {"dirichlet": "Dir", "iid": "Iid"}


def load():
    runs = {}
    for p in sorted(glob.glob(os.path.join(RES, "*.json"))):
        if os.path.getsize(p) == 0:
            continue
        d = json.load(open(p))
        if "setting" not in d:              # summary.json
            continue
        s = d["setting"]
        runs[(s["agg"], s["partition"], s["seed"])] = d
    # Interim: an unfinished FedAvg run contributes its completed rounds to the
    # decision-level statistics (each round is a complete observation); closed-loop
    # accuracies are read only from finished runs.
    for p in sorted(glob.glob(os.path.join(RES, "_ckpt", "fedavg_*.pt"))):
        tag = os.path.basename(p)[:-3]
        _, part, seed = tag.split("_")
        key = ("fedavg", part, int(seed[1:]))
        if key in runs:
            continue
        import torch
        ck = torch.load(p, weights_only=False, map_location="cpu")
        runs[key] = {"setting": {"agg": "fedavg", "partition": part, "seed": key[2],
                                 "n_mal": 2, "interim": True}, "log": ck["log"]}
    return runs


def main():
    runs = load()
    mac = {}
    P = r"\PENDING{}"

    def pct(x):
        return f"{100 * x:.1f}"

    # Model and federation constants come from the experiment module itself.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cr20", os.path.join(ROOT, "experiments", "generality", "cifar_resnet20.py"))
    cr = importlib.util.module_from_spec(spec); spec.loader.exec_module(cr)
    m = cr.ResNet20(); sd = m.state_dict()
    pn = {n for n, _ in m.named_parameters()}
    mac["gcNTrain"] = f"{sum(sd[k].numel() for k in sd if k in pn):,}".replace(",", "{,}")
    mac["gcNBuf"] = f"{sum(sd[k].numel() for k in sd if k not in pn):,}".replace(",", "{,}")
    mac["gcNBN"] = str(sum(k.endswith("num_batches_tracked") for k in sd))
    mac["gcRoot"] = str(cr.ROOT); mac["gcClients"] = str(cr.N_CLIENTS)
    mac["gcMal"] = str(cr.N_MAL); mac["gcBS"] = str(cr.BS)
    fin = [d for d in runs.values() if not d["setting"].get("interim")]
    mac["gcRounds"] = str(fin[0]["setting"]["rounds"]) if fin else "20"  # launcher value
    mac["gcRows"] = f"{cr.N_TRAIN:,}".replace(",", "{,}")

    summary = {}
    for part, tag in PART.items():
        rs = [d for (a, p, _), d in runs.items() if a == "fedavg" and p == part]
        mac[f"gcSeeds{tag}"] = str(len(rs)) if rs else P
        if not rs:
            for k in ("CntShare", "BufShare", "QZero", "KrumDiff", "MkDiff", "MkAtkFull",
                      "MkAtkTr", "PairFull", "PairTr", "TrustFull", "TrustTr",
                      "AtkWFull", "AtkWTr", "AtkZeroFull", "AtkZeroTr", "HonZeroFull", "HonZeroTr", "BMin", "BMax",
                      "RoundsTot", "RoundsDone", "AccFedavg", "Finished", "KrumDiffNc", "MkDiffNc",
                      "MkDiffStats", "TrustNc"):
                mac[f"gc{k}{tag}"] = P
            continue
        cnt, buf, q0, kd, md, maf, mat = [], [], [], [], [], [], []
        kdc, mdc, mns, tn, hzf, hzt = [], [], [], [], [], []
        pf, pt, tf, tt, awf, awt, azf, azt, bs = [], [], [], [], [], [], [], [], []
        accs = []
        for d in rs:
            nmal = d["setting"]["n_mal"]
            mal = set(range(nmal))
            for r in d["log"]:
                cnt += r["counter_share"]; buf += r["buffer_share"]; q0.append(r["q0"])
                bs += r["batches"]
                F, T = r["dec"]["full"], r["dec"]["trainable"]
                N = r["dec"]["nocount"]
                kdc.append(F["krum_pick"] != N["krum_pick"])
                mdc.append(set(F["mkrum_keep"]) != set(N["mkrum_keep"]))
                mns.append(set(N["mkrum_keep"]) != set(T["mkrum_keep"]))
                kd.append(F["krum_pick"] != T["krum_pick"])
                md.append(set(F["mkrum_keep"]) != set(T["mkrum_keep"]))
                maf.append(len(mal & set(F["mkrum_keep"])))
                mat.append(len(mal & set(T["mkrum_keep"])))
                pf.append(F["mean_pair_cos"]); pt.append(T["mean_pair_cos"])
                hon = [i for i in range(len(F["fltrust_cos"])) if i not in mal]
                tf += [F["fltrust_cos"][i] for i in hon]
                tt += [T["fltrust_cos"][i] for i in hon]
                tn += [N["fltrust_cos"][i] for i in hon]
                awf.append(sum(F["fltrust_w"][i] for i in mal))
                awt.append(sum(T["fltrust_w"][i] for i in mal))
                azf += [F["fltrust_cos"][i] <= 0 for i in mal]
                azt += [T["fltrust_cos"][i] <= 0 for i in mal]
                hzf += [F["fltrust_cos"][i] <= 0 for i in hon]
                hzt += [T["fltrust_cos"][i] <= 0 for i in hon]
            if not d["setting"].get("interim"):
                accs.append(d["log"][-1].get("test_acc", float("nan")))
        mac[f"gcCntShare{tag}"] = pct(np.median(cnt))
        mac[f"gcBufShare{tag}"] = pct(np.median(buf))
        mac[f"gcQZero{tag}"] = pct(np.median(q0))
        mac[f"gcKrumDiff{tag}"] = pct(np.mean(kd))
        mac[f"gcMkDiff{tag}"] = pct(np.mean(md))
        mac[f"gcMkAtkFull{tag}"] = f"{np.mean(maf):.2f}"
        mac[f"gcMkAtkTr{tag}"] = f"{np.mean(mat):.2f}"
        mac[f"gcPairFull{tag}"] = f"{np.mean(pf):.3f}"
        mac[f"gcPairTr{tag}"] = f"{np.mean(pt):.3f}"
        mac[f"gcTrustFull{tag}"] = f"{np.median(tf):.3f}"
        mac[f"gcTrustTr{tag}"] = f"{np.median(tt):.3f}"
        mac[f"gcAtkWFull{tag}"] = pct(np.mean(awf))
        mac[f"gcAtkWTr{tag}"] = pct(np.mean(awt))
        mac[f"gcAtkZeroFull{tag}"] = pct(np.mean(azf))
        mac[f"gcAtkZeroTr{tag}"] = pct(np.mean(azt))
        mac[f"gcHonZeroFull{tag}"] = pct(np.mean(hzf))
        mac[f"gcHonZeroTr{tag}"] = pct(np.mean(hzt))
        mac[f"gcBMin{tag}"] = str(int(min(bs)))
        mac[f"gcBMax{tag}"] = str(int(max(bs)))
        mac[f"gcRoundsTot{tag}"] = str(len(kd))
        mac[f"gcRoundsDone{tag}"] = str(min(len(d["log"]) for d in rs))
        mac[f"gcAccFedavg{tag}"] = f"{np.nanmean(accs):.3f}" if accs else P
        mac[f"gcFinished{tag}"] = str(len(accs))
        mac[f"gcKrumDiffNc{tag}"] = pct(np.mean(kdc))
        mac[f"gcMkDiffNc{tag}"] = pct(np.mean(mdc))
        mac[f"gcMkDiffStats{tag}"] = pct(np.mean(mns))
        mac[f"gcTrustNc{tag}"] = f"{np.median(tn):.3f}"
        summary[part] = {"n_runs": len(rs), "round_records": len(kd),
                         "counter_share_median": float(np.median(cnt)),
                         "krum_pick_differs": float(np.mean(kd)),
                         "mkrum_set_differs": float(np.mean(md))}

    # closed loop, Dirichlet
    for rule, tag in (("fltrust", "Ft"), ("mkrum", "Mk")):
        seeds = sorted({s for (a, p, s) in runs if a == f"{rule}_full" and p == "dirichlet"}
                       & {s for (a, p, s) in runs if a == f"{rule}_trainable" and p == "dirichlet"})
        if not seeds:
            for k in ("AccFull", "AccTr", "AccDiff", "N", "Wins"):
                mac[f"gc{tag}{k}"] = P
            continue
        af = np.array([runs[(f"{rule}_full", "dirichlet", s)]["log"][-1]["test_acc"] for s in seeds])
        at = np.array([runs[(f"{rule}_trainable", "dirichlet", s)]["log"][-1]["test_acc"] for s in seeds])
        mac[f"gc{tag}AccFull"] = f"{af.mean():.3f}"
        mac[f"gc{tag}AccTr"] = f"{at.mean():.3f}"
        mac[f"gc{tag}AccDiff"] = f"{(at - af).mean():+.3f}"
        mac[f"gc{tag}N"] = str(len(seeds))
        mac[f"gc{tag}Wins"] = str(int((at > af).sum()))
        summary[f"{rule}_closed_loop"] = {"seeds": seeds, "acc_full": af.tolist(),
                                          "acc_trainable": at.tolist()}

    lines = ["% Generated by paper/make_numbers_generality.py from results/generality_cifar/. DO NOT EDIT."]
    lines += [f"\\providecommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(RES, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    npend = sum(v == P for v in mac.values())
    print(f"wrote paper/numbers_generality.tex ({len(mac)} macros, {npend} PENDING; "
          f"{len(runs)} runs)")


if __name__ == "__main__":
    main()
