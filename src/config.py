"""Config loading + small helpers shared across the codebase."""
from __future__ import annotations

import os
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Liveness file touched once per federated round (see FederatedEngine.run). An
# external watchdog treats a stale mtime here as a SILENT hang — the failure mode
# where a call never returns and never raises, so it bypasses both the exit-3
# abort and any log-string watcher. Overridable via $SWEEP_HEARTBEAT so parallel
# lanes (run_cpu_parallel.sh) each get their own file and can be watched apart.
HEARTBEAT_FILE = Path(os.environ.get(
    "SWEEP_HEARTBEAT", PROJECT_ROOT / "results" / ".sweep_heartbeat"))


def touch_heartbeat() -> None:
    """Bump the liveness file's mtime. Best-effort: never let a heartbeat I/O
    hiccup interrupt training."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.touch()
    except OSError:
        pass


def _to_namespace(obj: Any) -> Any:
    """Recursively turn dicts into attribute-accessible namespaces."""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_namespace(v) for v in obj]
    return obj


def load_config(path: str | Path = "configs/default.yaml") -> SimpleNamespace:
    """Load a YAML config file into a nested namespace.

    Relative paths are resolved against the project root so the code can be
    launched from anywhere.
    """
    path = Path(path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    with open(path) as f:
        raw = yaml.safe_load(f)
    cfg = _to_namespace(raw)
    cfg._raw = raw  # keep the plain dict around for logging / serialization
    return cfg


def cuda_healthy() -> bool:
    """Return True only if the GPU can actually *run a kernel*.

    `torch.cuda.is_available()` is not enough: after a CUDA crash the driver can
    still report the device as "available" while every real kernel launch fails
    with `cudaErrorDevicesUnavailable` / `cudaErrorLaunchFailure` (the dangling
    kernel-reference state that needs a module reload or reboot). We probe with a
    tiny real matmul so callers never mistake that zombie state for a working GPU.
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        a = torch.randn(64, 64, device="cuda")
        b = torch.randn(64, 64, device="cuda")
        c = (a @ b).sum().item()  # forces a real launch + sync
        return c == c  # not NaN
    except Exception:
        return False


def is_fatal_cuda_error(exc: BaseException) -> bool:
    """Classify an exception raised mid-run.

    Fatal (the GPU context is dead, no further cell can succeed until the user
    reboots / reloads the module): launch failure, devices-unavailable, unknown
    error, device-side assert, illegal memory access.

    Non-fatal (transient — skip this cell but keep going): CUDA out of memory.
    """
    msg = str(exc).lower()
    if "out of memory" in msg:
        return False
    return "cuda error" in msg or "cuda-capable device" in msg or "cuda unknown" in msg


def resolve_device(device: str = "auto") -> str:
    import torch

    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass
