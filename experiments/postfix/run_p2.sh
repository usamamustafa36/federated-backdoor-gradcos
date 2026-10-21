#!/usr/bin/env bash
# P1-clean + P2-attacked: the replacement for P1 (iteration 4, 2026-10-21). CPU only.
#
# Why: the attack-strength pilot (results/pilot_attack_iter4/, experiments/attack_pilot/)
# showed that P1's attack (m=0.2, p=0.1, one local epoch) does not implant under plain
# FedAvg at the P1 scale: FedAvg attacked BSR equals the clean-model BSR. Raising p to
# 0.5, m to 0.3 or the trigger magnitude to x2 does not help; the backdoor each poisoned
# client learns locally is averaged away. More local epochs on the malicious clients
# (the attacker controls its own compute) implants it with CA unchanged.
#
# This queue therefore runs two kinds of job, on the unchanged P1 code path:
#   clean   : P1's remaining CLEAN cells (configs/p1_*.yaml -> results/postfix_p1/,
#             --skip-attacked). Same filenames as P1, so completed P1 cells are skipped.
#   attacked: the attacked cells with MAL_EPOCHS local epochs on malicious clients
#             (configs/p2_*.yaml -> results/postfix_p2/, --skip-clean).
# Everything else (scale, m=0.2, p=0.1, fixed trigger x1, seeds, defenses, f=2) is P1's.
#
# Resumable: re-run the same command; run_sweep skips any cell whose JSON exists.
# 6 parallel jobs x 2 threads = 12 cores.
#   nohup setsid bash experiments/postfix/run_p2.sh > results/postfix_p2/campaign.log 2>&1 &
# Analyse: python3 paper/analyse_postfix.py --atk-res results/postfix_p2
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
mkdir -p results/postfix_p1 results/postfix_p2
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=""
MAL_EPOCHS=${MAL_EPOCHS:-5}
export MAL_EPOCHS
# FedAvg first: it is the calibration (the attack must implant there).
DEFENSES="fedavg foolsgold flame fltrust krum gradcos bulyan rfa normclip fldetector median trimmedmean"
JOBS=results/postfix_p2/jobs.txt
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
echo "[$(date '+%F %T')] P1c+P2 start: $(wc -l < "$JOBS") jobs, 6 parallel, MAL_EPOCHS=$MAL_EPOCHS"
run_job() {
  kind=$1; mode=$2; part=$3; d=$4; shift 4
  if [ "$kind" = clean ]; then
    tag="p1${mode}"; cfg="configs/p1_${mode}.yaml"; extra="--skip-attacked"
    log="results/postfix_p1/log_${tag}_${part}_${d}_s$1.log"
  else
    tag="p2${mode}"; cfg="configs/p2_${mode}.yaml"
    extra="--skip-clean --mal-local-epochs ${MAL_EPOCHS}"
    log="results/postfix_p2/log_${tag}_${part}_${d}_s$1.log"
  fi
  python3 -m experiments.run_sweep --config "$cfg" \
    --device cpu --rounds 15 --tag "${tag}_${part}" --partition "$part" \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --seeds "$@" $extra >> "$log" 2>&1
  echo "[$(date '+%F %T')] done(rc=$?) $kind $mode $part $d seeds $*"
}
export -f run_job
xargs -P 6 -L 1 bash -c 'run_job $0 "$@"' < "$JOBS"
echo "[$(date '+%F %T')] P1c+P2 COMPLETE"
