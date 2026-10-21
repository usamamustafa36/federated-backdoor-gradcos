"""Why does seed 46 resist the backdoor? Data-only probe (iteration 7; no training).

For every Dirichlet seed 42-51 with the share-matched attackers used by the
calibration, recompute exactly what the malicious clients poison
(`poison_local_data`, seed = run seed + cid) and what the honest clients hold,
and report per-class composition of
  * the poisoned rows (source class of each trigger-stamped, relabelled row),
  * the BSR test set (every attack-class test row, trigger stamped),
  * honest rows per class,
plus the trigger columns' natural value ranges per class (does any class
already sit on the trigger values?).

  python3 -m experiments.calib_iter6.s46_probe
Writes results/calib_iter6/s46_probe.json.
"""
import json
import numpy as np
from src.config import PROJECT_ROOT, load_config
from src.data.preprocess import load_dataset
from src.data.partition import partition_data
from src.fl.build import assign_malicious_share_matched
from src.attacks import _trigger_for
from src.attacks.triggers import poison_local_data


def main():
    cfg = load_config("configs/calib6_full.yaml")
    ds = load_dataset(cfg)
    trig = _trigger_for(cfg, ds)
    names = list(ds.class_names)
    C, b = ds.num_classes, ds.benign_index
    K, a = cfg.federated.num_clients, cfg.federated.dirichlet_alpha
    ytr, yte = ds.y_train, ds.y_test
    out = {"class_names": names, "trigger_columns": [ds.feature_names[c] for c in trig.columns],
           "trigger_values": trig.values.tolist()}

    # BSR test-set composition (fixed across seeds)
    te_att = yte[yte != b]
    out["bsr_test_class_counts"] = np.bincount(te_att, minlength=C).tolist()

    # Natural values of the trigger columns per class (train set)
    col = {}
    for j, c in enumerate(trig.columns):
        v = ds.x_train[:, c]
        uniq = np.unique(np.round(v, 3))
        col[ds.feature_names[c]] = {
            "trigger_value": float(trig.values[j]),
            "n_unique": int(len(uniq)),
            "min": float(v.min()), "max": float(v.max()),
            "frac_ge_trigger_minus_0.25": float(np.mean(np.abs(v - trig.values[j]) <= 0.25)),
            "per_class_mean": [float(v[ytr == k].mean()) for k in range(C)],
        }
    out["trigger_column_stats"] = col
    # rows whose trigger block is already within L_inf 0.5 of the trigger, per class
    blk = ds.x_train[:, trig.columns]
    near = np.max(np.abs(blk - trig.values[None, :]), axis=1) <= 0.5
    out["near_trigger_rows_per_class"] = np.bincount(ytr[near], minlength=C).tolist()

    rows = []
    for s in range(42, 52):
        parts = partition_data(ytr, K, "dirichlet", a, s)
        sz = np.array([len(p) for p in parts])
        mal = sorted(assign_malicious_share_matched(sz, 0.2, s, 0.01))
        pois = np.zeros(C, dtype=int)            # source class of poisoned rows
        mal_cls = np.zeros(C, dtype=int)
        for cid in mal:
            y = ytr[parts[cid]]
            x = ds.x_train[parts[cid]]
            mal_cls += np.bincount(y, minlength=C)
            _, yp = poison_local_data(x, y, trig, b, cfg.attack.poison_rate, seed=s + cid)
            changed = (yp != y)
            pois += np.bincount(y[changed], minlength=C)
        hon = np.zeros(C, dtype=int)
        for cid in range(K):
            if cid not in mal:
                hon += np.bincount(ytr[parts[cid]], minlength=C)
        # fraction of the BSR test set whose class the attackers poisoned at all,
        # weighted by the poison count per class relative to that class's honest rows
        cover = float(sum(out["bsr_test_class_counts"][k] for k in range(C) if pois[k] > 0)
                      / len(te_att))
        rows.append(dict(seed=s, mal=mal, mal_rows=int(sz[mal].sum()),
                         mal_class_counts=mal_cls.tolist(), poisoned_by_class=pois.tolist(),
                         n_poisoned=int(pois.sum()), honest_class_counts=hon.tolist(),
                         poison_frac_of_all_rows=float(pois.sum() / sz.sum()),
                         bsr_test_coverage=cover))
    out["seeds"] = rows
    p = PROJECT_ROOT / "results" / "calib_iter6" / "s46_probe.json"
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p)
    print("BSR test classes:", dict(zip(names, out["bsr_test_class_counts"])))
    print("near-trigger train rows/class:", dict(zip(names, out["near_trigger_rows_per_class"])))
    for k, v in col.items():
        print(k, {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items()
                  if kk != "per_class_mean"}, [round(x, 2) for x in v["per_class_mean"]])
    for r in rows:
        print(r["seed"], r["mal"], "poisoned", r["n_poisoned"], dict(zip(names, r["poisoned_by_class"])),
              "| mal benign", r["mal_class_counts"][b], "| cover", round(r["bsr_test_coverage"], 3))


if __name__ == "__main__":
    main()
