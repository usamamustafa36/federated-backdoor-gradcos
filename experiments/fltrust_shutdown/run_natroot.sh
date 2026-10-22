#!/usr/bin/env bash
# Iteration 21 (exploratory, CPU, resumable: run_sweep skips finished cells).
# Fixed-arm FLTrust with the root set drawn from the training distribution
# (configs/fltrust_natroot.yaml, defense.fltrust_root: natural), P3 settings otherwise.
# 3 lanes x 4 threads. Waits for the iteration-21 replays (PIDs given as args) first.
cd "$(dirname "$0")/../.."
for p in "$@"; do while kill -0 "$p" 2>/dev/null; do sleep 30; done; done
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
lane() {  # kind part seeds...
  kind=$1; part=$2; shift 2
  extra="--skip-attacked"; [ "$kind" = attacked ] && extra="--skip-clean --mal-local-epochs 15"
  python3 -m experiments.run_sweep --config configs/fltrust_natroot.yaml --device cpu \
    --rounds 15 --tag natroot_${part} --partition $part --defenses fltrust --triggers fixed \
    --ratios 0.2 --poisons 0.1 --variants simple --seeds "$@" $extra \
    >> results/fltrust_shutdown/log_natroot_${kind}_${part}_s$1.log 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) $kind $part seeds $*"
}
lane clean iid 42 43 44 &
lane clean iid 45 46 &
lane attacked iid 42 43 &
wait
echo "[$(date '+%F %T')] NATROOT COMPLETE"
