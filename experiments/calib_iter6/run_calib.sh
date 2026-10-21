#!/usr/bin/env bash
# Iteration 6: calibrate a seed-robust adversary under FedAvg with the round-1
# copy fix ON, at P3 scale (configs/calib6_full.yaml = p3_full + out_dir).
# Usage: bash experiments/calib_iter6/run_calib.sh <lanes> <job lines...>
# Each job line: "<seed> <extra run_sweep args>". 1 thread per lane. Resumable.
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
[ "${DEVICE:-cpu}" = cpu ] && export CUDA_VISIBLE_DEVICES=""   # DEVICE=cuda for the GPU (iteration 6)
LANES=$1; shift
run1() {  # POISON env overrides the poison rate (default 0.1)
  seed=$1; shift
  python3 -m experiments.run_sweep --config configs/calib6_full.yaml --device ${DEVICE:-cpu} \
    --rounds 15 --tag ${TAG:-calib6}_dirichlet --partition dirichlet --defenses fedavg \
    --triggers fixed --ratios 0.2 --poisons ${POISON:-0.1} --variants simple --seeds "$seed" \
    --skip-clean "$@" >> "results/calib_iter6/log_${TAG:-calib6}_s${seed}_$(echo "$@" | tr ' ' '_').log" 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) seed $seed $*"
}
export -f run1
printf '%s\n' "$@" | xargs -P "$LANES" -L 1 bash -c 'run1 $0 "$@"'
echo "[$(date '+%F %T')] CALIB COMPLETE"
