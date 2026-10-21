#!/usr/bin/env python3
"""Second-architecture probe of the num_batches_tracked defect (iteration 3, CPU).

Repeats the geometric part of probe_defect.py on a CIFAR-style ResNet-18
(3x3 stem, four stages of two BasicBlocks, 64-512 channels, 20 BatchNorm layers),
written out by hand because torchvision is broken on this machine
(`operator torchvision::nms does not exist`). It measures, for two clients that
start from one initialisation and run B_i != B_j local SGD steps:
  * the coordinate census (trainable / buffer / BatchNorm layers L),
  * inertness of +1e5 on every counter under momentum=0.1,
  * Proposition 1 on the two real local updates (cos and squared distance), and
  * the buffer and counter shares of ||d_i||^2 and of ||d_i - d_j||^2,
    with the full-vector and trainable-only cosines.
Inputs are synthetic (Gaussian images, random labels), as in probe_defect.py:
the quantities are properties of the transmission format and of BatchNorm. The
trainable update's norm, and hence the share, does depend on optimiser, learning
rate and data; the setting used (SGD, lr 0.01, momentum 0.9, batch 32) is stated
in the output and in the paper. This is a geometry probe, not a federated run.

Writes results/defect_probe_resnet.json and paper/numbers_defect_resnet.tex
(\\dr... macros; generated, DO NOT EDIT).
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
import torch.nn.functional as Fn

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
torch.set_num_threads(2)
BS, C, HW = 32, 10, 32
LR, MOM = 0.01, 0.9


class BasicBlock(nn.Module):
    def __init__(self, cin, cout, stride):
        super().__init__()
        self.c1 = nn.Conv2d(cin, cout, 3, stride, 1, bias=False)
        self.b1 = nn.BatchNorm2d(cout)
        self.c2 = nn.Conv2d(cout, cout, 3, 1, 1, bias=False)
        self.b2 = nn.BatchNorm2d(cout)
        self.short = nn.Sequential()
        if stride != 1 or cin != cout:
            self.short = nn.Sequential(nn.Conv2d(cin, cout, 1, stride, bias=False),
                                       nn.BatchNorm2d(cout))

    def forward(self, x):
        y = Fn.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return Fn.relu(y + self.short(x))


class ResNet18(nn.Module):
    def __init__(self, num_classes=C):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv2d(3, 64, 3, 1, 1, bias=False), nn.BatchNorm2d(64),
                                  nn.ReLU())
        layers, cin = [], 64
        for cout, stride in ((64, 1), (128, 2), (256, 2), (512, 2)):
            layers += [BasicBlock(cin, cout, stride), BasicBlock(cout, cout, 1)]
            cin = cout
        self.layers = nn.Sequential(*layers)
        self.fc = nn.Linear(512, num_classes)

    def forward(self, x):
        x = self.layers(self.stem(x))
        return self.fc(Fn.adaptive_avg_pool2d(x, 1).flatten(1))


def flat(sd, keys):
    return np.concatenate([sd[k].detach().cpu().numpy().astype(np.float64).ravel() for k in keys])


def local_train(model, nbatches, seed):
    g = torch.Generator().manual_seed(seed)
    opt = torch.optim.SGD(model.parameters(), lr=LR, momentum=MOM)
    model.train()
    for _ in range(nbatches):
        x = torch.randn(BS, 3, HW, HW, generator=g)
        y = torch.randint(0, C, (BS,), generator=g)
        opt.zero_grad()
        Fn.cross_entropy(model(x), y).backward()
        opt.step()
    return model


def inertness():
    torch.manual_seed(0)
    m = local_train(ResNet18(), 2, seed=1)
    a, b = copy.deepcopy(m), copy.deepcopy(m)
    for mod in b.modules():
        if isinstance(mod, nn.modules.batchnorm._BatchNorm):
            mod.num_batches_tracked += 100000
    g = torch.Generator().manual_seed(2)
    a.train(); b.train()
    with torch.no_grad():
        for _ in range(3):
            x = torch.randn(BS, 3, HW, HW, generator=g)
            a(x); b(x)
    sa, sb = a.state_dict(), b.state_dict()
    rm = max(float((sa[k] - sb[k]).abs().max()) for k in sa if k.endswith("running_mean"))
    rv = max(float((sa[k] - sb[k]).abs().max()) for k in sa if k.endswith("running_var"))
    a.eval(); b.eval()
    with torch.no_grad():
        xt = torch.randn(64, 3, HW, HW, generator=g)
        lo = float((a(xt) - b(xt)).abs().max())
    return {"max_abs_running_mean": rm, "max_abs_running_var": rv, "max_abs_eval_logit": lo}


def main():
    torch.manual_seed(0)
    model = ResNet18()
    sd = model.state_dict()
    pnames = {n for n, _ in model.named_parameters()}
    keys = list(sd.keys())
    tkeys = [k for k in keys if k in pnames]
    bkeys = [k for k in keys if k not in pnames]
    ckeys = [k for k in keys if k.endswith("num_batches_tracked")]
    n_train = sum(sd[k].numel() for k in tkeys)
    n_buf = sum(sd[k].numel() for k in bkeys)
    L = len(ckeys)

    inert = inertness()

    Bi, Bj = 16, 11
    g0 = copy.deepcopy(model.state_dict())
    ci = local_train(copy.deepcopy(model), Bi, seed=10).state_dict()
    cj = local_train(copy.deepcopy(model), Bj, seed=11).state_dict()
    di, dj = flat(ci, keys) - flat(g0, keys), flat(cj, keys) - flat(g0, keys)
    ui, uj = flat(ci, tkeys) - flat(g0, tkeys), flat(cj, tkeys) - flat(g0, tkeys)
    bi, bj = flat(ci, bkeys) - flat(g0, bkeys), flat(cj, bkeys) - flat(g0, bkeys)
    cnt_i, cnt_j = flat(ci, ckeys) - flat(g0, ckeys), flat(cj, ckeys) - flat(g0, ckeys)

    def cos(x, y):
        return float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))

    si, sj = float(bi @ bi / (di @ di)), float(bj @ bj / (dj @ dj))
    cos_full = cos(di, dj)
    cos_pred = math.sqrt((1 - si) * (1 - sj)) * cos(ui, uj) + math.sqrt(si * sj) * cos(bi, bj)
    dist_full = float(((di - dj) ** 2).sum())
    dist_pred = float(((ui - uj) ** 2).sum() + ((bi - bj) ** 2).sum())
    cnt_dist = float(((cnt_i - cnt_j) ** 2).sum())
    out = {
        "model": "ResNet-18 (CIFAR-style, hand-written), 3x32x32 synthetic inputs, 10 classes",
        "optimiser": f"SGD lr={LR} momentum={MOM}, batch {BS}",
        "n_trainable": n_train, "n_buffer": n_buf, "n_bn_layers": L,
        "inert_momentum_default": inert,
        "prop1": {
            "B_i": Bi, "B_j": Bj, "s_i": si, "s_j": sj,
            "trainable_norm_i": float(np.linalg.norm(ui)),
            "counter_share_norm_i": float(cnt_i @ cnt_i / (di @ di)),
            "cos_full": cos_full, "cos_trainable": cos(ui, uj), "cos_pred": cos_pred,
            "cos_abs_err": abs(cos_full - cos_pred),
            "dist_rel_err": abs(dist_full - dist_pred) / dist_full,
            "counter_dist": cnt_dist, "counter_dist_pred": L * (Bi - Bj) ** 2,
            "counter_share_dist": cnt_dist / dist_full,
        },
    }
    with open(os.path.join(ROOT, "results", "defect_probe_resnet.json"), "w") as f:
        json.dump(out, f, indent=2)

    p = out["prop1"]

    def sci(x):
        if x == 0:
            return "0"
        e = int(math.floor(math.log10(abs(x))))
        return f"{x / 10 ** e:.1f}\\times10^{{{e}}}"

    mac = {
        "drNTrain": f"{n_train:,}".replace(",", "{,}"),
        "drNBuf": f"{n_buf:,}".replace(",", "{,}"), "drNBN": str(L),
        "drInertMean": sci(inert["max_abs_running_mean"]),
        "drInertVar": sci(inert["max_abs_running_var"]),
        "drInertLogit": sci(inert["max_abs_eval_logit"]),
        "drPropBi": str(Bi), "drPropBj": str(Bj),
        "drBufShareI": f"{100 * p['s_i']:.1f}",
        "drPropShareI": f"{100 * p['counter_share_norm_i']:.1f}",
        "drPropCosFull": f"{p['cos_full']:.3f}", "drPropCosSig": f"{p['cos_trainable']:.3f}",
        "drPropCosErr": sci(p["cos_abs_err"]), "drPropDistErr": sci(p["dist_rel_err"]),
        "drPropDistShare": f"{100 * p['counter_share_dist']:.1f}",
        "drCounterDist": str(int(round(p["counter_dist"]))),
    }
    lines = ["% Generated by experiments/counter_defect/probe_resnet.py "
             "-> results/defect_probe_resnet.json. DO NOT EDIT."]
    lines += [f"\\providecommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    with open(os.path.join(ROOT, "paper", "numbers_defect_resnet.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
