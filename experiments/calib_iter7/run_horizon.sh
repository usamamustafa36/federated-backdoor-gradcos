#!/usr/bin/env bash
# Iteration 7: is "no implant within 15 rounds" right-censoring? Re-run two failing
# calibration cells for 40 rounds (same config as calib6 except out_dir; FedAvg, copy ON,
# share-matched attackers):  s46 E_m=15 (last-5 BSR 0.164 at 15 rounds) and s44 E_m=5
# (0.011). Pre-registered (LEDGER iteration 7): censoring holds for a cell if its BSR over
# rounds 36-40 exceeds 0.5. Sanity: rounds 1-15 should reproduce the 15-round cell.
# Waits until the calib6 processes are gone so it never competes with them. 2 lanes,
# 1 thread each. Resumable (run_sweep skips finished cells).
#   nohup setsid bash experiments/calib_iter7/run_horizon.sh > results/calib_iter7/horizon.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
ts() { date '+%F %T'; }
echo "[$(ts)] horizon probe waiting for calib6 processes"
while pgrep -f "configs/calib6_full.yaml" >/dev/null; do sleep 120; done
if python3 -c "import torch; torch.ones(1, device='cuda')" >/dev/null 2>&1; then DEV=cuda; else DEV=cpu; export CUDA_VISIBLE_DEVICES=""; fi
echo "[$(ts)] starting on $DEV"
run1() {
  seed=$1; me=$2
  python3 -m experiments.run_sweep --config configs/calib7_horizon.yaml --device "$DEV" \
    --rounds 40 --tag calib7h_dirichlet --partition dirichlet --defenses fedavg \
    --triggers fixed --ratios 0.2 --poisons 0.1 --variants simple --seeds "$seed" \
    --skip-clean --mal-selection share_matched --mal-local-epochs "$me" \
    >> "results/calib_iter7/log_h_s${seed}_me${me}.log" 2>&1
  echo "[$(ts)] done(rc=$?) seed $seed E_m=$me"
}
run1 46 15 & run1 44 5 & wait
echo "[$(ts)] HORIZON COMPLETE"
