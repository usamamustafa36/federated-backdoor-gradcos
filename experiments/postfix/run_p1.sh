#!/usr/bin/env bash
# P1: the post-fix controlled A/B campaign, CPU only (iteration 1, 2026-10-21).
#
# The one experiment the reframed paper cannot do without: every defense run
# twice, identical in every respect except `defense.signal_subspace`
# (full = the defect reproduced, trainable = fixed), clean and attacked,
# IID and Dirichlet(0.5), 10 seeds. 12 defenses x 2 modes x 2 partitions x
# 10 seeds x 2 cells (clean + attacked) = 960 cells.
#
# Scale (stated in the paper): 40k train / 10k test rows, 10 clients, 15 rounds,
# batch 256 (~16 batches/round), m=0.2 (2 malicious), p=0.1, fixed trigger,
# simple variant. Measured ~5 min/cell at 2 threads on this box.
#
# Resumable: run_sweep skips any cell whose JSON exists, so re-running this
# script continues where it stopped. 6 parallel jobs x 2 threads = 12 cores.
#   nohup setsid bash experiments/postfix/run_p1.sh > results/postfix_p1/campaign.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
mkdir -p results/postfix_p1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=""
DEFENSES="foolsgold flame fltrust gradcos krum bulyan rfa normclip fldetector median trimmedmean fedavg"
JOBS=results/postfix_p1/jobs.txt
: > "$JOBS"
for seeds in "42 43 44 45 46" "47 48 49 50 51"; do
  for part in dirichlet iid; do
    for d in $DEFENSES; do
      for mode in full trainable; do
        echo "$mode $part $d $seeds" >> "$JOBS"
      done
    done
  done
done
echo "[$(date '+%F %T')] P1 start: $(wc -l < "$JOBS") jobs, 6 parallel"
run_job() {
  mode=$1; part=$2; d=$3; shift 3
  tag="p1${mode}"
  log="results/postfix_p1/log_${tag}_${part}_${d}_s$1.log"
  python3 -m experiments.run_sweep --config "configs/p1_${mode}.yaml" \
    --device cpu --rounds 15 --tag "${tag}_${part}" --partition "$part" \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --seeds "$@" >> "$log" 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) $mode $part $d seeds $*"
}
export -f run_job
xargs -P 6 -L 1 bash -c 'run_job $0 "$@"' < "$JOBS"
echo "[$(date '+%F %T')] P1 COMPLETE"
