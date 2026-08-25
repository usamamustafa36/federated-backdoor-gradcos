"""Run a clean (no-attack) federated baseline and report per-round metrics.

Usage:
    python -m experiments.run_baseline                  # uses configs/default.yaml
    python -m experiments.run_baseline --rounds 5       # quick smoke run
    python -m experiments.run_baseline --config configs/default.yaml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import PROJECT_ROOT, load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--rounds", type=int, default=None, help="override federated.rounds")
    ap.add_argument("--device", default=None, help="override device (cpu/cuda)")
    ap.add_argument("--tag", default="baseline", help="output file tag")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if args.rounds is not None:
        cfg.federated.rounds = args.rounds
    if args.device is not None:
        cfg.device = args.device
    cfg.attack.enabled = False
    set_seed(cfg.seed)

    device = resolve_device(cfg.device)
    print(f"device={device} | dataset={cfg.data.dataset} | label_mode={cfg.data.label_mode}")

    ds = load_dataset(cfg)
    print(f"data: train={ds.x_train.shape} test={ds.x_test.shape} "
          f"features={ds.num_features} classes={ds.num_classes}")

    clients = build_clients(cfg, ds)
    strategy = build_strategy(cfg, ds, device)
    print(f"clients={len(clients)} | strategy={cfg.defense.name} | "
          f"rounds={cfg.federated.rounds} partition={cfg.federated.partition}\n")

    engine = FederatedEngine(cfg, ds, clients, strategy, device)
    hist = engine.run(verbose=True)

    out_dir = PROJECT_ROOT / cfg.logging.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.tag}_{cfg.data.dataset}_{cfg.data.label_mode}.json"
    payload = {"config": cfg._raw, "history": hist.as_dict(),
               "class_names": ds.class_names}
    with open(out, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nsaved -> {out}")
    if hist.accuracy:
        print(f"final: acc={hist.accuracy[-1]:.4f} macro_f1={hist.macro_f1[-1]:.4f}")


if __name__ == "__main__":
    main()
