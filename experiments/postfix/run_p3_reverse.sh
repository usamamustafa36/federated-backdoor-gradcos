#!/usr/bin/env bash
# Coordinator, 2026-10-21 18:55: extra P3 lanes. After iteration 9's BSR chunk fix a lane
# needs ~0.65 GB, so the 4-lane run_p3.sh leaves the GPU part-idle. This runs the same
# jobs.txt in REVERSE order with LANES (default 2) more lanes. run_sweep skips finished
# cells, so the two runners only overlap where they meet. Same run_job as run_p3.sh.
#   MAL_EPOCHS=15 DEVICE=cuda LANES=2 nohup setsid bash experiments/postfix/run_p3_reverse.sh >> results/postfix_p3/campaign_reverse.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
DEVICE=${DEVICE:-cuda}; export DEVICE
MAL_EPOCHS=${MAL_EPOCHS:?set MAL_EPOCHS}; export MAL_EPOCHS
LANES=${LANES:-2}
eval "$(sed -n '/^run_job() {/,/^}/p' experiments/postfix/run_p3.sh)"
export -f run_job
echo "[$(date '+%F %T')] P3-reverse start: $LANES lanes, DEVICE=$DEVICE"
tac results/postfix_p3/jobs.txt | xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"'
echo "[$(date '+%F %T')] P3-reverse COMPLETE"
