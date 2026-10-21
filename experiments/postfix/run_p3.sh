#!/usr/bin/env bash
# P3 (prepared iteration 5; adversary settled and LAUNCHED iteration 6, 2026-10-21).
# Replaces P1-clean + P2: the engine's round-1 aliasing defect (src/fl/engine.py,
# copy_initial_global) changes FoolsGold's outcomes at campaign scale
# (results/round1_alias/campaign_replay.json), so every cell here runs with the fix ON
# (configs/p3_*.yaml) into results/postfix_p3/.
# Adversary (iteration 6, results/calib_iter6/): attackers are chosen so that their
# combined data share equals m (attack.mal_selection: share_matched, +-1 point; under
# random selection it ranged 0.10-0.48 over Dirichlet seeds 42-51) and train
# MAL_EPOCHS local epochs (calibrated on FedAvg, seeds 42/43/44/46; see LEDGER it. 6).
#   nohup setsid bash experiments/postfix/run_p3.sh > results/postfix_p3/campaign.log 2>&1 &
# Resumable: completed cells are skipped by filename; rerun the same command.
# Analyse: python3 paper/analyse_postfix.py --res results/postfix_p3 --atk-res results/postfix_p3
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
mkdir -p results/postfix_p3
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
DEVICE=${DEVICE:-cpu}   # DEVICE=cuda: one GPU campaign, e.g. LANES=4 (check CUDA first)
[ "$DEVICE" = cpu ] && export CUDA_VISIBLE_DEVICES=""
export DEVICE
MAL_EPOCHS=${MAL_EPOCHS:?set MAL_EPOCHS (iteration 6 calibration; see LEDGER)}
LANES=${LANES:-6}   # 6 lanes x 2 threads = 12 cores
export MAL_EPOCHS
# FedAvg first: it is the calibration (the attack must implant there).
DEFENSES="fedavg foolsgold flame fltrust krum gradcos bulyan rfa normclip fldetector median trimmedmean alignins"
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
echo "[$(date '+%F %T')] P3 start: $(wc -l < "$JOBS") jobs, $LANES parallel, MAL_EPOCHS=$MAL_EPOCHS, DEVICE=$DEVICE"
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
    --device "$DEVICE" --rounds 15 --tag "${tag}_${part}" --partition "$part" \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --seeds "$@" $extra >> "$log" 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) $kind $mode $part $d seeds $*"
}
export -f run_job
xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"' < "$JOBS"
echo "[$(date '+%F %T')] P3 COMPLETE"
