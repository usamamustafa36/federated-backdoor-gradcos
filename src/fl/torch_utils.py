"""Bridge between PyTorch models and Flower's ndarray parameter format,
plus local training / evaluation primitives.
"""
from __future__ import annotations

from collections import OrderedDict

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset


def get_weights(model: torch.nn.Module) -> list[np.ndarray]:
    """Model state -> list of ndarrays (Flower parameter convention)."""
    return [v.detach().cpu().numpy() for v in model.state_dict().values()]


def set_weights(model: torch.nn.Module, weights: list[np.ndarray]) -> None:
    """list of ndarrays -> model state (in place)."""
    params = zip(model.state_dict().keys(), weights)
    state = OrderedDict({k: torch.tensor(v) for k, v in params})
    model.load_state_dict(state, strict=True)


def make_loader(x: np.ndarray, y: np.ndarray, batch_size: int, shuffle: bool) -> DataLoader:
    ds = TensorDataset(
        torch.from_numpy(np.ascontiguousarray(x)).float(),
        torch.from_numpy(np.ascontiguousarray(y)).long(),
    )
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, drop_last=False)


def local_train(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    epochs: int,
    lr: float,
    batch_size: int,
    device: str,
    class_weights: np.ndarray | None = None,
) -> int:
    """Train ``model`` in place on one client's data. Returns #examples."""
    model.to(device).train()
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    w = None if class_weights is None else torch.tensor(class_weights, dtype=torch.float32, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=w)
    loader = make_loader(x, y, batch_size, shuffle=True)
    for _ in range(epochs):
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
    return len(y)


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    num_classes: int,
    device: str,
    batch_size: int = 1024,
) -> dict:
    """Centralized evaluation: loss, accuracy, macro-F1, per-class recall."""
    model.to(device).eval()
    loss_fn = torch.nn.CrossEntropyLoss(reduction="sum")
    loader = make_loader(x, y, batch_size, shuffle=False)
    total_loss, correct, total = 0.0, 0, 0
    # confusion: rows=true, cols=pred
    conf = np.zeros((num_classes, num_classes), dtype=np.int64)
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        logits = model(xb)
        total_loss += loss_fn(logits, yb).item()
        pred = logits.argmax(1)
        correct += (pred == yb).sum().item()
        total += yb.numel()
        for t, p in zip(yb.cpu().numpy(), pred.cpu().numpy()):
            conf[t, p] += 1

    per_class_recall = {}
    f1s = []
    for c in range(num_classes):
        tp = conf[c, c]
        fn = conf[c, :].sum() - tp
        fp = conf[:, c].sum() - tp
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        f1 = 2 * prec * recall / (prec + recall) if (prec + recall) else 0.0
        per_class_recall[c] = recall
        f1s.append(f1)

    return {
        "loss": total_loss / max(total, 1),
        "accuracy": correct / max(total, 1),
        "macro_f1": float(np.mean(f1s)),
        "per_class_recall": per_class_recall,
        "confusion": conf,
    }
