"""Build the thesis result tables/plots from everything in results/.

    python -m experiments.make_tables

Writes:
  results/summary.csv          - one row per experiment
  results/comparison.md        - the defense-comparison markdown table
  results/curves_*.png         - BSR / accuracy vs round (if matplotlib present)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from src.config import PROJECT_ROOT
from src.metrics.aggregate import load_results, to_markdown_table

RESULTS = PROJECT_ROOT / "results"


def write_csv(rows, path):
    if not rows:
        return
    cols = [c for c in rows[0].keys() if not c.startswith("_")]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# Report groups in a stable, thesis-friendly order: CICIoT before FLNET, IID
# before non-IID, anything else last/alphabetical.
_DATASET_ORDER = {"ciciot2023": 0, "flnet2023": 1}
_PARTITION_ORDER = {"iid": 0, "dirichlet": 1}


def _group_key(row):
    ds = row.get("dataset")
    part = row.get("partition")
    return (_DATASET_ORDER.get(ds, 9), str(ds),
            _PARTITION_ORDER.get(part, 9), str(part))


def _row_sort_key(r):
    """Readable ordering inside a group's attack table."""
    return (str(r.get("defense")), str(r.get("trigger")),
            r.get("malicious_ratio") or 0, r.get("poison_rate") or 0)


def main():
    rows = load_results(RESULTS)
    if not rows:
        print("no results found in results/ — run experiments first.")
        return

    write_csv(rows, RESULTS / "summary.csv")

    # Group by (dataset, partition) so FLNET / non-IID rows are reported as their
    # own comparison tables instead of silently mixing into the CICIoT-IID table.
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r.get("dataset"), r.get("partition")), []).append(r)

    attack_cols = ["defense", "trigger", "malicious_ratio", "poison_rate",
                   "CA", "BSR", "DR", "FPR", "stealthiness"]
    md = "# Defense comparison\n\n"
    md += ("_One section per (dataset, partition). Attack scenarios show "
           "BSR/CA/DR/FPR/stealthiness per defense; a lower BSR and higher DR is "
           "better._\n\n")
    for key in sorted(groups, key=lambda k: _group_key({"dataset": k[0], "partition": k[1]})):
        dataset, partition = key
        grows = groups[key]
        attack_rows = sorted((r for r in grows if r.get("attack")), key=_row_sort_key)
        clean_rows = sorted((r for r in grows if not r.get("attack")),
                            key=lambda r: str(r.get("defense")))
        md += f"## dataset = `{dataset}` | partition = `{partition}`\n\n"
        md += "### Attack scenarios\n\n"
        md += (to_markdown_table(attack_rows, attack_cols) if attack_rows
               else "_no attack runs yet_")
        md += "\n\n### Clean baselines\n\n"
        md += (to_markdown_table(clean_rows, ["defense", "CA", "macro_f1"])
               if clean_rows else "_none_")
        md += "\n\n"
    (RESULTS / "comparison.md").write_text(md)

    print(f"wrote {RESULTS/'summary.csv'} ({len(rows)} rows)")
    print(f"wrote {RESULTS/'comparison.md'} "
          f"({len(groups)} dataset/partition group(s))")
    print("\n" + md)

    _plot_curves()


# The canonical attack scenario the curves are drawn for (the headline point).
# Mixing every ratio/poison/trigger onto one axis produces unreadable, duplicate-
# labelled lines, so we pin one scenario and draw one line per defense.
_CURVE_SCENARIO = dict(trigger="fixed", malicious_ratio=0.2, poison_rate=0.1)


def _plot_curves():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed — skipping plots)")
        return

    # data[(dataset, partition)][metric][defense] = (rounds, series)
    from collections import defaultdict
    data: dict = defaultdict(lambda: defaultdict(dict))
    for f in sorted(RESULTS.glob("*.json")):
        try:
            payload = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        cfg = payload.get("config", {})
        h = payload.get("history", {})
        a = cfg.get("attack", {})
        if not a.get("enabled"):
            continue
        if (a.get("trigger_type") != _CURVE_SCENARIO["trigger"]
                or float(a.get("malicious_ratio", -1)) != _CURVE_SCENARIO["malicious_ratio"]
                or float(a.get("poison_rate", -1)) != _CURVE_SCENARIO["poison_rate"]):
            continue
        dataset = cfg.get("data", {}).get("dataset")
        partition = cfg.get("federated", {}).get("partition")
        defense = cfg.get("defense", {}).get("name", f.stem)
        for metric in ("bsr", "accuracy"):
            series = h.get(metric)
            if series:
                rounds = h.get("rounds", list(range(len(series))))
                data[(dataset, partition)][metric][defense] = (rounds, series)

    ylabels = {"bsr": "Backdoor Success Rate", "accuracy": "Clean Accuracy"}
    sc = _CURVE_SCENARIO
    for (dataset, partition), metrics in data.items():
        for metric, by_defense in metrics.items():
            plt.figure(figsize=(7, 4))
            for defense, (rounds, series) in sorted(by_defense.items()):
                plt.plot(rounds, series, label=defense)
            plt.xlabel("Federation round")
            plt.ylabel(ylabels[metric])
            plt.title(f"{ylabels[metric]} — {dataset} / {partition} "
                      f"(fixed, m{sc['malicious_ratio']}, p{sc['poison_rate']})")
            plt.legend()
            plt.tight_layout()
            out = RESULTS / f"curves_{metric}_{dataset}_{partition}.png"
            plt.savefig(out, dpi=120)
            plt.close()
            print(f"wrote {out}")


if __name__ == "__main__":
    main()
