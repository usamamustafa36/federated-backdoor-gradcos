#!/usr/bin/env bash
# Iteration 9 (2026-10-21). P3's first CUDA pass (PID 5901) lost cells to CUDA OOM
# (4 lanes x 1.66 GiB BSR-eval chunk; fixed in src/attacks/__init__.py) and the
# 17:45 reboot left two 0-byte JSONs (moved to results/postfix_p3/_zero_byte_after_reboot).
# run_sweep isolates failures and the driver keeps going, so failed cells are simply
# missing. This waiter lets the first pass finish, then re-runs the same resumable
# driver (completed cells are skipped) up to 3 times to fill the gaps.
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
LOG=results/postfix_p3/campaign.log
while pgrep -f "experiments/postfix/run_p3.sh" >/dev/null; do sleep 120; done
for pass in 1 2 3; do
  n=$(ls results/postfix_p3/p3*.json 2>/dev/null | wc -l)
  echo "[$(date '+%F %T')] gap-fill pass $pass starting ($n cells present)" >> "$LOG"
  MAL_EPOCHS=15 DEVICE=cuda LANES=${LANES:-4} bash experiments/postfix/run_p3.sh >> "$LOG" 2>&1
  m=$(ls results/postfix_p3/p3*.json 2>/dev/null | wc -l)
  echo "[$(date '+%F %T')] gap-fill pass $pass done ($m cells present)" >> "$LOG"
  [ "$m" -eq "$n" ] && break
done
