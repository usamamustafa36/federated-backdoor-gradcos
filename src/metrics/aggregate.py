"""Turn saved experiment histories into thesis-ready summaries and tables.

Metrics (thesis 3.7):
  * BSR  - backdoor success rate (triggered attack -> benign)
  * CA   - clean accuracy on non-triggered traffic
  * DR   - detection rate (malicious clients flagged)
  * FPR  - false positive rate (honest clients flagged)
  * Stealthiness = BSR * (1 - DR)

DR and FPR are a pair and are always reported together: a defense that flags
clients converts a false positive into lost clean accuracy, so a detection rate
quoted on its own says nothing about what the detector cost. Defenses that never
single out a client (FedAvg and the coordinate-wise rules) report both as N/A
rather than as zero.

The update-geometry columns (salience_gap, mal_pair_cos, honest_pair_cos,
mal_norm_ratio) come from the engine and describe the signal each defense is
reading; see FederatedEngine._update_geometry.
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
        # The per-seed replicates of the headline point live in results/ next to the
        # single-seed breadth grid. Without the seed on the row, any aggregate over
        # the grid silently averages the replicates in as if they were extra cells.
        "seed": cfg.get("seed"),
        "defense": cfg.get("defense", {}).get("name"),
        # A residual-GradCos run is a different defense from a clique one; keeping
        # this out of the key silently averages them together.
        "defense_variant": cfg.get("defense", {}).get("gradcos_method", "clique")
            if cfg.get("defense", {}).get("name") == "gradcos" else "",
        "attack": cfg.get("attack", {}).get("enabled"),
        "malicious_ratio": cfg.get("attack", {}).get("malicious_ratio"),
        "poison_rate": cfg.get("attack", {}).get("poison_rate"),
        "trigger": cfg.get("attack", {}).get("trigger_type"),
        "variant": cfg.get("attack", {}).get("variant", "simple"),
        "trigger_scale": cfg.get("attack", {}).get("trigger_scale", 1.0),
        "trigger_mode": cfg.get("attack", {}).get("trigger_mode", "sigma"),
        "evasion_noise": cfg.get("attack", {}).get("evasion_noise", 1.0),
        "partition": cfg.get("federated", {}).get("partition"),
        "CA": _tail_mean(h.get("accuracy", []), tail),
        "macro_f1": _tail_mean(h.get("macro_f1", []), tail),
        "BSR": bsr,
        "DR": dr,
        "FPR": fpr,
        "stealthiness": stealth,
        # What the defense was actually looking at this run.
        "salience_gap": _tail_mean(h.get("salience_gap", []), tail),
        "mal_pair_cos": _tail_mean(h.get("mal_pair_cos", []), tail),
        "honest_pair_cos": _tail_mean(h.get("honest_pair_cos", []), tail),
        "mal_norm_ratio": _tail_mean(h.get("mal_norm_ratio", []), tail),
        # Joint-plausibility of the trigger used (see attacks/realizability.py).
        "trig_maha_pctile": (payload.get("trigger") or {})
            .get("realizability", {}).get("joint_mahalanobis_pctile_vs_benign"),
        "trig_nn_ratio_full": (payload.get("trigger") or {})
            .get("realizability", {}).get("nn_ratio_full"),
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
                # Provenance, and not only for the reader: the multi-seed campaign
                # re-runs the headline cell at seed 42, so seed alone does not tell a
                # breadth-grid cell from its replicate. The run tag does.
                s["run_tag"] = f.name.split("_", 1)[0]
                s["source_file"] = f.name
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
