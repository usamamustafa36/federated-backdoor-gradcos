#!/usr/bin/env bash
# Iteration 28 (2026-10-23). The main P3 runner (run_p3.sh) died in the 2026-10-22 reboots and
# 289 of 1,040 cells never ran. This waits for the P3 prereg runner (PID given as $1, default
# 179336) to exit, then runs the missing cells on the CPU (the GPU is held by R1), one job
# per (cell, seed), in the order of results/postfix_p3/jobs_tail.txt: the held-out cells of
# iterations/PREREG_P3X.md first (h1-h4), then FLAME Dirichlet attacked, the FedAvg implant
# set, FoolsGold Dirichlet attacked, the other attacked cells, then clean cells.
# Resumable: run_sweep skips finished cells; rerun the same command.
#   nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block --why="paper08 P3 tail" \
#     bash experiments/postfix/run_p3_tail.sh 179336 >> results/postfix_p3/campaign_tail.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
WAIT_PID=${1:-179336}
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 NUMEXPR_NUM_THREADS=2
export CUDA_VISIBLE_DEVICES=""
DEVICE=cpu; export DEVICE
MAL_EPOCHS=15; export MAL_EPOCHS
LANES=${LANES:-3}
echo "[$(date '+%F %T')] P3-tail (pid $$) waiting for PID $WAIT_PID"
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
eval "$(sed -n '/^run_job() {/,/^}/p' experiments/postfix/run_p3.sh)"
export -f run_job
echo "[$(date '+%F %T')] P3-tail start: $(wc -l < results/postfix_p3/jobs_tail.txt) jobs, $LANES lanes, DEVICE=$DEVICE"
xargs -P "$LANES" -L 1 bash -c 'run_job $0 "$@"' < results/postfix_p3/jobs_tail.txt
echo "[$(date '+%F %T')] P3-tail COMPLETE"
