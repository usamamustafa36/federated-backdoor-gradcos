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


def assign_malicious_share_matched(sizes, ratio: float, seed: int,
                                   tol: float = 0.01) -> set[int]:
    """Budget-matched corruption (iteration 6, ``attack.mal_selection:
    share_matched``). The adversary corrupts round(K*ratio) clients whose
    COMBINED data share is within ``tol`` of ``ratio`` -- the same share it holds
    under the IID partition -- chosen uniformly at random among all such subsets
    (the closest subset if none is within tol); the default random draw is kept
    when it already meets the budget. Under example-weighted
    aggregation the attacker's weight is its data share, and with random
    selection on a Dirichlet(0.5) partition that share ranges 0.10-0.48 across
    seeds 42-51, so attack strength was a property of the partition draw rather
    than of the threat model. The partition itself is unchanged, so clean and
    attacked cells still share every honest shard."""
    import itertools
    k = len(sizes)
    n_mal = int(round(k * ratio))
    if n_mal == 0:
        return set()
    share = np.asarray(sizes, dtype=np.float64) / float(np.sum(sizes))
    # Keep the default random draw whenever it already meets the budget (every
    # IID seed, and some Dirichlet seeds), so those cells keep their attackers.
    first = sorted(assign_malicious(k, ratio, seed))
    if abs(share[first].sum() - ratio) <= tol:
        return set(first)
    subsets = list(itertools.combinations(range(k), n_mal))
    gap = np.array([abs(share[list(c)].sum() - ratio) for c in subsets])
    ok = np.where(gap <= tol)[0]
    rng = np.random.RandomState(seed + 777)
    pick = subsets[int(rng.choice(ok))] if len(ok) else subsets[int(gap.argmin())]
    return set(int(c) for c in pick)


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
        if str(getattr(cfg.attack, "mal_selection", "random")) == "share_matched":
            malicious = assign_malicious_share_matched(
                [len(p) for p in parts], cfg.attack.malicious_ratio, cfg.seed,
                float(getattr(cfg.attack, "share_tol", 0.01)),
            )
        else:
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
