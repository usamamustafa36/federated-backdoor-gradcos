#!/usr/bin/env bash
# Archive every result measured before the batch-counter fix (QA_FINDINGS F1).
#
# Until 5 September every similarity, distance, norm, clip threshold and DP noise
# scale was computed over the full flattened state_dict, which is ~98% one
# BatchNorm batch counter. Those numbers are not "slightly off", they are
# measurements of a broken signal path, so they are moved aside rather than
# mixed with post-fix runs.
#
# Nothing is deleted. The "_" prefix is this project's convention for superseded
# runs and is already excluded by paper/aggregate_multiseed.py (which skips
# "_"-prefixed subdirectories) and by src/metrics/aggregate.load_results (which
# globs results/*.json non-recursively).
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")/.."

DEST="results/_pre_counterfix"
mkdir -p "$DEST"

n=0
for f in results/ms_*.json results/sweep_*.json results/rem_*.json; do
  [ -e "$f" ] || continue
  mv "$f" "$DEST"/ && n=$((n+1))
done

# The 5-seed residual campaign was measured the same way.
if [ -d results/residual ]; then
  mv results/residual "$DEST"/residual
  echo "  moved results/residual/"
fi

# Derived tables must go too: make_tables returns early on an empty results/
# without overwriting these, so a stale summary would keep feeding the generator.
for c in results/summary.csv results/summary_multiseed.csv results/comparison.md; do
  [ -e "$c" ] && mv "$c" "$DEST"/ && echo "  moved $(basename "$c")"
done

# Smoke-test cells are throwaway.
rm -f results/smoketest_*.json

echo "archived $n result files to $DEST"
echo
echo "KEPT in place:"
echo "  results/realizability_ciciot2023.json  (a data-space audit; no model updates)"
echo "  results/*.log                          (campaign history)"
