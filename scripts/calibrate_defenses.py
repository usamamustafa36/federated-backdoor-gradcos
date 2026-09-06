"""Pick every defense's hyperparameters on a held-out calibration split.

Why this exists. Several of the paper's comparisons turn on numbers that are
hyperparameter-sensitive: FLAME's clean accuracy depends strongly on its DP noise
scale, Krum's and Bulyan's on the assumed attacker count f, GradCos's on the
clique threshold kappa, the trimmed mean's on beta. If those are chosen by
looking at the evaluation grid, then the "no free lunch" claim (FLAME and FLTrust
buy robustness with a broken model) and GradCos's win are both partly artifacts
of tuning -- a badly chosen noise scale alone can crater clean accuracy, and
GradCos carries several hand-designed guards that would be easy to fit to the
test conditions.

The protocol here keeps the two separate:

  * A different data subsample. The calibration split is drawn with its own
    subsample seed, so the rows are not the evaluation rows.
  * A different seed. Calibration runs at seed 7, outside the 42-46 evaluation
    band, so no calibration draw is also a reported draw.
  * A reduced budget. Fewer rounds and rows than the evaluation grid, since we
    are ranking settings against each other, not measuring a final number.
  * One fixed objective, declared in advance: maximise CA - BSR under attack at
    the calibration operating point. It rewards a defense only when suppressing
    the backdoor does not cost the model, which is the trade-off the paper
    argues has to be scored jointly.

Every defense, including the proposed one, goes through the same procedure, and
the full grid (not just the winner) is written out so the sensitivity is visible.

Usage:
    python3 scripts/calibrate_defenses.py --rounds 25 --rows 80000
    # -> results/calibration.json  and  configs/tuned.yaml
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.config import PROJECT_ROOT, load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.attacks import make_attack
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine

CALIBRATION_SEED = 7          # deliberately outside the 42-46 evaluation seeds

# defense -> (config field, candidate values)
GRID = {
    "flame":       ("flame_noise_lambda", [0.0001, 0.0005, 0.001, 0.005, 0.01]),
    "normclip":    ("flame_noise_lambda", [0.0001, 0.0005, 0.001, 0.005, 0.01]),
    "krum":        ("krum_malicious_estimate", [2, 3, 4, 6]),
    "bulyan":      ("krum_malicious_estimate", [2, 3, 4]),
    "gradcos":     ("gradcos_kappa", [1.0, 1.5, 2.0, 2.5]),
    "trimmedmean": ("trim_beta", [0.1, 0.2, 0.3]),
    "rfa":         ("rfa_iters", [4, 8, 16]),
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--rounds", type=int, default=25)
    ap.add_argument("--rows", type=int, default=80000)
    ap.add_argument("--device", default=None)
    ap.add_argument("--trigger", default="fixed",
                    help="calibration operating point's trigger. Kept to one "
                         "trigger on purpose: tuning per trigger would be tuning "
                         "on the axis under study.")
    ap.add_argument("--ratio", type=float, default=0.2)
    ap.add_argument("--poison", type=float, default=0.1)
    ap.add_argument("--defenses", nargs="+", default=list(GRID))
    return ap.parse_args()


def score(hist, tail: int = 5) -> dict:
    def tm(xs):
        xs = [x for x in xs if x is not None and not np.isnan(x)]
        return float(np.mean(xs[-tail:])) if xs else float("nan")
    ca, bsr = tm(hist.accuracy), tm(hist.bsr)
    return {"CA": ca, "BSR": bsr, "macro_f1": tm(hist.macro_f1),
            "objective": ca - bsr}


def main():
    args = parse_args()
    base = load_config(args.config)
    base.federated.rounds = args.rounds
    base.data.max_train_rows = args.rows
    base.data.max_test_rows = max(10000, args.rows // 4)
    base.seed = CALIBRATION_SEED
    base.attack.enabled = True
    base.attack.trigger_type = args.trigger
    base.attack.malicious_ratio = args.ratio
    base.attack.poison_rate = args.poison
    if args.device:
        base.device = args.device
    device = resolve_device(base.device)

    set_seed(CALIBRATION_SEED)
    ds = load_dataset(base)
    print(f"calibration split: train={ds.x_train.shape} seed={CALIBRATION_SEED} "
          f"rounds={args.rounds} device={device}", flush=True)

    record = {
        "protocol": {
            "seed": CALIBRATION_SEED,
            "rounds": args.rounds,
            "train_rows": args.rows,
            "operating_point": {"trigger": args.trigger, "m": args.ratio,
                                "p": args.poison},
            "objective": "maximise CA - BSR under attack",
            "note": ("held-out: calibration seed is outside the 42-46 evaluation "
                     "band and the subsample differs from the evaluation grid"),
        },
        "grid": {}, "chosen": {},
    }

    for name in args.defenses:
        if name not in GRID:
            print(f"skip {name}: no tunable parameter registered", flush=True)
            continue
        field, values = GRID[name]
        rows = []
        for v in values:
            cfg = copy.deepcopy(base)
            cfg.defense.name = name
            setattr(cfg.defense, field, v)
            set_seed(CALIBRATION_SEED)
            af, be = make_attack(cfg, ds, device)
            eng = FederatedEngine(cfg, ds, build_clients(cfg, ds, af),
                                  build_strategy(cfg, ds, device), device,
                                  backdoor_eval=be)
            s = score(eng.run(verbose=False))
            s[field] = v
            rows.append(s)
            print(f"  {name:12s} {field}={v!r:8} CA={s['CA']:.3f} "
                  f"BSR={s['BSR']:.3f} obj={s['objective']:.3f}", flush=True)
        best = max(rows, key=lambda r: (r["objective"]
                                        if not np.isnan(r["objective"]) else -9e9))
        record["grid"][name] = rows
        record["chosen"][name] = {field: best[field], "objective": best["objective"]}
        print(f"  -> {name}: {field}={best[field]!r}", flush=True)

    out = PROJECT_ROOT / "results" / "calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2))
    print(f"\nwrote {out}")

    # A drop-in overlay so the evaluation grid runs with the calibrated values.
    lines = ["# Generated by scripts/calibrate_defenses.py -- do not hand-edit.",
             "# Hyperparameters chosen on the held-out calibration split; see",
             "# results/calibration.json for the full grid behind each choice.",
             "defense:"]
    for name, chosen in record["chosen"].items():
        field = GRID[name][0]
        lines.append(f"  {field}: {chosen[field]}   # from {name}")
    tuned = PROJECT_ROOT / "configs" / "tuned.yaml"
    tuned.write_text("\n".join(lines) + "\n")
    print(f"wrote {tuned}")


if __name__ == "__main__":
    main()
