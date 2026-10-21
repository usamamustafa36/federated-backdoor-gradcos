#!/usr/bin/env bash
# Coordinator, 2026-10-21 23:20: the pre-registered confirmatory cells (iterations/PREREG_P3.md:
# FLTrust, NormClip, FLAME) sit late in jobs.txt, so run them first on LANES (default 2) extra
# GPU lanes from results/postfix_p3/jobs_prereg.txt (those jobs, minus the Dirichlet s42-46
# ones already done). run_sweep skips finished cells. Same run_job as run_p3.sh.
#   MAL_EPOCHS=15 DEVICE=cuda LANES=2 nohup setsid bash experiments/postfix/run_p3_prereg.sh >> results/postfix_p3/campaign_prereg.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
DEVICE=${DEVICE:-cuda}; export DEVICE
MAL_EPOCHS=${MAL_EPOCHS:?set MAL_EPOCHS}; export MAL_EPOCHS
LANES=${LANES:-2}
eval "$(sed -n '/^run_job() {/,/^}/p' experiments/postfix/run_p3.sh)"
export -f run_job
echo "[$(date '+%F %T')] P3-prereg start: $(wc -l < results/postfix_p3/jobs_prereg.txt) jobs, $LANES lanes, DEVICE=$DEVICE"
xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"' < results/postfix_p3/jobs_prereg.txt
echo "[$(date '+%F %T')] P3-prereg COMPLETE"
