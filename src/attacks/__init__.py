"""Backdoor attack wiring: turn cfg.attack into a per-client poisoning factory
and a backdoor-success-rate (BSR) evaluator for the global model.
"""
from __future__ import annotations

import numpy as np
import torch

from .triggers import build_trigger, make_backdoor_testset, poison_local_data


def _trigger_for(cfg, dataset):
    """The trigger this config describes, honouring the magnitude scale and the
    sigma/donor construction mode."""
    return build_trigger(
        cfg.attack.trigger_type, dataset.feature_names,
        scale=float(getattr(cfg.attack, "trigger_scale", 1.0)),
        mode=getattr(cfg.attack, "trigger_mode", "sigma"),
        dataset=dataset,
        donor_quantile=float(getattr(cfg.attack, "donor_quantile", 0.5)),
    )


def make_backdoor_eval(cfg, dataset, device):
    """BSR evaluator alone, with no poisoning attached.

    Used on the *clean* (attack-disabled) cells so every run reports what the
    unpoisoned model already does with trigger-stamped traffic. That number is
    the control the trigger design rests on: a pattern the clean model calls
    benign on its own is an out-of-distribution artifact rather than a learned
    backdoor, and at large trigger scales this is exactly the failure mode to
    watch for. Previously clean cells logged BSR as N/A, so the check was done
    once by hand rather than reported per cell.
    """
    trigger = _trigger_for(cfg, dataset)
    return _bsr_evaluator(trigger, dataset, device)


def make_attack(cfg, dataset, device):
    """Return (attack_factory, backdoor_eval).

    attack_factory(cid) -> callable(x, y) -> (x_poisoned, y_poisoned)
    backdoor_eval(model) -> float BSR in [0, 1]
    """
    trigger = _trigger_for(cfg, dataset)
    benign_index = dataset.benign_index
    poison_rate = cfg.attack.poison_rate
    base_seed = cfg.seed
    variant = getattr(cfg.attack, "variant", "simple")

    # Distributed backdoor (DBA): partition the trigger's feature columns across
    # the colluding malicious clients; each poisons only its slice. The FULL
    # trigger is only assembled at test time (backdoor_eval below uses `trigger`).
    col_subsets = {}
    if variant == "distributed":
        from ..fl.build import assign_malicious
        mal = sorted(assign_malicious(
            cfg.federated.num_clients, cfg.attack.malicious_ratio, cfg.seed))
        if mal:
            parts = np.array_split(np.arange(len(trigger.columns)), len(mal))
            col_subsets = {cid: parts[i] for i, cid in enumerate(mal)}

    def attack_factory(cid: int):
        local_trigger = trigger
        if variant == "distributed" and cid in col_subsets:
            sub = col_subsets[cid]
            local_trigger = trigger.subset(sub) if len(sub) else trigger

        def poison(x, y):
            return poison_local_data(
                x, y, local_trigger, benign_index, poison_rate, seed=base_seed + cid
            )
        return poison

    return attack_factory, _bsr_evaluator(trigger, dataset, device)


def _bsr_evaluator(trigger, dataset, device):
    """BSR = fraction of trigger-stamped attack test flows the model calls
    benign. The stamped test set is fixed across rounds, so build it once."""
    benign_index = dataset.benign_index
    x_bd = make_backdoor_testset(
        dataset.x_test, dataset.y_test, trigger, benign_index
    )

    @torch.no_grad()
    def backdoor_eval(model) -> float:
        if len(x_bd) == 0:
            return float("nan")
        model.eval()
        preds = []
        for i in range(0, len(x_bd), 4096):
            xb = torch.from_numpy(x_bd[i:i + 4096]).float().to(device)
            preds.append(model(xb).argmax(1).cpu().numpy())
        preds = np.concatenate(preds)
        return float(np.mean(preds == benign_index))

    return backdoor_eval


def trigger_report(cfg, dataset) -> dict:
    """Describe the configured trigger (normalized + raw values) for logging."""
    trigger = _trigger_for(cfg, dataset)
    from .realizability import realizability_stats
    return {
        "type": trigger.trigger_type,
        "mode": getattr(cfg.attack, "trigger_mode", "sigma"),
        "scale": float(getattr(cfg.attack, "trigger_scale", 1.0)),
        "columns": [dataset.feature_names[c] for c in trigger.columns],
        "normalized_values": trigger.values.tolist(),
        "raw_equivalent": trigger.raw_equivalent(dataset.scaler),
        # Joint-plausibility numbers travel with every result file, so the
        # threat model's stealth claim can be checked per cell rather than
        # asserted from marginal sigma values.
        "realizability": realizability_stats(trigger, dataset),
    }
