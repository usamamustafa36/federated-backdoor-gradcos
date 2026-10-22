"""Apply PREREG_R1's norm-bound rule to the FedAvg pilot cells (seeds 7, 8).

b* = the smallest b in {1, 2} whose mean final-round FedAvg BSR over seeds 7 and 8 is
>= 0.5; if neither reaches it, b* = 2 and the stealthy attacker is flagged as not
implanting. Prints one line "B=<b*>" last (the campaign script reads it); exits 3 if
a pilot cell is missing, so the campaign waits instead of guessing.

    python3 experiments/r1_falsify/choose_b.py [results/r1_falsify]
"""
from __future__ import annotations

import glob
import json
import os
import sys

CANDIDATES = (1, 2)
SEEDS = (7, 8)
THRESH = 0.5


def final_bsr(out_dir: str, b: int, seed: int) -> float | None:
    pat = os.path.join(out_dir, f"r1pilottrainable_dirichlet_*_fedavg_atk1_*_nb{b}_s{seed}.json")
    fs = [f for f in glob.glob(pat) if os.path.getsize(f) > 0]
    if len(fs) != 1:
        return None
    return float(json.load(open(fs[0]))["history"]["bsr"][-1])


def main() -> int:
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "results/r1_falsify"
    means = {}
    for b in CANDIDATES:
        v = [final_bsr(out_dir, b, s) for s in SEEDS]
        if any(x is None for x in v):
            print(f"missing pilot cell for b={b}: {v}")
            return 3
        means[b] = sum(v) / len(v)
        print(f"b={b}: final BSR {['%.3f' % x for x in v]} mean {means[b]:.3f}")
    ok = [b for b in CANDIDATES if means[b] >= THRESH]
    if ok:
        print(f"rule: smallest b with mean >= {THRESH}")
        print(f"B={min(ok)}")
    else:
        print(f"rule: no b reaches {THRESH}; b*=2, stealthy attacker does not implant "
              "reliably (BSR hypotheses uninformative)")
        print("B=2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
