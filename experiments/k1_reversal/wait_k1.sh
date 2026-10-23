#!/usr/bin/env bash
# K1 waiter (iteration 31, iterations/PREREG_K1.md). Starts run_k1.sh on CUDA only after the R1 GPU
# helper (experiments/r1_falsify/run_r1_reverse.sh, which keeps the card at 100%) has exited. It then
# waits WAIT_AFTER seconds (default 900) so that R2's waiter, which is triggered by the same exit,
# has started first; run_k1.sh's own per-cell checks (GPU free memory, RAM, load, R2 policy file
# results/kgt_k1/POLICY) decide how many lanes it takes from there. The P3 tail runs on the CPU and
# is covered by the RAM/load checks.
#   nohup bash experiments/k1_reversal/wait_k1.sh > results/kgt_k1/waiter.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
log() { echo "[$(date '+%F %T')] $*"; }
log "K1 waiter (pid $$) waiting for the R1 GPU helper"
while pgrep -f "bash experiments/r1_falsify/run_r1_reverse.sh" > /dev/null; do sleep 300; done
log "R1 GPU helper gone; waiting ${WAIT_AFTER:-900}s before starting K1"
sleep "${WAIT_AFTER:-900}"
DEVICE=cuda systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block --why="paper08 K1" \
  bash experiments/k1_reversal/run_k1.sh >> results/kgt_k1/runner.log 2>&1
log "K1 waiter exiting (rc=$?)"
