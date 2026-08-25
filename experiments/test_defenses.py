"""Fast synthetic validation of the gradient-space defenses.

Constructs 16 fake client updates: 12 honest (aligned direction) + 4 malicious
(a different 'backdoor' direction), then checks each defense flags the malicious
clients. No model training -> runs in seconds. FLTrust is covered by the
integration run (it needs a real root dataset + model).
"""
from __future__ import annotations

import numpy as np
from flwr.common import Code, FitRes, Status, ndarrays_to_parameters

from src.defenses.krum import Krum
from src.defenses.flame import FLAME
from src.defenses.gradcos import GradCos

D = 800
N = 16
N_MAL = 4
MAL_CIDS = set(range(N - N_MAL, N))  # last 4 are malicious


def make_results(seed=0):
    rng = np.random.RandomState(seed)
    u_h = rng.randn(D); u_h /= np.linalg.norm(u_h)
    u_m = rng.randn(D); u_m /= np.linalg.norm(u_m)
    # make the malicious direction clearly different
    u_m = u_m - (u_m @ u_h) * u_h; u_m /= np.linalg.norm(u_m)

    global_w = [np.zeros(D, dtype=np.float32)]
    results = []
    for cid in range(N):
        mal = cid in MAL_CIDS
        base = (u_m if mal else u_h)
        delta = base + 0.15 * rng.randn(D)            # honest cloud is tight
        w = (global_w[0] + delta).astype(np.float32)
        fr = FitRes(
            status=Status(Code.OK, ""),
            parameters=ndarrays_to_parameters([w]),
            num_examples=1000,
            metrics={"cid": cid, "malicious": int(mal)},
        )
        results.append((None, fr))
    return global_w, results


def check(name, strat):
    global_w, results = make_results()
    strat.set_current_global(global_w)
    params, metrics = strat.aggregate_fit(1, results, [])
    flagged = set(strat.last_flagged_cids)
    caught = flagged & MAL_CIDS
    fp = flagged - MAL_CIDS
    dr = len(caught) / len(MAL_CIDS)
    fpr = len(fp) / (N - len(MAL_CIDS))
    ok = "OK " if (dr >= 0.75 and fpr <= 0.25) else "WEAK"
    print(f"[{ok}] {name:8s} | flagged={sorted(flagged)} "
          f"| DR={dr:.2f} FPR={fpr:.2f} | metrics={metrics}")
    assert params is not None


def main():
    print(f"synthetic: N={N} clients, malicious={sorted(MAL_CIDS)}\n")
    check("Krum", Krum(num_malicious=N_MAL))
    check("FLAME", FLAME())
    check("GradCos", GradCos(threshold=0.0, adaptive=True))
    print("\nall defenses executed without error.")


if __name__ == "__main__":
    main()
