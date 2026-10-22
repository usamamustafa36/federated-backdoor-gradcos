"""Iteration 21: mechanism of the fixed-arm FLTrust IID 'shutdown'.

In P3, fixed-arm (trainable-subspace) FLTrust under IID gives every client zero
trust from round 6-15 on, in 10/10 runs, and the global model freezes. This
replays one clean P3 cell on CPU with the exact P3 config (read from the P3 result
JSON) and, every round, logs what FLTrust computed:

  * each client's trainable cosine to the root update g0 and ||g0||, ||g_i||;
  * the global model's loss/accuracy on the root set and on the test set, and
    its predicted-class histogram on the test set;
  * a per-tensor decomposition of <g_i, g0> (which layers make the cosine <= 0);
  * COUNTERFACTUAL root updates computed from the same global model, with the RNG
    state saved and restored so the replayed run itself is untouched:
      bal_w  : the same class-balanced root set, trained WITH the clients'
               class weights (the server currently trains without them);
      nat    : a root set of the same size drawn uniformly from the training rows
               (FLTrust's assumption: root ~ training distribution), no weights;
      nat_w  : the same natural root set, with the clients' class weights.
    For each: the clients' trainable cosines to it.

Nothing here feeds a decision; the replayed run is the unchanged P3 code path.
Usage: python -m experiments.fltrust_shutdown.replay --seed 42 --rounds 10 \
           --partition iid --threads 4 --out results/fltrust_shutdown/replay_iid_s42.json
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import time

import numpy as np
import torch

from src.config import PROJECT_ROOT, _to_namespace, set_seed
from src.data.preprocess import load_dataset
from src.fl import torch_utils as tu
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine

P3_CFG = PROJECT_ROOT / "results/postfix_p3/p3trainable_iid_ciciot2023_fltrust_atk0_m0.0_p0.0_fixed_s42.json"


def rng_state():
    return (random.getstate(), np.random.get_state(), torch.get_rng_state())


def rng_restore(s):
    random.setstate(s[0]); np.random.set_state(s[1]); torch.set_rng_state(s[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--partition", default="iid")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    torch.set_num_threads(args.threads)

    raw = json.load(open(P3_CFG))["config"]
    raw = copy.deepcopy(raw)
    raw["device"] = "cpu"
    raw["federated"]["rounds"] = args.rounds
    raw["federated"]["partition"] = args.partition
    raw["logging"]["out_dir"] = "results/fltrust_shutdown"
    base = _to_namespace(copy.deepcopy(raw)); base._raw = raw
    set_seed(base.seed)                     # dataset drawn with the base seed, as run_sweep
    ds = load_dataset(base)
    cfg = _to_namespace(copy.deepcopy(raw)); cfg._raw = raw
    cfg.seed = args.seed; raw["seed"] = args.seed
    set_seed(cfg.seed)
    clients = build_clients(cfg, ds, None)
    strat = build_strategy(cfg, ds, "cpu")
    eng = FederatedEngine(cfg, ds, clients, strat, "cpu", backdoor_eval=None)
    cw = eng.class_weights
    mask = strat.signal_mask
    assert mask is not None, "expected the trainable (fixed) arm"

    # tensor boundaries for the per-tensor decomposition
    from src.models.cnn_lstm import build_model
    m0 = build_model(cfg, ds.num_features, ds.num_classes)
    names, sizes = [], []
    for k, v in m0.state_dict().items():
        names.append(k); sizes.append(int(v.numel()))
    bounds = np.cumsum([0] + sizes)

    # natural root set: same size as the balanced one, uniform over training rows
    n_root = len(strat.root_y)
    rs = np.random.RandomState(args.seed + 7777)
    nat_idx = rs.choice(len(ds.y_train), size=n_root, replace=False)
    nat_x, nat_y = ds.x_train[nat_idx], ds.y_train[nat_idx]

    def root_update(x, y, weights):
        model = build_model(cfg, ds.num_features, ds.num_classes)
        tu.set_weights(model, [w.astype(np.float32) for w in strat.current_global])
        tu.local_train(model, x, y, epochs=cfg.federated.local_epochs, lr=cfg.model.lr,
                       batch_size=cfg.federated.batch_size, device="cpu",
                       class_weights=weights)
        g = strat.flatten(strat.current_global)
        return strat.flatten([w.astype(np.float64) for w in tu.get_weights(model)]) - g

    def loss_acc(x, y):
        model = build_model(cfg, ds.num_features, ds.num_classes)
        tu.set_weights(model, [w.astype(np.float32) for w in strat.current_global])
        ev = tu.evaluate(model, x, y, ds.num_classes, "cpu")
        return float(ev["loss"]), float(ev["accuracy"])

    def pred_hist():
        model = build_model(cfg, ds.num_features, ds.num_classes)
        tu.set_weights(model, [w.astype(np.float32) for w in strat.current_global])
        model.eval()
        with torch.no_grad():
            p = []
            for i in range(0, len(ds.x_test), 2048):
                p.append(model(torch.tensor(ds.x_test[i:i + 2048], dtype=torch.float32)).argmax(1).numpy())
        return np.bincount(np.concatenate(p), minlength=ds.num_classes).tolist()

    def cosines(g0, deltas):
        a = g0[mask]; na = np.linalg.norm(a) + 1e-12
        return [float(np.dot(d[mask], a) / ((np.linalg.norm(d[mask]) + 1e-12) * na)) for d in deltas]

    log = {"seed": args.seed, "partition": args.partition, "n_root": n_root,
           "root_class_counts": np.bincount(strat.root_y, minlength=ds.num_classes).tolist(),
           "nat_class_counts": np.bincount(nat_y, minlength=ds.num_classes).tolist(),
           "train_class_counts": np.bincount(ds.y_train, minlength=ds.num_classes).tolist(),
           "test_class_counts": np.bincount(ds.y_test, minlength=ds.num_classes).tolist(),
           "class_weights": [float(c) for c in cw], "class_names": ds.class_names,
           "tensor_names": names, "rounds": []}

    orig_server_update = strat._server_update
    cache = {}

    def wrapped_server_update():
        g0 = orig_server_update(); cache["g0"] = g0; return g0
    strat._server_update = wrapped_server_update

    orig_agg = strat.aggregate_fit

    def wrapped_agg(rnd, results, failures):
        t0 = time.time()
        out = orig_agg(rnd, results, failures)
        g0 = cache["g0"]
        g = strat.flatten(strat.current_global)
        deltas = [strat.flatten(nds) - g for _, nds, _, _ in strat.extract(results)]
        a = g0[mask]
        rec = {"round": rnd,
               "flagged": len(strat.last_flagged_cids),
               "g0_norm": float(np.linalg.norm(a)),
               "client_norms": [float(np.linalg.norm(d[mask])) for d in deltas],
               "cos": cosines(g0, deltas),
               "cos_mean_update": cosines(g0, [np.mean(deltas, axis=0)])[0]}
        # per-tensor contribution to <g_i, g0> (trainable coords only), mean over clients
        contrib = {}
        for j, nm in enumerate(names):
            lo, hi = bounds[j], bounds[j + 1]
            if not mask[lo:hi].any():
                continue
            contrib[nm] = float(np.mean([np.dot(d[lo:hi], g0[lo:hi]) for d in deltas]))
        rec["dot_by_tensor"] = contrib
        rec["root_loss_acc"] = loss_acc(strat.root_x, strat.root_y)
        rec["nat_loss_acc"] = loss_acc(nat_x, nat_y)
        rec["test_pred_hist"] = pred_hist()
        # counterfactual roots, RNG-neutral
        st = rng_state()
        for tag, (x, y, w) in {"bal_w": (strat.root_x, strat.root_y, cw),
                               "nat": (nat_x, nat_y, None),
                               "nat_w": (nat_x, nat_y, cw),
                               "bal_rep": (strat.root_x, strat.root_y, None)}.items():
            gc = root_update(x, y, w)
            rec[f"cf_{tag}_cos"] = cosines(gc, deltas)
            rec[f"cf_{tag}_g0_norm"] = float(np.linalg.norm(gc[mask]))
            rec[f"cf_{tag}_cos_to_g0"] = cosines(g0, [gc])[0]
        rng_restore(st)
        rec["sec"] = round(time.time() - t0, 1)
        log["rounds"].append(rec)
        print(f"r{rnd} flagged={rec['flagged']} cos[min,max]=[{min(rec['cos']):.3f},{max(rec['cos']):.3f}] "
              f"|g0|={rec['g0_norm']:.3f} |gi|med={np.median(rec['client_norms']):.3f} "
              f"bal_w=[{min(rec['cf_bal_w_cos']):.3f},{max(rec['cf_bal_w_cos']):.3f}] "
              f"nat=[{min(rec['cf_nat_cos']):.3f},{max(rec['cf_nat_cos']):.3f}] "
              f"nat_w=[{min(rec['cf_nat_w_cos']):.3f},{max(rec['cf_nat_w_cos']):.3f}] "
              f"rep=[{min(rec['cf_bal_rep_cos']):.3f},{max(rec['cf_bal_rep_cos']):.3f}] "
              f"pred={rec['test_pred_hist']}", flush=True)
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out + ".tmp", "w") as f:
            json.dump(log, f, indent=1)
        os.replace(args.out + ".tmp", args.out)
        return out
    strat.aggregate_fit = wrapped_agg

    hist = eng.run(verbose=True)
    log["accuracy"] = hist.accuracy
    log["fpr"] = hist.false_positive_rate
    with open(args.out, "w") as f:
        json.dump(log, f, indent=1)


if __name__ == "__main__":
    main()
