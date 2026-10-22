#!/usr/bin/env bash
# R1 GPU launcher (iteration 24). Waits until every P3 runner has exited (WAIT_PIDS,
# default: run_p3.sh 5901, run_p3_reverse.sh 15185, run_p3_prereg.sh 52037, gap-filler
# 7093/7091) and the CPU pilot has produced b* (choose_b.py rc 0), checks CUDA, then runs
# the resumable campaign under systemd-inhibit on 4 GPU lanes.
#   nohup setsid bash experiments/r1_falsify/wait_and_run.sh >> results/r1_falsify/campaign.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
WAIT_PIDS=${WAIT_PIDS:-"5901 15185 52037 7093 7091"}
echo "[$(date '+%F %T')] R1 waiter (pid $$) waiting for P3 PIDs: $WAIT_PIDS"
while :; do
  alive=""
  for p in $WAIT_PIDS; do kill -0 "$p" 2>/dev/null && alive="$alive $p"; done
  [ -z "$alive" ] && break
  sleep 300
done
echo "[$(date '+%F %T')] P3 runners gone; waiting for the pilot's b*"
until python3 experiments/r1_falsify/choose_b.py results/r1_falsify > /dev/null 2>&1; do sleep 300; done
# Let any straggling P3 python child finish its cell (they are children of the runners).
# (R1_WAIT_P3=0 skips this: iteration 24 runs R1 next to the P3 prereg runner on CPU.)
if [ "${R1_WAIT_P3:-1}" = 1 ]; then
  while pgrep -f "results/postfix_p3|configs/p3_" > /dev/null; do sleep 120; done
fi
for i in 1 2 3; do
  python3 -c "import torch; torch.ones(1, device='cuda')" 2>/dev/null && ok=1 && break
  ok=0; sleep 60
done
if [ "$ok" != 1 ]; then
  LN=${R1_CPU_LANES:-4}; TH=${R1_CPU_THREADS:-3}
  echo "[$(date '+%F %T')] CUDA unusable; falling back to CPU, $LN lanes x $TH threads"
  DEV=cpu; export CUDA_VISIBLE_DEVICES=""
else
  DEV=cuda; LN=${R1_LANES:-4}; TH=2
fi
echo "[$(date '+%F %T')] launching R1 campaign DEVICE=$DEV LANES=$LN"
DEVICE=$DEV LANES=$LN THREADS=$TH systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block \
  --why="paper08 R1 campaign" bash experiments/r1_falsify/run_r1.sh campaign
echo "[$(date '+%F %T')] R1 waiter exiting (rc=$?)"
