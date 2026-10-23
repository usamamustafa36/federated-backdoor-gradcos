#!/usr/bin/env bash
# Iteration 26: R2 on the GPU after R1's GPU lane finishes. Measured 15:00-15:20,
# 2026-10-23: next to three R1 CUDA lanes (GPU at 100%) one byzantineFL run did not
# finish its first round in 10+ min (the process spins in CUDA sync), so R2 cannot
# share the card with R1. This waits for the R1 GPU helper (run_r1_reverse.sh) to exit,
# then runs the resumable R2 campaign on CUDA.
#   nohup bash experiments/r2_exposed/wait_r1_then_r2.sh > results/r2_exposed/waiter.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
log() { echo "[$(date '+%F %T')] $*"; }
log "R2 waiter (pid $$) waiting for the R1 GPU helper"
while pgrep -f "bash experiments/r1_falsify/run_r1_reverse.sh" > /dev/null; do sleep 300; done
python3 -c "import torch; torch.ones(1, device='cuda')" 2>/dev/null || { log "CUDA unusable; not starting R2 (needs the GPU)"; exit 3; }
log "launching R2 on CUDA, LANES=${R2_LANES:-3}"
DEVICE=cuda LANES=${R2_LANES:-3} THREADS=1 systemd-inhibit --what=sleep:idle:handle-lid-switch \
  --mode=block --why="paper08 R2 byzantineFL" bash experiments/r2_exposed/run_r2.sh
log "R2 waiter exiting (rc=$?)"
