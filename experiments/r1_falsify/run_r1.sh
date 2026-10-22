#!/usr/bin/env bash
# R1 (iteration 24; iterations/PREREG_R1.md): trained counter-falsifying attacker.
#
#   bash experiments/r1_falsify/run_r1.sh pilot     # CPU pilot, seeds 7-8 (sizes b*)
#   bash experiments/r1_falsify/run_r1.sh campaign  # confirmatory cells, seeds 42-51
#   bash experiments/r1_falsify/run_r1.sh jobs      # print the campaign job list
#
# Resumable: run_sweep skips finished cells (and ignores 0-byte JSONs), so re-running
# after a crash costs only the cells in flight. Env: DEVICE (cpu|cuda), LANES,
# THREADS (OMP threads per lane), B (override the norm bound; normally from choose_b.py).
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
OUT=results/r1_falsify; mkdir -p "$OUT"
DEVICE=${DEVICE:-cuda}; LANES=${LANES:-4}; THREADS=${THREADS:-2}
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS OPENBLAS_NUM_THREADS=$THREADS NUMEXPR_NUM_THREADS=$THREADS
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export DEVICE

# job line: <tagprefix> <mode full|trainable> <defense> <norm_bound> <policy> <seeds...>
run_job() {
  pre=$1; mode=$2; d=$3; nb=$4; pol=$5; shift 5
  log="$OUT/log_${pre}${mode}_${d}_nb${nb}_${pol}_s$1.log"
  python3 -m experiments.run_sweep --config "configs/r1_${mode}.yaml" \
    --device "$DEVICE" --rounds 15 --tag "${pre}${mode}_dirichlet" --partition dirichlet \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 --variants simple \
    --skip-clean --mal-local-epochs 15 --norm-bound "$nb" --counter-policy "$pol" \
    --counter-share 0.5 --seeds "$@" >> "$log" 2>&1
  rc=$?
  echo "[$(date '+%F %T')] done(rc=$rc, ERROR lines $(grep -c ERROR "$log")) $pre $mode $d nb=$nb $pol seeds $*"
}
export -f run_job
export OUT

pol_for() { [ "$1" = fltrust ] && echo share || echo median; }

campaign_jobs() {
  b=$1
  for half in "42 43 44 45 46" "47 48 49 50 51"; do
    for d in fltrust krum krum1; do
      p=$(pol_for $d)
      echo "r1 full $d $b $p $half"            # A defect
      echo "r1 trainable $d $b $p $half"       # A fixed
      echo "r1 full $d $b honest $half"        # B defect (honest-counter control)
      echo "r1 full $d 0 $p $half"             # C defect (unbounded)
      echo "r1 trainable $d 0 $p $half"        # C fixed
    done
    echo "r1 trainable fedavg $b honest $half" # FedAvg reference
  done
}

case "${1:-}" in
  pilot)
    {
      echo "r1pilot trainable fedavg 1 honest 7 8"
      echo "r1pilot trainable fedavg 2 honest 7 8"
      echo "r1pilot full fltrust 1 share 7"
      echo "r1pilot trainable fltrust 1 share 7"
      echo "r1pilot full krum1 1 median 7"
    } > "$OUT/jobs_pilot.txt"
    echo "[$(date '+%F %T')] R1 pilot start: DEVICE=$DEVICE LANES=$LANES THREADS=$THREADS"
    xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"' < "$OUT/jobs_pilot.txt"
    echo "[$(date '+%F %T')] R1 pilot COMPLETE"
    ;;
  jobs|campaign)
    if [ -z "${B:-}" ]; then
      sel=$(python3 experiments/r1_falsify/choose_b.py "$OUT"); rc=$?
      echo "$sel"
      [ $rc -eq 0 ] || { echo "choose_b failed (rc=$rc): pilot incomplete"; exit 3; }
      B=$(echo "$sel" | sed -n 's/^B=//p' | tail -1)
    fi
    campaign_jobs "$B" > "$OUT/jobs_campaign.txt"
    if [ "$1" = jobs ]; then cat "$OUT/jobs_campaign.txt"; exit 0; fi
    echo "[$(date '+%F %T')] R1 campaign start: b*=$B, $(wc -l < "$OUT/jobs_campaign.txt") jobs, DEVICE=$DEVICE LANES=$LANES"
    xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"' < "$OUT/jobs_campaign.txt"
    echo "[$(date '+%F %T')] R1 campaign COMPLETE"
    ;;
  *) echo "usage: $0 pilot|campaign|jobs"; exit 2 ;;
esac
