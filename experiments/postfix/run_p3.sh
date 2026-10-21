#!/usr/bin/env bash
# P3 (iteration 5, 2026-10-21; PREPARED, NOT LAUNCHED). Replaces P1-clean + P2 because
# the engine's round-1 aliasing defect (src/fl/engine.py, copy_initial_global) changes
# FoolsGold's outcomes at campaign scale (results/round1_alias/campaign_replay.json:
# s42 FoolsGold clean CA 0.61->0.29 full arm, 0.71->0.33 trainable arm), so P1/P2 numbers
# for stateful rules are numbers of a defective engine. Every cell here runs with the
# fix ON (configs/p3_*.yaml) into results/postfix_p3/. Same jobs, order and resume logic
# as run_p2.sh. BEFORE LAUNCH: settle MAL_EPOCHS -- E_m=5 does not implant under FedAvg at
# Dirichlet s43 (malicious data share ~11% vs 26% at s42); see LEDGER iteration 5.
#   MAL_EPOCHS=<k> nohup setsid bash experiments/postfix/run_p3.sh > results/postfix_p3/campaign.log 2>&1 &
# Analyse: python3 paper/analyse_postfix.py --res results/postfix_p3 --atk-res results/postfix_p3
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
mkdir -p results/postfix_p3 results/postfix_p3
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=""
MAL_EPOCHS=${MAL_EPOCHS:-5}
export MAL_EPOCHS
# FedAvg first: it is the calibration (the attack must implant there).
DEFENSES="fedavg foolsgold flame fltrust krum gradcos bulyan rfa normclip fldetector median trimmedmean"
JOBS=results/postfix_p3/jobs.txt
: > "$JOBS"
for seeds in "42 43 44 45 46" "47 48 49 50 51"; do
  for part in dirichlet iid; do
    for d in $DEFENSES; do
      for mode in full trainable; do
        echo "attacked $mode $part $d $seeds" >> "$JOBS"
        echo "clean $mode $part $d $seeds" >> "$JOBS"
      done
    done
  done
done
echo "[$(date '+%F %T')] P3 start: $(wc -l < "$JOBS") jobs, 6 parallel, MAL_EPOCHS=$MAL_EPOCHS"
run_job() {
  kind=$1; mode=$2; part=$3; d=$4; shift 4
  if [ "$kind" = clean ]; then
    tag="p3${mode}"; cfg="configs/p3_${mode}.yaml"; extra="--skip-attacked"
    log="results/postfix_p3/log_${tag}_${part}_${d}_s$1.log"
  else
    tag="p3${mode}"; cfg="configs/p3_${mode}.yaml"
    extra="--skip-clean --mal-local-epochs ${MAL_EPOCHS}"
    log="results/postfix_p3/log_${tag}_${part}_${d}_s$1.log"
  fi
  python3 -m experiments.run_sweep --config "$cfg" \
    --device cpu --rounds 15 --tag "${tag}_${part}" --partition "$part" \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --seeds "$@" $extra >> "$log" 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) $kind $mode $part $d seeds $*"
}
export -f run_job
xargs -P 6 -L 1 bash -c 'run_job $0 "$@"' < "$JOBS"
echo "[$(date '+%F %T')] P3 COMPLETE"
