#!/usr/bin/env python3
"""Generality probe (iteration 19, CPU): does the num_batches_tracked hazard carry
over to a standard BatchNorm image model on real images?

Setting (stated in the output JSON and in the supplement):
  * CIFAR-10 (python pickles, read from --cifar), N_TRAIN training images split
    over 10 clients, 2 of them label-flipping attackers (y -> (y+1) mod 10,
    the attack of yjlee22/byzantineFL); a class-balanced root set of ROOT clean
    images held by the server (FLTrust's 100-image root set);
  * ResNet-20 (He et al. 2016, CIFAR variant, option-A shortcuts, 19 BatchNorm
    layers, PyTorch default momentum=0.1 so the counter is inert);
  * one local epoch per round, SGD lr 0.05 momentum 0.9 wd 5e-4, batch 32;
    clients transmit their full state_dict, as Flower's quick-start does;
  * partition `iid` (equal shards: every client runs the same number of
    batches) or `dirichlet` (label Dirichlet alpha=0.5: shard sizes differ).

Every round the SAME client updates are scored by each rule on three vectors:
  full      flattened state_dict (counter included)      -- the exposed pipeline
  nocount   state_dict without num_batches_tracked       -- buffers, no counter
  trainable parameters() only                            -- the fixed pipeline
Rules: Krum (single pick), Multi-Krum (keep n-f), FLTrust (ReLU-cosine trust to
the server's root update, B_0 = ceil(ROOT/32) batches). Recorded per round: the
counter and buffer shares of each client's squared norm, the selections, the
trust scores, and whether attackers are kept / trusted under each vector. This
is a decision-level counterfactual: one trajectory, every arm scored on it.

`--agg` chooses the rule that drives the trajectory (closed loop):
  fedavg | fltrust_full | fltrust_trainable | mkrum_full | mkrum_trainable.
Resumable: a checkpoint is written after every round; a finished run is skipped.
Output: results/generality_cifar/<agg>_<partition>_s<seed>.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import pickle
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
N_CLIENTS, N_MAL, ROOT = 10, 2, 100
N_TRAIN = 10000          # overridden by --n-train
BS, LR, MOM, WD = 32, 0.05, 0.9, 5e-4
ALPHA = 0.5


# ----------------------------------------------------------------- data
def load_cifar(root):
    xs, ys = [], []
    for i in range(1, 6):
        with open(os.path.join(root, f"data_batch_{i}"), "rb") as f:
            d = pickle.load(f, encoding="bytes")
        xs.append(d[b"data"]); ys.append(d[b"labels"])
    with open(os.path.join(root, "test_batch"), "rb") as f:
        d = pickle.load(f, encoding="bytes")
    xt, yt = d[b"data"], d[b"labels"]
    x = np.concatenate(xs).reshape(-1, 3, 32, 32).astype(np.float32) / 255.0
    xt = np.asarray(xt).reshape(-1, 3, 32, 32).astype(np.float32) / 255.0
    m = x.mean((0, 2, 3), keepdims=True); s = x.std((0, 2, 3), keepdims=True)
    return ((x - m) / s, np.concatenate(ys).astype(np.int64),
            (xt - m) / s, np.asarray(yt, dtype=np.int64))


def sha_files(root):
    h = hashlib.sha256()
    for n in [f"data_batch_{i}" for i in range(1, 6)] + ["test_batch"]:
        with open(os.path.join(root, n), "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def partition(y, partition_kind, rng):
    idx = rng.permutation(len(y))
    root_idx, pool = [], []
    for c in range(10):                       # class-balanced root set first
        cidx = idx[y[idx] == c]
        root_idx.extend(cidx[:ROOT // 10]); pool.extend(cidx[ROOT // 10:])
    pool = rng.permutation(np.array(pool))[:N_TRAIN]
    if partition_kind == "iid":
        parts = np.array_split(pool, N_CLIENTS)
    else:
        parts = [[] for _ in range(N_CLIENTS)]
        for c in range(10):
            cidx = pool[y[pool] == c]
            p = rng.dirichlet([ALPHA] * N_CLIENTS)
            cuts = (np.cumsum(p) * len(cidx)).astype(int)[:-1]
            for k, part in enumerate(np.split(cidx, cuts)):
                parts[k].extend(part.tolist())
        parts = [np.array(p, dtype=np.int64) for p in parts]
        for k in range(N_CLIENTS):            # every client needs >= 1 batch
            if len(parts[k]) < BS:
                parts[k] = np.concatenate([parts[k], rng.choice(pool, BS - len(parts[k]))])
    return np.array(root_idx), [np.asarray(p) for p in parts]


# ----------------------------------------------------------------- model
class Block(nn.Module):
    def __init__(self, cin, cout, stride):
        super().__init__()
        self.c1 = nn.Conv2d(cin, cout, 3, stride, 1, bias=False); self.b1 = nn.BatchNorm2d(cout)
        self.c2 = nn.Conv2d(cout, cout, 3, 1, 1, bias=False); self.b2 = nn.BatchNorm2d(cout)
        self.pad = cout - cin
        self.stride = stride

    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        sc = x
        if self.stride != 1 or self.pad:      # option A: subsample + zero-pad
            sc = x[:, :, ::self.stride, ::self.stride]
            sc = F.pad(sc, (0, 0, 0, 0, self.pad // 2, self.pad - self.pad // 2))
        return F.relu(y + sc)


class ResNet20(nn.Module):
    def __init__(self, k=10):
        super().__init__()
        self.c = nn.Conv2d(3, 16, 3, 1, 1, bias=False); self.b = nn.BatchNorm2d(16)
        layers, cin = [], 16
        for cout, stride in ((16, 1), (32, 2), (64, 2)):
            for j in range(3):
                layers.append(Block(cin, cout, stride if j == 0 else 1)); cin = cout
        self.layers = nn.Sequential(*layers)
        self.f = nn.Linear(64, k)

    def forward(self, x):
        x = self.layers(F.relu(self.b(self.c(x))))
        return self.f(F.adaptive_avg_pool2d(x, 1).flatten(1))


def train_local(model, x, y, gen):
    opt = torch.optim.SGD(model.parameters(), lr=LR, momentum=MOM, weight_decay=WD)
    model.train()
    perm = torch.randperm(len(x), generator=gen)
    nb = 0
    for i in range(0, len(x), BS):
        b = perm[i:i + BS]
        xb = x[b]
        if torch.rand(1, generator=gen).item() < 0.5:   # light augmentation: h-flip
            xb = xb.flip(3)
        opt.zero_grad(); F.cross_entropy(model(xb), y[b]).backward(); opt.step()
        nb += 1
    return nb


@torch.no_grad()
def evaluate(model, x, y):
    model.eval()
    correct = 0
    for i in range(0, len(x), 1000):
        correct += int((model(x[i:i + 1000]).argmax(1) == y[i:i + 1000]).sum())
    return correct / len(x)


# ----------------------------------------------------------------- rules
def krum_scores(V, f):
    n = len(V)
    sq = (V * V).sum(1)
    D = sq[:, None] + sq[None, :] - 2.0 * V @ V.T
    D = np.maximum(D, 0.0); np.fill_diagonal(D, np.inf)
    k = max(1, n - f - 2)
    return np.array([np.sort(D[i])[:k].sum() for i in range(n)])


def fltrust_weights(V, v0):
    n0 = np.linalg.norm(v0) + 1e-12
    cos = np.array([float(v @ v0) / ((np.linalg.norm(v) + 1e-12) * n0) for v in V])
    ts = np.maximum(cos, 0.0)
    w = ts / ts.sum() if ts.sum() > 0 else np.zeros_like(ts)
    return cos, ts, w


def run(args):
    out_dir = os.path.join(ROOT_DIR, "results", "generality_cifar")
    os.makedirs(out_dir, exist_ok=True)
    tag = f"{args.agg}_{args.partition}_s{args.seed}"
    out_path = os.path.join(out_dir, tag + ".json")
    ck_path = os.path.join(out_dir, "_ckpt", tag + ".pt")
    os.makedirs(os.path.dirname(ck_path), exist_ok=True)
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        print(f"[skip] {tag} done"); return
    global N_TRAIN
    N_TRAIN = args.n_train
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    X, Y, XT, YT = load_cifar(args.cifar)
    root_idx, parts = partition(Y, args.partition, rng)
    Xt, Yt = torch.from_numpy(X), torch.from_numpy(Y)
    XTt, YTt = torch.from_numpy(XT), torch.from_numpy(YT)
    mal = set(range(N_MAL))                   # clients 0..N_MAL-1 attack
    model = ResNet20()
    sd0 = model.state_dict()
    pnames = {n for n, _ in model.named_parameters()}
    keys = list(sd0.keys())
    tmask = np.concatenate([np.full(sd0[k].numel(), k in pnames) for k in keys])
    cmask = np.concatenate([np.full(sd0[k].numel(), k.endswith("num_batches_tracked"))
                            for k in keys])
    vec = {"full": np.ones_like(tmask), "nocount": ~cmask, "trainable": tmask}

    def flat(sd):
        return np.concatenate([sd[k].detach().double().numpy().ravel() for k in keys])

    def unflat(v, like):
        out, o = {}, 0
        for k in keys:
            t = like[k]; n = t.numel()
            out[k] = torch.from_numpy(v[o:o + n].reshape(t.shape)).to(t.dtype) \
                if t.dtype.is_floating_point else \
                torch.from_numpy(np.rint(v[o:o + n]).reshape(t.shape)).to(t.dtype)
            o += n
        return out

    start, log = 1, []
    gen = torch.Generator().manual_seed(args.seed + 7)
    if os.path.exists(ck_path):
        ck = torch.load(ck_path, weights_only=False)
        model.load_state_dict(ck["model"]); log = ck["log"]; start = ck["round"] + 1
        gen.set_state(ck["gen"])
        print(f"[resume] {tag} from round {start}")

    for r in range(start, args.rounds + 1):
        t0 = time.time()
        g_sd = copy.deepcopy(model.state_dict()); g = flat(g_sd)
        D, sizes, nbs = [], [], []
        for c in range(N_CLIENTS):
            net = copy.deepcopy(model)
            ci = torch.from_numpy(parts[c])
            yc = Yt[ci]
            if c in mal:
                yc = (yc + 1) % 10
            nbs.append(train_local(net, Xt[ci], yc, gen))
            D.append(flat(net.state_dict()) - g); sizes.append(len(ci))
        D = np.stack(D)
        srv = copy.deepcopy(model)
        b0 = train_local(srv, Xt[torch.from_numpy(root_idx)], Yt[torch.from_numpy(root_idx)], gen)
        d0 = flat(srv.state_dict()) - g

        rec = {"round": r, "batches": nbs, "B0": b0}
        tot = (D * D).sum(1)
        rec["counter_share"] = ((D[:, cmask] ** 2).sum(1) / tot).tolist()
        rec["buffer_share"] = ((D[:, ~tmask] ** 2).sum(1) / tot).tolist()
        rec["q0"] = float((d0[cmask] ** 2).sum() / (d0 @ d0))
        keep = N_CLIENTS - N_MAL
        dec = {}
        for name, m in vec.items():
            V, v0 = D[:, m], d0[m]
            ks = krum_scores(V, N_MAL)
            order = np.argsort(ks)
            cos, ts, w = fltrust_weights(V, v0)
            U = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-12)
            C = U @ U.T
            dec[name] = {
                "krum_pick": int(order[0]),
                "mkrum_keep": sorted(order[:keep].tolist()),
                "fltrust_cos": cos.tolist(), "fltrust_w": w.tolist(),
                "mean_pair_cos": float((C.sum() - N_CLIENTS) / (N_CLIENTS * (N_CLIENTS - 1))),
            }
        rec["dec"] = dec

        # ---- aggregation (closed loop)
        kind = args.agg
        if kind == "fedavg":
            w = np.array(sizes, float); w /= w.sum()
            agg = w @ D
        elif kind.startswith("mkrum"):
            sel = dec[kind.split("_")[1]]["mkrum_keep"]
            w = np.zeros(N_CLIENTS); w[sel] = np.array(sizes, float)[sel]; w /= w.sum()
            agg = w @ D
        else:                                  # FLTrust: trust-weighted, rescaled to ||d0||
            m = vec[kind.split("_")[1]]
            ts = np.maximum(np.array(dec[kind.split("_")[1]]["fltrust_cos"]), 0.0)
            n0 = np.linalg.norm(d0[m])
            agg = np.zeros_like(g)
            if ts.sum() > 0:
                for i in range(N_CLIENTS):
                    if ts[i] > 0:
                        agg += ts[i] * D[i] * (n0 / (np.linalg.norm(D[i, m]) + 1e-12))
                agg /= ts.sum()
        model.load_state_dict(unflat(g + agg, g_sd))
        if r % args.eval_every == 0 or r == args.rounds:
            rec["test_acc"] = evaluate(model, XTt, YTt)
        rec["sec"] = round(time.time() - t0, 1)
        log.append(rec)
        print(f"[{tag}] r{r} acc={rec.get('test_acc', float('nan')):.3f} "
              f"cshare={np.mean(rec['counter_share']):.3f} B={nbs} B0={b0} "
              f"krum full/tr={dec['full']['krum_pick']}/{dec['trainable']['krum_pick']} "
              f"{rec['sec']}s", flush=True)
        tmp = ck_path + ".tmp"
        torch.save({"model": model.state_dict(), "log": log, "round": r,
                    "gen": gen.get_state()}, tmp)
        os.replace(tmp, ck_path)

    res = {
        "setting": {"model": "ResNet-20 (option A), 19 BatchNorm layers",
                    "n_trainable": int(tmask.sum()), "n_buffer": int((~tmask).sum()),
                    "n_bn": int(sum(k.endswith('num_batches_tracked') for k in keys)),
                    "dataset": "CIFAR-10", "cifar_sha256": sha_files(args.cifar),
                    "n_clients": N_CLIENTS, "n_mal": N_MAL, "attack": "label flip y->(y+1)%10",
                    "n_train": N_TRAIN, "root": ROOT, "batch": BS, "lr": LR, "momentum": MOM,
                    "wd": WD, "local_epochs": 1, "alpha": ALPHA, "rounds": args.rounds,
                    "partition": args.partition, "agg": args.agg, "seed": args.seed,
                    "shard_sizes": [int(len(p)) for p in parts]},
        "log": log,
    }
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(res, f)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, out_path)
    print(f"[done] {tag}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cifar", default=os.environ.get("CIFAR_DIR", os.path.join(ROOT_DIR, "data", "cifar10", "cifar-10-batches-py")))
    ap.add_argument("--agg", default="fedavg",
                    choices=["fedavg", "fltrust_full", "fltrust_trainable",
                             "mkrum_full", "mkrum_trainable"])
    ap.add_argument("--partition", default="dirichlet", choices=["iid", "dirichlet"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--n-train", type=int, default=10000)
    ap.add_argument("--eval-every", type=int, default=5)
    ap.add_argument("--threads", type=int, default=2)
    run(ap.parse_args())
