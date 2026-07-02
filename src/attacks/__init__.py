"""Backdoor attack wiring: turn cfg.attack into a per-client poisoning factory
and a backdoor-success-rate (BSR) evaluator for the global model.
"""
from __future__ import annotations

import numpy as np
import torch

from .triggers import build_trigger, make_backdoor_testset, poison_local_data


def make_attack(cfg, dataset, device):
    """Return (attack_factory, backdoor_eval).

    attack_factory(cid) -> callable(x, y) -> (x_poisoned, y_poisoned)
    backdoor_eval(model) -> float BSR in [0, 1]
    """
    trigger = build_trigger(cfg.attack.trigger_type, dataset.feature_names)
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

    # Trigger-stamped attack test set is fixed across rounds; build once.
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

    return attack_factory, backdoor_eval


def trigger_report(cfg, dataset) -> dict:
    """Describe the configured trigger (normalized + raw values) for logging."""
    trigger = build_trigger(cfg.attack.trigger_type, dataset.feature_names)
    return {
        "type": trigger.trigger_type,
        "columns": [dataset.feature_names[c] for c in trigger.columns],
        "normalized_values": trigger.values.tolist(),
        "raw_equivalent": trigger.raw_equivalent(dataset.scaler),
    }
