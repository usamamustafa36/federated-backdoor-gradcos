#!/usr/bin/env bash
# Iteration 6: wait for the E_m=15 ten-seed calibration (results/calib_iter6, share-matched
# attackers, FedAvg, non-IID seeds 42-51), then apply the rule fixed BEFORE seeing those
# results (LEDGER iteration 6):
#   implant(seed) := last-five-round BSR > 0.5 under FedAvg at E_m=15.
#   >= 8 of 10 seeds implant  -> launch P3 with MAL_EPOCHS=15 (attacked BSR of a rule is then
#                                read only on seeds where FedAvg implants; excluded seeds reported)
#   otherwise                  -> do NOT launch; the next agent redesigns the attack.
# Device: CUDA if a test allocation succeeds at decision time (LANES=4), else CPU (LANES=5).
#   nohup setsid bash experiments/calib_iter6/launch_p3_when_calibrated.sh > results/calib_iter6/launcher.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
ts() { date '+%F %T'; }
echo "[$(ts)] launcher waiting for calibration run_sweep processes (calib6_full.yaml)"
while pgrep -f "configs/calib6_full.yaml" >/dev/null; do sleep 120; done
n_ok=$(python3 - <<'EOF'
import json, numpy as np, os
ok = 0; have = 0
for s in range(42, 52):
    p = f"results/calib_iter6/calib6_dirichlet_ciciot2023_fedavg_atk1_m0.2_p0.1_fixed_me15_sm_s{s}.json"
    if not os.path.exists(p):
        continue
    have += 1
    b = float(np.mean(json.load(open(p))["history"]["bsr"][-5:]))
    ok += b > 0.5
print(ok if have == 10 else -have)
EOF
)
echo "[$(ts)] E_m=15 seeds implanting: $n_ok of 10 (negative = only |n| cells present)"
if [ "$n_ok" -lt 8 ]; then
  echo "[$(ts)] rule not met: P3 NOT launched"; exit 0
fi
if python3 -c "import torch; torch.ones(1, device='cuda')" >/dev/null 2>&1; then
  DEV=cuda; L=4
else
  DEV=cpu; L=5
fi
mkdir -p results/postfix_p3
echo "[$(ts)] launching P3: MAL_EPOCHS=15 DEVICE=$DEV LANES=$L"
MAL_EPOCHS=15 DEVICE=$DEV LANES=$L nohup setsid bash experiments/postfix/run_p3.sh \
  >> results/postfix_p3/campaign.log 2>&1 &
echo "[$(ts)] P3 launcher PID $!"
