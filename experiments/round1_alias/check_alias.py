"""Iteration 5: controlled check of the round-1 aliasing defect in FederatedEngine.

tu.get_weights returns numpy VIEWS of the model's storage. FederatedEngine.__init__
stored those views as global_weights, so in round 1 every client's local training
writes through to global_weights. `federated.copy_initial_global: true` (default
off) copies them. This script measures, on a tiny CPU config:

  trace    what round 1 actually does with and without the copy: where each client
           starts (distance to the initial weights, BatchNorm counter at start),
           what the defense receives as the "global", and round 2 for contrast.
  outcome  paired bug-vs-fix runs (same seed, same data) for several rules and both
           signal subspaces; reports the paper's measured quantities: last-5-round
           CA/BSR/DR/FPR and the all-round diagnostics.

Writes results/round1_alias/{trace.json, outcome_*.json, summary.json}.
CPU only, 2 threads.  Usage:
  python3 -m experiments.round1_alias.check_alias trace
  python3 -m experiments.round1_alias.check_alias outcome [--seeds 42 43 44]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
import numpy as np
import torch

torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "2")))

from src.config import PROJECT_ROOT, load_config, set_seed  # noqa: E402
from src.data.preprocess import load_dataset  # noqa: E402
from src.attacks import make_attack, make_backdoor_eval  # noqa: E402
from src.fl.build import build_clients, build_strategy  # noqa: E402
from src.fl.engine import FederatedEngine  # noqa: E402
from src.fl import torch_utils as tu  # noqa: E402
from experiments.run_sweep import make_cfg, run_one  # noqa: E402

OUT = PROJECT_ROOT / "results" / "round1_alias"


def tiny_base(mode: str, rows: int, rounds: int):
    base = load_config(f"configs/p1_{mode}.yaml")
    base.device = "cpu"
    base.data.max_train_rows = rows
    base.data.max_test_rows = max(2000, rows // 4)
    base.federated.rounds = rounds
    base.federated.partition = "dirichlet"
    base._raw["data"]["max_train_rows"] = rows
    base._raw["data"]["max_test_rows"] = base.data.max_test_rows
    base._raw["device"] = "cpu"
    return base


def set_flag(cfg, on: bool):
    cfg.federated.copy_initial_global = bool(on)
    cfg._raw["federated"]["copy_initial_global"] = bool(on)
    return cfg


def flat(ws, mask=None):
    v = np.concatenate([np.asarray(w, dtype=np.float64).ravel() for w in ws])
    return v if mask is None else v[mask]


def trace(args):
    rec = {}
    base = tiny_base("full", args.rows, 2)
    set_seed(base.seed)
    ds = load_dataset(base)
    for on in (False, True):
        cfg = make_cfg(base, **{"defense.name": "foolsgold", "attack.enabled": False})
        set_flag(cfg, on)
        set_seed(cfg.seed)
        strategy = build_strategy(cfg, ds, "cpu")
        clients = build_clients(cfg, ds, None)
        eng = FederatedEngine(cfg, ds, clients, strategy, "cpu")
        keys = list(eng.model.state_dict().keys())
        cnt_idx = [i for i, k in enumerate(keys) if k.endswith("num_batches_tracked")]
        tmask = np.asarray(eng._trainable_mask(), dtype=bool)
        init = flat(eng.global_weights, None).copy()
        log = {"starts": [], "refs": []}
        state = {"rnd": 0, "last_trained": None, "round_start_global": None}
        orig_fit = eng._client_fit

        def fit(client):
            # what the engine will load for this client (before set_weights)
            g_now = flat(eng.global_weights).copy()
            start_cnt = int(sum(int(np.asarray(eng.global_weights[i]).ravel()[0]) for i in cnt_idx))
            fr = orig_fit(client)
            from flwr.common import parameters_to_ndarrays
            trained = parameters_to_ndarrays(fr.parameters)
            log["starts"].append({
                "round": state["rnd"], "cid": client.cid,
                "start_dist_to_round_global": float(np.linalg.norm(
                    (g_now - state["round_start_global"])[tmask])),
                "start_counter_sum": start_cnt,
                "trained_counter_sum": int(sum(int(np.asarray(trained[i]).ravel()[0])
                                               for i in cnt_idx)),
                "n_rows": int(len(client.y)),
            })
            state["last_trained"] = flat(trained).copy()
            return fr

        eng._client_fit = fit
        orig_set = strategy.set_current_global

        def set_cur(w):
            ref = flat(w).copy()
            log["refs"].append({
                "round": state["rnd"],
                "ref_dist_to_round_start_global": float(np.linalg.norm(
                    (ref - state["round_start_global"])[tmask])),
                "ref_dist_to_last_client": float(np.linalg.norm(
                    (ref - state["last_trained"])[tmask])),
                "ref_counter_sum": int(sum(int(np.asarray(w[i]).ravel()[0]) for i in cnt_idx)),
            })
            return orig_set(w)

        strategy.set_current_global = set_cur
        # drive the two rounds by hand through run(): patch the round counter via
        # the heartbeat hook is overkill; instead wrap _select_clients.
        orig_sel = eng._select_clients

        def sel(rnd):
            state["rnd"] = rnd
            # the global at the START of the round, copied before anyone trains
            state["round_start_global"] = flat(eng.global_weights).copy()
            return orig_sel(rnd)

        eng._select_clients = sel
        eng.run(verbose=False)
        # Per-client start distance: in the defect, client k starts where k-1 ended.
        rec["fix" if on else "bug"] = log
        rec["init_trainable_norm"] = float(np.linalg.norm(init[tmask]))
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(rec, open(OUT / "trace.json", "w"), indent=1)
    for k in ("bug", "fix"):
        print(f"== {k}")
        for r in rec[k]["starts"]:
            print(f"  r{r['round']} cid{r['cid']}: start dist to round-start global "
                  f"{r['start_dist_to_round_global']:.4f}, counter start {r['start_counter_sum']} -> trained "
                  f"{r['trained_counter_sum']}, rows {r['n_rows']}")
        for r in rec[k]["refs"]:
            print(f"  r{r['round']} defense reference: dist to round-start global "
                  f"{r['ref_dist_to_round_start_global']:.4f}, to last client "
                  f"{r['ref_dist_to_last_client']:.4f}, counter sum {r['ref_counter_sum']}")


DIAG = ["buffer_norm_share", "buffer_dist_share", "pair_cos_full", "pair_cos_sig"]


def tailm(xs, k=5):
    xs = [x for x in xs[-k:] if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else float("nan")


def allm(xs, skip_first=False):
    xs = xs[1:] if skip_first else xs
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else float("nan")


def outcome(args):
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for mode in args.modes:
        base = tiny_base(mode, args.rows, args.rounds)
        base.attack.mal_local_epochs = args.mal_epochs
        base._raw["attack"]["mal_local_epochs"] = args.mal_epochs
        base.attack.boost = 1.0
        base._raw["attack"]["boost"] = 1.0
        set_seed(base.seed)
        ds = load_dataset(base)
        for defense in args.defenses:
            for atk in args.attacks:
                for seed in args.seeds:
                    for on in (False, True):
                        over = {"defense.name": defense, "attack.enabled": bool(atk),
                                "seed": seed}
                        cfg = make_cfg(base, **{k: v for k, v in over.items() if k != "seed"})
                        cfg.seed = seed
                        cfg._raw["seed"] = seed
                        if not atk:
                            cfg.attack.malicious_ratio = 0.0
                            cfg.attack.poison_rate = 0.0
                            cfg._raw["attack"]["malicious_ratio"] = 0.0
                            cfg._raw["attack"]["poison_rate"] = 0.0
                        set_flag(cfg, on)
                        tag = f"r1{'fix' if on else 'bug'}_{mode}"
                        t0 = time.time()
                        run_one(cfg, ds, "cpu", OUT, tag, seed_suffix=f"_s{seed}")
                        from experiments.run_sweep import cell_name
                        p = json.load(open(OUT / cell_name(cfg, tag, f"_s{seed}")))
                        h = p["history"]
                        r = {"mode": mode, "defense": defense, "attack": atk, "seed": seed,
                             "fix": on, "sec": round(time.time() - t0, 1),
                             "CA": tailm(h["accuracy"]), "BSR": tailm(h["bsr"]),
                             "DR": tailm(h["detection_rate"]),
                             "FPR": tailm(h["false_positive_rate"]),
                             "CA_r1": h["accuracy"][0], "FPR_r1": h["false_positive_rate"][0]}
                        for k in DIAG:
                            r[k] = allm(h.get(k, []))
                            r[k + "_r2on"] = allm(h.get(k, []), skip_first=True)
                            r[k + "_r1"] = (h.get(k) or [float("nan")])[0]
                        rows.append(r)
                        print(json.dumps(r), flush=True)
                        json.dump(rows, open(OUT / f"outcome_{args.name}.json", "w"), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["trace", "outcome"])
    ap.add_argument("--rows", type=int, default=8000)
    ap.add_argument("--rounds", type=int, default=15)
    ap.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    ap.add_argument("--defenses", nargs="+",
                    default=["fedavg", "foolsgold", "fltrust", "flame", "krum"])
    ap.add_argument("--attacks", nargs="+", type=int, default=[0, 1])
    ap.add_argument("--mal-epochs", type=int, default=5)
    ap.add_argument("--name", default="tiny")
    ap.add_argument("--modes", nargs="+", default=["full", "trainable"])
    args = ap.parse_args()
    trace(args) if args.part == "trace" else outcome(args)


if __name__ == "__main__":
    main()
