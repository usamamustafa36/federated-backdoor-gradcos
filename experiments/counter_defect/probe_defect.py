#!/usr/bin/env python3
"""Deterministic CPU probe of the num_batches_tracked defect (iteration 2).

Measures, on the paper's own CNN+LSTM (39 features, 8 classes), the facts the
manuscript's "The defect" section states, and writes them to
    results/defect_probe.json      raw measurements
    paper/numbers_defect.tex       \\df... macros (generated; DO NOT EDIT)

1. Coordinate census: trainable coordinates, buffer coordinates, BatchNorm layers.
2. Inertness: two copies of a trained-for-a-few-steps model that differ only by
   +100000 on num_batches_tracked are run through identical train-mode batches;
   we report the max abs difference of running_mean / running_var and of the
   eval-mode logits. Under momentum=0.1 (default) it must be exactly 0; under
   momentum=None (cumulative average) it is not -- the one case where PyTorch reads it.
3. Proposition 1 check on real local updates: two clients run B_i != B_j local
   batches from the same global model; we verify
       cos(d_i,d_j) = sqrt((1-s_i)(1-s_j)) cos(u_i,u_j) + sqrt(s_i s_j) cos(b_i,b_j)
       ||d_i-d_j||^2 = ||u_i-u_j||^2 + ||b_i-b_j||^2,  counter part = L (B_i-B_j)^2
   to floating-point precision, and report the counter share of ||d_i||^2.
Synthetic inputs (Gaussian features, random labels) are used deliberately: every
quantity here is a property of the transmission format and of PyTorch's BatchNorm,
not of the data. The share of the norm on real data is measured in the P1 runs.
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys

import numpy as np
import torch
import torch.nn as nn

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from src.models.cnn_lstm import CNNLSTM  # noqa: E402

torch.set_num_threads(1)
F, C, BS = 39, 8, 256


def flat(sd, keys):
    return np.concatenate([sd[k].detach().cpu().numpy().astype(np.float64).ravel() for k in keys])


def local_train(model, nbatches, seed):
    g = torch.Generator().manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    model.train()
    for _ in range(nbatches):
        x = torch.randn(BS, F, generator=g)
        y = torch.randint(0, C, (BS,), generator=g)
        opt.zero_grad()
        nn.functional.cross_entropy(model(x), y).backward()
        opt.step()
    return model


def inertness(momentum):
    torch.manual_seed(0)
    m = CNNLSTM(F, C)
    for mod in m.modules():
        if isinstance(mod, nn.modules.batchnorm._BatchNorm):
            mod.momentum = momentum
    local_train(m, 3, seed=1)
    a, b = copy.deepcopy(m), copy.deepcopy(m)
    for mod in b.modules():
        if isinstance(mod, nn.modules.batchnorm._BatchNorm):
            mod.num_batches_tracked += 100000
    g = torch.Generator().manual_seed(2)
    xs = [torch.randn(BS, F, generator=g) for _ in range(5)]
    a.train(); b.train()
    with torch.no_grad():
        for x in xs:
            a(x); b(x)
    sa, sb = a.state_dict(), b.state_dict()
    rm = max(float((sa[k] - sb[k]).abs().max()) for k in sa if k.endswith("running_mean"))
    rv = max(float((sa[k] - sb[k]).abs().max()) for k in sa if k.endswith("running_var"))
    a.eval(); b.eval()
    with torch.no_grad():
        xt = torch.randn(1024, F, generator=g)
        lo = float((a(xt) - b(xt)).abs().max())
    return {"max_abs_running_mean": rm, "max_abs_running_var": rv, "max_abs_eval_logit": lo}


def main():
    torch.manual_seed(0)
    model = CNNLSTM(F, C)
    sd = model.state_dict()
    pnames = {n for n, _ in model.named_parameters()}
    keys = list(sd.keys())
    tkeys = [k for k in keys if k in pnames]
    bkeys = [k for k in keys if k not in pnames]
    ckeys = [k for k in keys if k.endswith("num_batches_tracked")]
    n_train = sum(sd[k].numel() for k in tkeys)
    n_buf = sum(sd[k].numel() for k in bkeys)
    L = len(ckeys)

    inert_default = inertness(0.1)
    inert_cma = inertness(None)

    # Proposition 1 on two real local updates with unequal batch counts.
    Bi, Bj = 16, 11
    g0 = copy.deepcopy(model.state_dict())
    ci = local_train(copy.deepcopy(model), Bi, seed=10).state_dict()
    cj = local_train(copy.deepcopy(model), Bj, seed=11).state_dict()
    di = flat(ci, keys) - flat(g0, keys)
    dj = flat(cj, keys) - flat(g0, keys)
    ui, uj = flat(ci, tkeys) - flat(g0, tkeys), flat(cj, tkeys) - flat(g0, tkeys)
    bi, bj = flat(ci, bkeys) - flat(g0, bkeys), flat(cj, bkeys) - flat(g0, bkeys)
    cnt_i = flat(ci, ckeys) - flat(g0, ckeys)
    cnt_j = flat(cj, ckeys) - flat(g0, ckeys)

    def cos(x, y):
        return float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))

    si = float(bi @ bi / (di @ di))
    sj = float(bj @ bj / (dj @ dj))
    cos_full = cos(di, dj)
    cos_pred = math.sqrt((1 - si) * (1 - sj)) * cos(ui, uj) + math.sqrt(si * sj) * cos(bi, bj)
    dist_full = float(((di - dj) ** 2).sum())
    dist_pred = float(((ui - uj) ** 2).sum() + ((bi - bj) ** 2).sum())
    cnt_dist = float(((cnt_i - cnt_j) ** 2).sum())

    # Corollary 3 (FLTrust): the server's root update runs B_0 = 2 batches (300 rows,
    # batch 256). Its counter share q_0 and the client's q_i give the lower bound
    # cos(d_i, g_0) >= sqrt(q_i q_0) - sqrt((1-q_i)(1-q_0)), positive iff q_i + q_0 > 1.
    # Added in iteration 8; computed after the clients so earlier numbers are unchanged.
    B0 = 2
    c0 = local_train(copy.deepcopy(model), B0, seed=12).state_dict()
    d0 = flat(c0, keys) - flat(g0, keys)
    u0 = flat(c0, tkeys) - flat(g0, tkeys)
    cnt_0 = flat(c0, ckeys) - flat(g0, ckeys)
    q0 = float(cnt_0 @ cnt_0 / (d0 @ d0))
    qi = float(cnt_i @ cnt_i / (di @ di))
    flt_bound = math.sqrt(qi * q0) - math.sqrt((1 - qi) * (1 - q0))
    out = {
        "model": "CNN+LSTM (paper), 39 features, 8 classes",
        "n_trainable": n_train, "n_buffer": n_buf, "n_bn_layers": L,
        "inert_momentum_default": inert_default, "inert_momentum_none": inert_cma,
        "prop1": {
            "B_i": Bi, "B_j": Bj, "s_i": si, "s_j": sj,
            "counter_share_norm_i": float(cnt_i @ cnt_i / (di @ di)),
            "cos_full": cos_full, "cos_trainable": cos(ui, uj), "cos_pred": cos_pred,
            "cos_abs_err": abs(cos_full - cos_pred),
            "dist_full": dist_full, "dist_pred": dist_pred,
            "dist_rel_err": abs(dist_full - dist_pred) / dist_full,
            "counter_dist": cnt_dist, "counter_dist_pred": L * (Bi - Bj) ** 2,
            "counter_share_dist": cnt_dist / dist_full,
        },
        "fltrust": {
            "B_0": B0, "q_0": q0, "q_i": qi,
            "cos_full_i0": cos(di, d0), "cos_trainable_i0": cos(ui, u0),
            "lower_bound": flt_bound,
        },
    }
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "defect_probe.json"), "w") as f:
        json.dump(out, f, indent=2)

    p = out["prop1"]

    def sci(x):
        if x == 0:
            return "0"
        e = int(math.floor(math.log10(abs(x))))
        return f"{x / 10 ** e:.1f}\\times10^{{{e}}}"

    mac = {
        "dfNTrain": f"{n_train:,}".replace(",", "{,}"),
        "dfNBuf": str(n_buf), "dfNBN": str(L),
        "dfInertMean": sci(inert_default["max_abs_running_mean"]),
        "dfInertVar": sci(inert_default["max_abs_running_var"]),
        "dfInertLogit": sci(inert_default["max_abs_eval_logit"]),
        "dfCmaMean": sci(inert_cma["max_abs_running_mean"]),
        "dfCmaLogit": sci(inert_cma["max_abs_eval_logit"]),
        "dfPropBi": str(Bi), "dfPropBj": str(Bj),
        "dfPropShareI": f"{100 * p['counter_share_norm_i']:.1f}",
        "dfPropCosFull": f"{p['cos_full']:.3f}", "dfPropCosSig": f"{p['cos_trainable']:.3f}",
        "dfPropCosErr": sci(p["cos_abs_err"]), "dfPropDistErr": sci(p["dist_rel_err"]),
        "dfPropDistShare": f"{100 * p['counter_share_dist']:.1f}",
        "dfFltBzero": str(out["fltrust"]["B_0"]),
        "dfFltQzero": f"{100 * out['fltrust']['q_0']:.1f}",
        "dfFltCosFull": f"{out['fltrust']['cos_full_i0']:.3f}",
        "dfFltCosSig": f"{out['fltrust']['cos_trainable_i0']:.3f}",
        "dfFltBound": f"{out['fltrust']['lower_bound']:.3f}",
    }
    lines = ["% Generated by experiments/counter_defect/probe_defect.py "
             "-> results/defect_probe.json. DO NOT EDIT."]
    lines += [f"\\providecommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    with open(os.path.join(ROOT, "paper", "numbers_defect.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
