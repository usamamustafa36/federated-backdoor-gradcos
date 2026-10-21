"""Malicious data share per seed under random vs share-matched selection
(iteration 6). Deterministic from the partition code; no training.
Writes results/calib_iter6/mal_shares.json.
  python3 -m experiments.calib_iter6.shares
"""
import json
import numpy as np
from src.config import PROJECT_ROOT, load_config
from src.data.preprocess import load_dataset
from src.data.partition import partition_data
from src.fl.build import assign_malicious, assign_malicious_share_matched


def main():
    cfg = load_config("configs/p3_full.yaml")
    ds = load_dataset(cfg)
    K, m, a = cfg.federated.num_clients, 0.2, cfg.federated.dirichlet_alpha
    out = {"num_train_rows": int(len(ds.y_train)), "ratio": m, "tol": 0.01, "rows": []}
    for part in ("dirichlet", "iid"):
        for s in range(42, 52):
            parts = partition_data(ds.y_train, K, part, a, s)
            sz = np.array([len(p) for p in parts])
            sh = sz / sz.sum()
            r = sorted(assign_malicious(K, m, s))
            q = sorted(assign_malicious_share_matched(sz, m, s, 0.01))
            out["rows"].append(dict(partition=part, seed=s, sizes=sz.tolist(),
                                    random_cids=r, random_share=float(sh[r].sum()),
                                    matched_cids=q, matched_share=float(sh[q].sum()),
                                    matched_rows=sz[q].tolist()))
    p = PROJECT_ROOT / "results" / "calib_iter6" / "mal_shares.json"
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p)


if __name__ == "__main__":
    main()
