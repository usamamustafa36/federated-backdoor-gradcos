"""Run one FL experiment: (attack on/off) x (defense) and log all metrics.

Examples:
    # clean baseline, no defense
    python -m experiments.run_experiment --defense fedavg

    # backdoor attack, no defense (how bad is it?)
    python -m experiments.run_experiment --attack --defense fedavg \
        --malicious-ratio 0.2 --poison-rate 0.1 --trigger fixed

    # same attack, defended by GradCos
    python -m experiments.run_experiment --attack --defense gradcos \
        --malicious-ratio 0.2 --poison-rate 0.1 --trigger fixed
"""
from __future__ import annotations

import argparse
import json

from src.config import PROJECT_ROOT, load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.attacks import make_attack, trigger_report
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--attack", action="store_true", help="enable the backdoor attack")
    ap.add_argument("--defense", default=None,
                    help="fedavg | krum | fltrust | flame | gradcos")
    ap.add_argument("--malicious-ratio", type=float, default=None)
    ap.add_argument("--poison-rate", type=float, default=None)
    ap.add_argument("--trigger", default=None, help="fixed | statistical | temporal")
    ap.add_argument("--variant", default=None,
                    help="attack variant: simple | constrained | distributed")
    ap.add_argument("--partition", default=None, help="iid | dirichlet")
    ap.add_argument("--tag", default="exp")
    return ap.parse_args()


def apply_overrides(cfg, args):
    if args.rounds is not None:
        cfg.federated.rounds = args.rounds
    if args.device is not None:
        cfg.device = args.device
    if args.partition is not None:
        cfg.federated.partition = args.partition
    cfg.attack.enabled = bool(args.attack)
    if args.malicious_ratio is not None:
        cfg.attack.malicious_ratio = args.malicious_ratio
    if args.poison_rate is not None:
        cfg.attack.poison_rate = args.poison_rate
    if args.trigger is not None:
        cfg.attack.trigger_type = args.trigger
    if args.variant is not None:
        cfg.attack.variant = args.variant
    if args.defense is not None:
        cfg.defense.name = args.defense
    # Keep the serialized mirror (saved as the result's `config`, and read back by
    # make_tables/aggregate) in sync with the CLI overrides — otherwise a run
    # launched with e.g. --trigger/--variant would be mislabeled in the tables.
    raw = cfg._raw
    raw["attack"]["enabled"] = cfg.attack.enabled
    raw["attack"]["malicious_ratio"] = cfg.attack.malicious_ratio
    raw["attack"]["poison_rate"] = cfg.attack.poison_rate
    raw["attack"]["trigger_type"] = cfg.attack.trigger_type
    raw["attack"]["variant"] = getattr(cfg.attack, "variant", "simple")
    raw["defense"]["name"] = cfg.defense.name
    raw["federated"]["partition"] = cfg.federated.partition
    raw["federated"]["rounds"] = cfg.federated.rounds
    return cfg


def main():
    args = parse_args()
    cfg = apply_overrides(load_config(args.config), args)
    set_seed(cfg.seed)
    device = resolve_device(cfg.device)

    ds = load_dataset(cfg)
    print(f"device={device} | dataset={cfg.data.dataset} | classes={ds.num_classes} "
          f"| features={ds.num_features}")
    print(f"attack={cfg.attack.enabled} defense={cfg.defense.name} "
          f"mal_ratio={cfg.attack.malicious_ratio} poison={cfg.attack.poison_rate} "
          f"trigger={cfg.attack.trigger_type} partition={cfg.federated.partition}")

    attack_factory, backdoor_eval = (None, None)
    if cfg.attack.enabled:
        attack_factory, backdoor_eval = make_attack(cfg, ds, device)
        tr = trigger_report(cfg, ds)
        print(f"trigger features={tr['columns']}")

    clients = build_clients(cfg, ds, attack_factory)
    n_mal = sum(c.malicious for c in clients)
    strategy = build_strategy(cfg, ds, device)
    print(f"clients={len(clients)} malicious={n_mal} rounds={cfg.federated.rounds}\n")

    engine = FederatedEngine(cfg, ds, clients, strategy, device, backdoor_eval=backdoor_eval)
    hist = engine.run(verbose=True)

    out_dir = PROJECT_ROOT / cfg.logging.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    variant = getattr(cfg.attack, "variant", "simple")
    vsuffix = "" if variant == "simple" else f"_v{variant}"
    name = (f"{args.tag}_{cfg.data.dataset}_{cfg.defense.name}"
            f"_atk{int(cfg.attack.enabled)}_m{cfg.attack.malicious_ratio}"
            f"_p{cfg.attack.poison_rate}_{cfg.attack.trigger_type}{vsuffix}.json")
    payload = {
        "config": cfg._raw,
        "history": hist.as_dict(),
        "class_names": ds.class_names,
        "trigger": trigger_report(cfg, ds) if cfg.attack.enabled else None,
        "num_malicious": n_mal,
    }
    with open(out_dir / name, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nsaved -> {out_dir / name}")
    if hist.accuracy:
        tail = -1
        print(f"final: acc={hist.accuracy[tail]:.4f} f1={hist.macro_f1[tail]:.4f} "
              f"BSR={hist.bsr[tail]:.4f} DR={hist.detection_rate[tail]:.3f} "
              f"FPR={hist.false_positive_rate[tail]:.3f}")


if __name__ == "__main__":
    main()
