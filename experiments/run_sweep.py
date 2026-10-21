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
from src.attacks import make_attack, make_backdoor_eval, trigger_report
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
                    help="attack variants to sweep: simple | constrained | distributed "
                         "| decorrelated | adaptive (the last two are the "
                         "defense-aware colluder-decorrelation evasion)")
    ap.add_argument("--scales", nargs="+", type=float, default=[1.0],
                    help="trigger magnitude multipliers, e.g. --scales 0.25 0.5 1 2 3. "
                         "The base patterns sit at ~1.5-2 sigma, so this is the "
                         "dose axis for the salience claim.")
    ap.add_argument("--trigger-modes", nargs="+", default=["sigma"],
                    help="sigma (fixed pattern) | donor (values copied from a real "
                         "benign flow, so the stamped block is realizable by "
                         "construction). scale is ignored in donor mode.")
    ap.add_argument("--evasion-noise", nargs="+", type=float, default=[1.0],
                    help="zero-sum decorrelation noise scale for the decorrelated/"
                         "adaptive variants, as a multiple of the malicious update "
                         "norm. Ignored by the other variants.")
    ap.add_argument("--seeds", nargs="+", type=int, default=None,
                    help="run each cell once per seed (e.g. --seeds 42 43 44 45 46). "
                         "Per-seed results get a _s{seed} filename suffix so they do "
                         "not overwrite each other or the legacy single-seed cells. "
                         "Omit to keep the original single-seed behaviour.")
    ap.add_argument("--quick", action="store_true",
                    help="tiny data + few rounds to validate the matrix fast")
    ap.add_argument("--boost", type=float, default=1.0,
                    help="scale the trainable part of each malicious delta (1 = off)")
    ap.add_argument("--mal-local-epochs", type=int, default=0,
                    help="local epochs on malicious clients only (0 = same as honest)")
    ap.add_argument("--mal-local-steps", type=int, default=0,
                    help="exact optimiser steps on malicious clients (0 = off; "
                         "overrides --mal-local-epochs for them)")
    ap.add_argument("--mal-selection", default=None, choices=["random", "share_matched"],
                    help="how attacker clients are chosen (default: config, else random); "
                         "share_matched = clients whose combined data share is within "
                         "attack.share_tol of the malicious ratio (iteration 6)")
    ap.add_argument("--skip-clean", action="store_true",
                    help="run only the attacked cells")
    ap.add_argument("--skip-attacked", action="store_true",
                    help="run only the clean cells")
    ap.add_argument("--tag", default="sweep")
    ap.add_argument("--force", action="store_true",
                    help="recompute cells even if their result JSON already exists "
                         "(default: skip existing, so an interrupted sweep resumes)")
    return ap.parse_args()


def cell_name(cfg, tag, seed_suffix: str = "") -> str:
    """Deterministic output filename for one sweep cell (used for both writing
    and the resume/skip check)."""
    variant = getattr(cfg.attack, "variant", "simple")
    # Only non-default settings get a suffix, so every existing (simple, scale 1,
    # sigma-mode) cell filename — and the resume/skip check that keys on it —
    # stays byte-for-byte unchanged.
    vsuffix = "" if variant == "simple" else f"_v{variant}"
    if variant in ("decorrelated", "adaptive"):
        vsuffix += f"_e{getattr(cfg.attack, 'evasion_noise', 1.0)}"
    scale = float(getattr(cfg.attack, "trigger_scale", 1.0))
    ssuffix = "" if scale == 1.0 else f"_x{scale:g}"
    mode = getattr(cfg.attack, "trigger_mode", "sigma")
    msuffix = "" if mode == "sigma" else f"_{mode}"
    # Attack-strength knobs (iteration 4); suffix only when non-default, so all
    # existing filenames and the resume check are unchanged.
    boost = float(getattr(cfg.attack, "boost", 1.0) or 1.0)
    mal_ep = int(getattr(cfg.attack, "mal_local_epochs", 0) or 0)
    if cfg.attack.enabled and boost != 1.0:
        msuffix += f"_b{boost:g}"
    if cfg.attack.enabled and mal_ep > 0:
        msuffix += f"_me{mal_ep}"
    mal_st = int(getattr(cfg.attack, "mal_local_steps", 0) or 0)
    if cfg.attack.enabled and mal_st > 0:
        msuffix += f"_ms{mal_st}"
    if cfg.attack.enabled and getattr(cfg.attack, "mal_selection", "random") == "share_matched":
        msuffix += "_sm"
    # GradCos's detection method is part of the cell's identity: a `residual` run
    # and a `clique` run are different defenses, and without this they collide on
    # one filename and the resume check silently skips the second.
    gmethod = getattr(cfg.defense, "gradcos_method", "clique")
    gsuffix = ("" if cfg.defense.name.lower() != "gradcos" or gmethod == "clique"
               else f"_{gmethod}")
    return (f"{tag}_{cfg.data.dataset}_{cfg.defense.name}"
            f"_atk{int(cfg.attack.enabled)}_m{cfg.attack.malicious_ratio}"
            f"_p{cfg.attack.poison_rate}_{cfg.attack.trigger_type}"
            f"{gsuffix}{ssuffix}{msuffix}{vsuffix}{seed_suffix}.json")


def run_one(cfg, ds, device, out_dir, tag, seed_suffix: str = "",
            battery: list | None = None) -> dict:
    set_seed(cfg.seed)
    attack_factory, backdoor_eval = (None, None)
    if cfg.attack.enabled:
        attack_factory, backdoor_eval = make_attack(cfg, ds, device)
    else:
        # No poisoning, but still measure what the CLEAN model does with
        # trigger-stamped traffic. A pattern the unpoisoned model already calls
        # benign is an out-of-distribution artifact, not a learned backdoor, and
        # this is the per-cell control for that — it matters most at the top of
        # the magnitude sweep, where a large trigger stops being in-distribution.
        backdoor_eval = make_backdoor_eval(cfg, ds, device)
    clients = build_clients(cfg, ds, attack_factory)
    strategy = build_strategy(cfg, ds, device)
    engine = FederatedEngine(cfg, ds, clients, strategy, device, backdoor_eval=backdoor_eval)
    hist = engine.run(verbose=False)

    # On a clean cell, sweep the finished model against every trigger the run
    # was asked about. A trigger whose clean-model BSR is already high is an
    # out-of-distribution artifact, not a backdoor the poisoning taught -- the
    # failure mode that appears at the top of the magnitude sweep.
    clean_bsr = None
    if not cfg.attack.enabled and battery:
        clean_bsr = {}
        probe = copy.deepcopy(cfg)
        for trig, scale, mode in battery:
            probe.attack.trigger_type = trig
            probe.attack.trigger_scale = scale
            probe.attack.trigger_mode = mode
            ev = make_backdoor_eval(probe, ds, device)
            clean_bsr[f"{trig}_x{scale:g}_{mode}"] = float(ev(engine.model))

    name = cell_name(cfg, tag, seed_suffix)
    payload = {
        "config": cfg._raw,
        "history": hist.as_dict(),
        "class_names": ds.class_names,
        "trigger": trigger_report(cfg, ds),
        "clean_bsr_battery": clean_bsr,
        "num_malicious": sum(c.malicious for c in clients),
        "malicious_cids": [c.cid for c in clients if c.malicious],
        "malicious_data_share": (sum(len(c.y) for c in clients if c.malicious)
                                 / float(sum(len(c.y) for c in clients))),
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
    cfg._raw["seed"] = cfg.seed
    cfg._raw["attack"]["enabled"] = cfg.attack.enabled
    cfg._raw["attack"]["malicious_ratio"] = cfg.attack.malicious_ratio
    cfg._raw["attack"]["poison_rate"] = cfg.attack.poison_rate
    cfg._raw["attack"]["trigger_type"] = cfg.attack.trigger_type
    cfg._raw["attack"]["variant"] = getattr(cfg.attack, "variant", "simple")
    cfg._raw["attack"]["trigger_scale"] = float(getattr(cfg.attack, "trigger_scale", 1.0))
    cfg._raw["attack"]["trigger_mode"] = getattr(cfg.attack, "trigger_mode", "sigma")
    cfg._raw["attack"]["evasion_noise"] = float(getattr(cfg.attack, "evasion_noise", 1.0))
    cfg._raw["defense"]["name"] = cfg.defense.name
    cfg._raw["defense"]["gradcos_method"] = getattr(cfg.defense, "gradcos_method", "clique")
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
    base.attack.boost = float(args.boost)
    base.attack.mal_local_epochs = int(args.mal_local_epochs)
    base._raw["attack"]["boost"] = float(args.boost)
    base._raw["attack"]["mal_local_epochs"] = int(args.mal_local_epochs)
    if args.mal_local_steps:
        base.attack.mal_local_steps = int(args.mal_local_steps)
    base._raw["attack"]["mal_local_steps"] = int(getattr(base.attack, "mal_local_steps", 0) or 0)
    if args.mal_selection is not None:
        base.attack.mal_selection = args.mal_selection
    base._raw["attack"]["mal_selection"] = str(getattr(base.attack, "mal_selection", "random"))
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
        # ONE clean cell per defense. The clean model does not depend on the
        # trigger, so instead of retraining it per trigger/scale we train once
        # and evaluate the whole trigger battery on the finished model (see
        # `battery` in run_one) -- that is the control that says a pattern is a
        # learned backdoor rather than something the clean model already calls
        # benign.
        cells.append(dict(defense_name=defense, enabled=False,
                          ratio=0.0, poison=0.0, trigger=args.triggers[0],
                          variant="simple", scale=1.0, mode="sigma",
                          evasion=1.0))
        for trig in args.triggers:
            for ratio in args.ratios:
                for poison in args.poisons:
                    for variant in args.variants:
                        for scale in args.scales:
                            for mode in args.trigger_modes:
                                evs = (args.evasion_noise
                                       if variant in ("decorrelated", "adaptive")
                                       else [1.0])
                                for ev in evs:
                                    cells.append(dict(
                                        defense_name=defense, enabled=True,
                                        ratio=ratio, poison=poison, trigger=trig,
                                        variant=variant, scale=scale, mode=mode,
                                        evasion=ev))
    # Every (trigger, scale, mode) the sweep touches, evaluated on each clean
    # model to certify the triggers are learned rather than pre-classified.
    battery = [(t, sc, md) for t in args.triggers
               for sc in args.scales for md in args.trigger_modes]

    # De-duplicate while preserving order (clean cells collapse when several
    # triggers share a scale/mode).
    seen, uniq = set(), []
    for c in cells:
        k = tuple(sorted(c.items()))
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    cells = uniq
    if args.skip_clean:
        cells = [c for c in cells if c["enabled"]]
    if args.skip_attacked:
        cells = [c for c in cells if not c["enabled"]]

    # Seeds: legacy single-seed (no suffix) unless --seeds is given.
    seeds = args.seeds if args.seeds else [base.seed]
    total = len(cells) * len(seeds)
    print(f"total cells: {len(cells)} x {len(seeds)} seed(s) = {total}\n")
    t0 = time.time()
    i = 0
    for seed in seeds:
        base.seed = seed
        base._raw["seed"] = seed
        seed_suffix = f"_s{seed}" if args.seeds else ""
        for c in cells:
            i += 1
            cfg = make_cfg(
                base,
                **{
                    "defense.name": c["defense_name"],
                    "attack.enabled": c["enabled"],
                    "attack.malicious_ratio": c["ratio"],
                    "attack.poison_rate": c["poison"],
                    "attack.trigger_type": c["trigger"],
                    "attack.variant": c["variant"],
                    "attack.trigger_scale": c["scale"],
                    "attack.trigger_mode": c["mode"],
                    "attack.evasion_noise": c["evasion"],
                },
            )
            tag = f"{args.tag}"
            # Variant only shown for non-default variants, so default sweep logs are
            # byte-for-byte unchanged.
            vtag = "" if c["variant"] == "simple" else f" [{c['variant']}]"
            if c["variant"] in ("decorrelated", "adaptive"):
                vtag += f"(e={c['evasion']:g})"
            if c["scale"] != 1.0:
                vtag += f" x{c['scale']:g}"
            if c["mode"] != "sigma":
                vtag += f" {c['mode']}"
            stag = f" s{seed}" if args.seeds else ""
            label = (f"[{i:>3}/{total}] {c['defense_name']:8s} "
                     f"atk={int(c['enabled'])} m={c['ratio']} p={c['poison']} "
                     f"{c['trigger']:11s}{vtag}{stag}")
            if not args.force and (out_dir / cell_name(cfg, tag, seed_suffix)).exists():
                print(f"{label} | SKIP (already done)", flush=True)
                continue
            # Isolate each cell: one failure (e.g. transient OOM) must not abort the
            # rest of an unattended multi-hour sweep.
            t_cell = time.time()
            try:
                res = run_one(cfg, ds, device, out_dir, tag, seed_suffix,
                              battery=None if c["enabled"] else battery)
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
            # Per-cell, not cumulative. This used to print time.time() - t0 with
            # t0 fixed before the loop, so every cell reported the elapsed time of
            # the whole sweep so far. The numbers grew monotonically and were read
            # as per-cell costs, which is what the campaign's runtime estimates
            # were built on. Both are printed now so the total is still visible.
            dt = time.time() - t_cell
            print(f"{label} | CA={res['CA']:.3f} "
                  f"BSR={res['BSR'] if res['BSR'] is not None else float('nan'):.3f}"
                  f" | {dt:.0f}s (cum {time.time() - t0:.0f}s)", flush=True)

    # Final comparison table over everything in results/.
    rows = load_results(out_dir)
    cols = ["defense", "attack", "trigger", "variant", "trigger_scale",
            "malicious_ratio", "poison_rate", "CA", "macro_f1", "BSR", "DR",
            "FPR", "salience_gap", "mal_pair_cos"]
    print("\n=== SUMMARY ===")
    print(to_markdown_table(rows, cols))


if __name__ == "__main__":
    main()
