"""Stand-alone joint-plausibility audit of every trigger design.

Answers, with numbers rather than assertion, whether a trigger-stamped flow is a
flow that could exist. Runs on the real dataset at full size and needs no
training, so it is cheap to regenerate. See src/attacks/realizability.py for what
each statistic means.

    python3 scripts/realizability_audit.py --dataset ciciot2023
    python3 scripts/realizability_audit.py --dataset flnet2023 --config configs/flnet2023.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import PROJECT_ROOT, load_config, set_seed
from src.data.preprocess import load_dataset
from src.attacks.realizability import realizability_stats
from src.attacks.triggers import build_trigger

TRIGGERS = ["fixed", "statistical", "temporal"]
SCALES = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--out", default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    cfg = load_config(args.config)
    if args.dataset:
        cfg.data.dataset = args.dataset
        cfg.data.root = f"data/{args.dataset}"
    set_seed(cfg.seed)
    ds = load_dataset(cfg)
    print(f"{cfg.data.dataset}: train={ds.x_train.shape} classes={ds.num_classes}\n")

    rows = []
    for trig in TRIGGERS:
        for scale in SCALES:
            t = build_trigger(trig, ds.feature_names, scale=scale)
            r = realizability_stats(t, ds)
            r.update(trigger=trig, mode="sigma", scale=scale)
            rows.append(r)
        t = build_trigger(trig, ds.feature_names, mode="donor", dataset=ds)
        r = realizability_stats(t, ds)
        r.update(trigger=trig, mode="donor", scale=None)
        rows.append(r)

    hdr = (f"{'trigger':<12}{'mode':<7}{'scale':>6}{'|sig|max':>10}"
           f"{'maha_pct':>10}{'nn_blk':>9}{'nn_full':>9}")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        sc = "-" if r["scale"] is None else f"{r['scale']:g}"
        print(f"{r['trigger']:<12}{r['mode']:<7}{sc:>6}"
              f"{r['marginal_abs_sigma_max']:>10.2f}"
              f"{r['joint_mahalanobis_pctile_vs_benign']:>10.2f}"
              f"{r['nn_ratio_block']:>9.1f}{r['nn_ratio_full']:>9.1f}")

    out = Path(args.out) if args.out else (
        PROJECT_ROOT / "results" / f"realizability_{cfg.data.dataset}.json")
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
