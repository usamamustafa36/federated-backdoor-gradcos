"""FLAME mechanism probe (iteration 29; exploratory, logging only).

Runs one attacked IID FLAME cell in the defect arm (configs/p3_full.yaml) and, every round,
records for the updates the server received: each client's buffer share, counter delta and
trainable norm; mean full-vector and trainable-only cosines (attacker-honest, honest-honest,
attacker-attacker); and which clients FLAME's majority cluster (src/defenses/flame.py) admits
when it is given the full vector or only the trainable coordinates. No decision is changed.

Run from the repo root, with a copy of configs/p3_full.yaml whose logging.out_dir points at a
scratch directory (so no campaign cell is written):
  PYTHONPATH=. OMP_NUM_THREADS=2 python3 -u experiments/flame_probe/flame_probe.py \
    results/flame_probe/flame_iid_s42.jsonl --config <copy> --device cpu --rounds 10 \
    --tag probe_iid --partition iid --defenses flame --triggers fixed --ratios 0.2 \
    --poisons 0.1 --variants simple --seeds 42 --skip-clean --mal-local-epochs 15
"""
import json, sys
import numpy as np
from flwr.common import parameters_to_ndarrays
import src.fl.engine as E
from src.defenses.flame import FLAME
OUT = sys.argv[1]; sys.argv = [sys.argv[0]] + sys.argv[2:]

cls = [c for c in vars(E).values() if isinstance(c, type) and hasattr(c, "_defect_diagnostics")][0]
orig = cls._defect_diagnostics
state = {"rnd": 0}
def patched(self, results, pre_global):
    out = orig(self, results, pre_global)
    state["rnd"] += 1
    try:
        g = np.concatenate([w.ravel() for w in pre_global]).astype(np.float64)
        D = np.stack([np.concatenate([w.ravel() for w in parameters_to_ndarrays(fr.parameters)]).astype(np.float64) - g for _, fr in results])
        mal = np.array([bool(fr.metrics.get("malicious", 0)) for _, fr in results])
        m = np.asarray(self._trainable_mask(), dtype=bool)
        rec = {"round": state["rnd"], "mal": mal.tolist()}
        sq = (D ** 2).sum(1); sqb = (D[:, ~m] ** 2).sum(1)
        rec["buf_share"] = (sqb / sq).tolist()
        bi = np.argmax(np.abs(D[:, ~m]).mean(0))
        rec["counter"] = D[:, ~m][:, bi].tolist()
        rec["tr_norm"] = np.sqrt((D[:, m] ** 2).sum(1)).tolist()
        fl = FLAME.__new__(FLAME)
        for name, X in (("full", D), ("trainable", D[:, m])):
            U = X / np.linalg.norm(X, axis=1, keepdims=True)
            C = np.clip(U @ U.T, -1, 1)
            n = len(C); iu = np.triu_indices(n, 1)
            hh = [C[i, j] for i, j in zip(*iu) if not mal[i] and not mal[j]]
            mh = [C[i, j] for i in range(n) for j in range(n) if mal[i] and not mal[j]]
            mm = [C[i, j] for i, j in zip(*iu) if mal[i] and mal[j]]
            cd = (1 - C).astype(np.float64); np.fill_diagonal(cd, 0)
            adm = sorted(FLAME._majority_cluster(fl, cd, n))
            # mean cosine of each client to all others (typicality)
            typ = [(C[i].sum() - 1) / (n - 1) for i in range(n)]
            rec[name] = {"hh": float(np.mean(hh)), "mh": float(np.mean(mh)), "mm": float(np.mean(mm)) if mm else None,
                         "admitted": adm, "typicality": typ}
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        print("PROBE ERROR", repr(e), flush=True)
    return out
cls._defect_diagnostics = patched
from experiments import run_sweep
run_sweep.main()
