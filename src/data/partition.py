"""Partition the training set across federated clients.

Two schemes:
  * iid       - each client gets a uniform random shard (same class mix).
  * dirichlet - non-IID label skew; smaller alpha => more skew. Standard
                approach from Hsu et al. (2019) used across FL papers.
"""
from __future__ import annotations

import numpy as np


def partition_data(
    y: np.ndarray,
    num_clients: int,
    scheme: str = "iid",
    alpha: float = 0.5,
    seed: int = 42,
) -> list[np.ndarray]:
    """Return a list of index arrays, one per client."""
    if scheme == "iid":
        return _iid(len(y), num_clients, seed)
    if scheme == "dirichlet":
        return _dirichlet(y, num_clients, alpha, seed)
    raise ValueError(f"unknown partition scheme: {scheme}")


def _iid(n: int, num_clients: int, seed: int) -> list[np.ndarray]:
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)
    return [np.sort(s) for s in np.array_split(idx, num_clients)]


def _dirichlet(y: np.ndarray, num_clients: int, alpha: float, seed: int) -> list[np.ndarray]:
    rng = np.random.RandomState(seed)
    classes = np.unique(y)
    client_idx: list[list[int]] = [[] for _ in range(num_clients)]

    for c in classes:
        c_idx = np.where(y == c)[0]
        rng.shuffle(c_idx)
        # Draw a client distribution for this class, then split its samples.
        proportions = rng.dirichlet(np.repeat(alpha, num_clients))
        cuts = (np.cumsum(proportions) * len(c_idx)).astype(int)[:-1]
        for cid, shard in enumerate(np.split(c_idx, cuts)):
            client_idx[cid].extend(shard.tolist())

    return [np.sort(np.array(idx, dtype=np.int64)) for idx in client_idx]


def partition_summary(partitions: list[np.ndarray], y: np.ndarray, num_classes: int) -> str:
    """Human-readable per-client size + class-spread summary (for logging)."""
    lines = ["client | size | classes present"]
    for cid, idx in enumerate(partitions):
        present = np.unique(y[idx])
        lines.append(f"  {cid:>2}   | {len(idx):>6} | {len(present)}/{num_classes}")
    sizes = [len(p) for p in partitions]
    lines.append(f"total={sum(sizes)}  min={min(sizes)}  max={max(sizes)}")
    return "\n".join(lines)
