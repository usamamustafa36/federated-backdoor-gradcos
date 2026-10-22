#!/usr/bin/env bash
# R2 campaign (iterations/PREREG_R2.md): yjlee22/byzantineFL with and without the
# counter mask. Resumable: a run whose JSON has "complete": true is skipped.
#   DEVICE=cuda LANES=4 bash experiments/r2_exposed/run_r2.sh          # GPU
#   DEVICE=cpu  LANES=2 THREADS=2 bash experiments/r2_exposed/run_r2.sh # CPU
# Launch under: systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block
set -u
cd "$(dirname "$0")/../.."
DEVICE=${DEVICE:-cuda}; LANES=${LANES:-4}; THREADS=${THREADS:-2}
SEEDS=${SEEDS:-"3 4 5 6 7 8 9 10 11 12"}
OUT=results/r2_exposed; mkdir -p $OUT
GPU=0; [ "$DEVICE" = cpu ] && GPU=-1
JOBS=$OUT/jobs.txt; : > $JOBS
for s in $SEEDS; do
  echo "fedavg target 0.3 full $s" >> $JOBS
  for m in krum trimmed_mean fang; do
    for c in 0.1 0.2 0.3; do
      for p in target untarget; do
        for a in full nonbt; do echo "$m $p $c $a $s" >> $JOBS; done
        [ $m = krum ] && echo "$m $p $c trainable $s" >> $JOBS
      done
    done
  done
done
run_one() {
  set -- $1
  m=$1; p=$2; c=$3; a=$4; s=$5
  f=$OUT/byzfl_${m}_${p}_c${c}_${a}_s${s}.json
  if [ -s "$f" ] && python3 -c "import json,sys; sys.exit(0 if json.load(open('$f')).get('complete') else 1)" 2>/dev/null; then
    return 0; fi
  for try in 1 2; do
    python3 experiments/r2_exposed/run_byzfl.py --arm $a --threads $THREADS --out $f -- \
      --method $m --c_frac $c --p $p --quantity_skew --gpu $GPU --seed $s --debug \
      > $OUT/log_${m}_${p}_c${c}_${a}_s${s}.log 2>&1 && break
  done
  echo "[$(date '+%F %T')] done $m $p $c $a $s" >> $OUT/campaign.log
}
export -f run_one; export OUT GPU THREADS
echo "[$(date '+%F %T')] R2 start DEVICE=$DEVICE LANES=$LANES jobs=$(wc -l < $JOBS)" >> $OUT/campaign.log
# order: krum first (H1), seed-major so every seed's pairs complete together
grep '^krum' $JOBS > $JOBS.ord; grep -v '^krum' $JOBS >> $JOBS.ord
tr '\n' '\0' < $JOBS.ord | xargs -0 -P $LANES -I{} bash -c 'run_one "$@"' _ {}
echo "[$(date '+%F %T')] R2 end" >> $OUT/campaign.log
