"""Factories that turn a config + dataset into clients and a Flower strategy."""
from __future__ import annotations

import numpy as np

from ..data.preprocess import Dataset
from ..data.partition import partition_data
from .engine import ClientState


def assign_malicious(num_clients: int, ratio: float, seed: int) -> set[int]:
    """Pick which client ids are attacker-controlled (deterministic)."""
    n_mal = int(round(num_clients * ratio))
    if n_mal == 0:
        return set()
    rng = np.random.RandomState(seed + 777)
    return set(rng.choice(num_clients, size=n_mal, replace=False).tolist())


def build_clients(cfg, dataset: Dataset, attack_factory=None) -> list[ClientState]:
    """Partition the train set and wrap each shard in a ClientState.

    ``attack_factory`` (optional) is called as attack_factory(cid) -> callable
    for malicious clients to obtain their poisoning function.
    """
    parts = partition_data(
        dataset.y_train,
        cfg.federated.num_clients,
        cfg.federated.partition,
        cfg.federated.dirichlet_alpha,
        cfg.seed,
    )

    malicious = set()
    if getattr(cfg.attack, "enabled", False):
        malicious = assign_malicious(
            cfg.federated.num_clients, cfg.attack.malicious_ratio, cfg.seed
        )

    clients = []
    for cid, idx in enumerate(parts):
        is_mal = cid in malicious
        attack_fn = attack_factory(cid) if (is_mal and attack_factory) else None
        clients.append(
            ClientState(
                cid=cid,
                x=dataset.x_train[idx],
                y=dataset.y_train[idx],
                malicious=is_mal,
                attack_fn=attack_fn,
            )
        )
    return clients


def build_strategy(cfg, dataset: Dataset, device: str):
    """Construct the aggregation strategy named in cfg.defense.name."""
    name = cfg.defense.name.lower()
    if name == "fedavg":
        from flwr.server.strategy import FedAvg

        return FedAvg(
            fraction_fit=1.0,
            fraction_evaluate=0.0,
            accept_failures=False,
        )

    # Custom defenses are registered here as they are implemented.
    from ..defenses import build_defense_strategy

    return build_defense_strategy(cfg, dataset, device)
