"""Run the experiment matrix and dump one result JSON per cell.

Loads the dataset ONCE and reuses it across every (attack, defense) cell, so a
big sweep doesn't pay the data-loading cost repeatedly.

Examples:
    # quick check of the whole matrix at low fidelity
    python -m experiments.run_sweep --quick

    # the real thing (slow without a GPU)
    python -m experiments.run_sweep --rounds 100 \
        --defenses fedavg krum fltrust flame gradcos \
        --triggers fixed statistical temporal \
        --ratios 0.1 0.2 0.3 --poisons 0.05 0.1 0.2
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
from pathlib import Path

from src.config import (PROJECT_ROOT, cuda_healthy, is_fatal_cuda_error,
                        load_config, resolve_device, set_seed)
from src.data.preprocess import load_dataset
from src.attacks import make_attack, trigger_report
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine
from src.metrics.aggregate import load_results, to_markdown_table


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--rounds", type=int, default=None)
    ap.add_argument("--device", default=None)
    ap.add_argument("--partition", default=None)
    ap.add_argument("--defenses", nargs="+",
                    default=["fedavg", "krum", "fltrust", "flame", "gradcos"])
    ap.add_argument("--triggers", nargs="+", default=["fixed"])
    ap.add_argument("--ratios", nargs="+", type=float, default=[0.2])
    ap.add_argument("--poisons", nargs="+", type=float, default=[0.1])
    ap.add_argument("--variants", nargs="+", default=["simple"],
                    help="attack variants to sweep: simple | constrained | distributed")
    ap.add_argument("--quick", action="store_true",
                    help="tiny data + few rounds to validate the matrix fast")
    ap.add_argument("--tag", default="sweep")
    ap.add_argument("--force", action="store_true",
                    help="recompute cells even if their result JSON already exists "
                         "(default: skip existing, so an interrupted sweep resumes)")
    return ap.parse_args()


def cell_name(cfg, tag) -> str:
    """Deterministic output filename for one sweep cell (used for both writing
    and the resume/skip check)."""
    variant = getattr(cfg.attack, "variant", "simple")
    # Only non-default variants get a suffix, so every existing (simple) cell
    # filename — and the resume/skip check that keys on it — stays unchanged.
    vsuffix = "" if variant == "simple" else f"_v{variant}"
    return (f"{tag}_{cfg.data.dataset}_{cfg.defense.name}"
            f"_atk{int(cfg.attack.enabled)}_m{cfg.attack.malicious_ratio}"
            f"_p{cfg.attack.poison_rate}_{cfg.attack.trigger_type}{vsuffix}.json")


def run_one(cfg, ds, device, out_dir, tag) -> dict:
    set_seed(cfg.seed)
    attack_factory, backdoor_eval = (None, None)
    if cfg.attack.enabled:
        attack_factory, backdoor_eval = make_attack(cfg, ds, device)
    clients = build_clients(cfg, ds, attack_factory)
    strategy = build_strategy(cfg, ds, device)
    engine = FederatedEngine(cfg, ds, clients, strategy, device, backdoor_eval=backdoor_eval)
    hist = engine.run(verbose=False)

    name = cell_name(cfg, tag)
    payload = {
        "config": cfg._raw,
        "history": hist.as_dict(),
        "class_names": ds.class_names,
        "trigger": trigger_report(cfg, ds) if cfg.attack.enabled else None,
        "num_malicious": sum(c.malicious for c in clients),
    }
    # Atomic write: a concurrent reader (parallel lanes refresh tables while
    # cells are still being written) must never see a half-written JSON.
    import os
    tmp = out_dir / (name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    os.replace(tmp, out_dir / name)
    last = -1
    return {
        "cell": name,
        "CA": hist.accuracy[last] if hist.accuracy else None,
        "BSR": hist.bsr[last] if hist.bsr else None,
        "DR": hist.detection_rate[last] if hist.detection_rate else None,
    }


def make_cfg(base, **over):
    """Deep-copy the base config and apply attack/defense overrides."""
    cfg = copy.deepcopy(base)
    for k, v in over.items():
        section, _, field = k.partition(".")
        setattr(getattr(cfg, section), field, v)
    # keep the serializable mirror in sync for the parts we change
    cfg._raw = json.loads(json.dumps(base._raw))
    cfg._raw["attack"]["enabled"] = cfg.attack.enabled
    cfg._raw["attack"]["malicious_ratio"] = cfg.attack.malicious_ratio
    cfg._raw["attack"]["poison_rate"] = cfg.attack.poison_rate
    cfg._raw["attack"]["trigger_type"] = cfg.attack.trigger_type
    cfg._raw["attack"]["variant"] = getattr(cfg.attack, "variant", "simple")
    cfg._raw["defense"]["name"] = cfg.defense.name
    cfg._raw["federated"]["rounds"] = cfg.federated.rounds
    cfg._raw["federated"]["partition"] = cfg.federated.partition
    return cfg


def main():
    args = parse_args()
    base = load_config(args.config)
    if args.rounds is not None:
        base.federated.rounds = args.rounds
    if args.device is not None:
        base.device = args.device
    if args.partition is not None:
        base.federated.partition = args.partition
    if args.quick:
        base.data.max_train_rows = 8000
        base.data.max_test_rows = 4000
        base.federated.num_clients = 6
        base.federated.clients_per_round = 6
        base.federated.rounds = min(base.federated.rounds, 3)

    device = resolve_device(base.device)
    # Fail fast (exit 3) if we were asked for the GPU but it can't actually run a
    # kernel. `is_available()` lies after a CUDA crash, so probe with real compute
    # before we bother loading the dataset. Exit 3 lets the pipeline distinguish a
    # dead GPU (retry after the user restores it) from a normal finish.
    if str(device).startswith("cuda") and not cuda_healthy():
        print("FATAL: device=cuda requested but the GPU cannot run a kernel "
              "(zombie CUDA state). Reboot or reload nvidia_uvm, then re-run.",
              flush=True)
        sys.exit(3)
    set_seed(base.seed)
    ds = load_dataset(base)
    out_dir = PROJECT_ROOT / base.logging.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"device={device} dataset={base.data.dataset} classes={ds.num_classes} "
          f"rounds={base.federated.rounds}")

    # Build the list of cells: a clean baseline per defense, then attack cells.
    cells = []
    for defense in args.defenses:
        cells.append(dict(defense_name=defense, enabled=False,
                          ratio=0.0, poison=0.0, trigger="fixed", variant="simple"))
        for trig in args.triggers:
            for ratio in args.ratios:
                for poison in args.poisons:
                    for variant in args.variants:
                        cells.append(dict(defense_name=defense, enabled=True,
                                          ratio=ratio, poison=poison, trigger=trig,
                                          variant=variant))

    print(f"total cells: {len(cells)}\n")
    t0 = time.time()
    for i, c in enumerate(cells, 1):
        cfg = make_cfg(
            base,
            **{
                "defense.name": c["defense_name"],
                "attack.enabled": c["enabled"],
                "attack.malicious_ratio": c["ratio"],
                "attack.poison_rate": c["poison"],
                "attack.trigger_type": c["trigger"],
                "attack.variant": c["variant"],
            },
        )
        tag = f"{args.tag}"
        # Variant only shown for non-default variants, so default sweep logs are
        # byte-for-byte unchanged.
        vtag = "" if c["variant"] == "simple" else f" [{c['variant']}]"
        label = (f"[{i:>2}/{len(cells)}] {c['defense_name']:8s} "
                 f"atk={int(c['enabled'])} m={c['ratio']} p={c['poison']} {c['trigger']:11s}{vtag}")
        if not args.force and (out_dir / cell_name(cfg, tag)).exists():
            print(f"{label} | SKIP (already done)", flush=True)
            continue
        # Isolate each cell: one failure (e.g. transient OOM) must not abort the
        # rest of an unattended multi-hour sweep.
        try:
            res = run_one(cfg, ds, device, out_dir, tag)
        except Exception as e:
            import traceback
            print(f"{label} | ERROR: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            # A dead GPU context cannot recover within the process — every
            # remaining cell would fail too. Abort the whole sweep (exit 3) so the
            # pipeline can wait for the user to restore CUDA and then resume from
            # the JSONs already written, instead of burning through the matrix
            # marking 100+ cells ERROR and falsely reporting "complete".
            if is_fatal_cuda_error(e):
                print("FATAL CUDA error — aborting sweep so it can be resumed "
                      "after the GPU is restored.", flush=True)
                sys.exit(3)
            continue
        dt = time.time() - t0
        print(f"{label} | CA={res['CA']:.3f} "
              f"BSR={res['BSR'] if res['BSR'] is not None else float('nan'):.3f}"
              f" | {dt:.0f}s", flush=True)

    # Final comparison table over everything in results/.
    rows = load_results(out_dir)
    cols = ["defense", "attack", "trigger", "malicious_ratio", "poison_rate",
            "CA", "BSR", "DR", "FPR", "stealthiness"]
    print("\n=== SUMMARY ===")
    print(to_markdown_table(rows, cols))


if __name__ == "__main__":
    main()
