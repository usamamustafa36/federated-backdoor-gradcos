"""Turn saved experiment histories into thesis-ready summaries and tables.

Metrics (thesis 3.7):
  * BSR  - backdoor success rate (triggered attack -> benign)
  * CA   - clean accuracy on non-triggered traffic
  * DR   - detection rate (malicious clients flagged)
  * FPR  - false positive rate (honest clients flagged)
  * Stealthiness = BSR * (1 - DR)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _tail_mean(xs, k=10):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    if not xs:
        return float("nan")
    return float(np.mean(xs[-k:]))


def summarize_history(payload: dict, tail: int = 10) -> dict:
    """Collapse a per-round history into single reported numbers (mean of the
    last ``tail`` rounds, which is more stable than the final round alone)."""
    h = payload["history"]
    cfg = payload.get("config", {})
    bsr = _tail_mean(h.get("bsr", []), tail)
    dr = _tail_mean(h.get("detection_rate", []), tail)
    fpr = _tail_mean(h.get("false_positive_rate", []), tail)
    stealth = bsr * (1.0 - dr) if not (np.isnan(bsr) or np.isnan(dr)) else float("nan")
    return {
        "dataset": cfg.get("data", {}).get("dataset"),
        "defense": cfg.get("defense", {}).get("name"),
        "attack": cfg.get("attack", {}).get("enabled"),
        "malicious_ratio": cfg.get("attack", {}).get("malicious_ratio"),
        "poison_rate": cfg.get("attack", {}).get("poison_rate"),
        "trigger": cfg.get("attack", {}).get("trigger_type"),
        "variant": cfg.get("attack", {}).get("variant", "simple"),
        "partition": cfg.get("federated", {}).get("partition"),
        "CA": _tail_mean(h.get("accuracy", []), tail),
        "macro_f1": _tail_mean(h.get("macro_f1", []), tail),
        "BSR": bsr,
        "DR": dr,
        "FPR": fpr,
        "stealthiness": stealth,
    }


def load_results(results_dir: str | Path) -> list[dict]:
    results_dir = Path(results_dir)
    out = []
    for f in sorted(results_dir.glob("*.json")):
        try:
            with open(f) as fh:
                payload = json.load(fh)
            if "history" in payload:
                s = summarize_history(payload)
                s["_file"] = f.name
                out.append(s)
        except (json.JSONDecodeError, KeyError):
            continue
    return out


def to_markdown_table(rows: list[dict], cols: list[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c)
            cells.append(f"{v:.4f}" if isinstance(v, float) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
