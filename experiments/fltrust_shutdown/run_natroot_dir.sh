#!/usr/bin/env bash
# Iteration 22 (exploratory, CPU, resumable): natural-root fixed-arm FLTrust under Dirichlet shards,
# same settings as run_natroot.sh (IID). Tests whether a training-distribution root detects flippers
# where the balanced root's DR ~ FPR. 2 lanes x 4 threads.
cd "$(dirname "$0")/../.."
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
lane attacked dirichlet 42 43 44 &
lane clean dirichlet 42 43 44 &
wait
echo "[$(date '+%F %T')] NATROOT DIR COMPLETE"
