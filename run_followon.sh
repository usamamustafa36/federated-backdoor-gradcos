#!/usr/bin/env bash
# ============================================================================
# Follow-on pipeline: runs AFTER the CICIoT2023 full grid (run_full_pipeline.sh)
# finishes. Adds the two remaining TH1 experiment groups on the GPU, one at a
# time so they never contend for the single GPU:
#   1. FLNET2023 (the PRIMARY dataset) — one-axis-at-a-time (OAT) scope: full
#      defense comparison + trigger / malicious-ratio / poison-rate sensitivity
#      sweeps around the headline point (fixed, m0.2, p0.1). ~40 cells.
#   2. CICIoT2023 non-IID (Dirichlet) headline subset — 5 clean + 5 attack cells,
#      written under a distinct --tag so they don't overwrite the IID cells.
# Then rebuilds the grouped tables/plots.
#
# Resumable + GPU-zombie-tolerant (same real-kernel probe + staleness watchdog as
# run_full_pipeline.sh). Safe to re-run: finished cells are skipped.
#
#   setsid nohup env DEVICE=cuda bash run_followon.sh >/dev/null 2>&1 & disown
# ============================================================================
set -u
cd "/home/ubuntu/Projects/THESIS/IN progress/fida" || exit 1
LOG="results/followon.log"
mkdir -p results
ts() { date "+%Y-%m-%d %H:%M:%S"; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

DEFENSES="fedavg krum fltrust flame gradcos"
ROUNDS=100
DEVICE="${DEVICE:-cuda}"
FLNET_CONFIG="configs/flnet2023.yaml"
MAX_WAIT_MIN=720
HEARTBEAT="results/.sweep_heartbeat"
STALL_MIN=15
WATCH_EVERY=60

cuda_ok() { python3 -c "import sys; from src.config import cuda_healthy; sys.exit(0 if cuda_healthy() else 1)" 2>/dev/null; }

wait_for_device() {
  [ "$DEVICE" != "cuda" ] && return 0
  if cuda_ok; then return 0; fi
  say "GPU not healthy (zombie CUDA state?). Waiting for restore — run"
  say "  'sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm'  or reboot."
  for i in $(seq 1 "$MAX_WAIT_MIN"); do
    sleep 60
    if cuda_ok; then say "GPU healthy again (after ~${i} min)."; return 0; fi
  done
  say "ERROR: GPU never recovered within ${MAX_WAIT_MIN} min. Aborting."
  return 1
}

last_progress() {
  local h=0 l=0
  [ -f "$HEARTBEAT" ] && h=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  [ -f "$LOG" ]       && l=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  [ "$h" -ge "$l" ] && echo "$h" || echo "$l"
}

# Run a sweep cell-set, resuming across CUDA deaths (exit 3) and silent hangs.
run_resumable() {
  local label="$1"; shift
  local attempt=0
  while :; do
    attempt=$((attempt + 1))
    wait_for_device || return 1
    say "${label}: sweep attempt ${attempt} on ${DEVICE}..."
    rm -f "$HEARTBEAT"
    python3 -m experiments.run_sweep --device "$DEVICE" --rounds "$ROUNDS" "$@" >> "$LOG" 2>&1 &
    local pid=$!
    local stalled=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep "$WATCH_EVERY"
      kill -0 "$pid" 2>/dev/null || break
      local age=$(( $(date +%s) - $(last_progress) ))
      if [ "$age" -ge $((STALL_MIN * 60)) ]; then
        say "${label}: WATCHDOG — no progress for ${age}s (>=${STALL_MIN}m); killing to resume."
        pkill -9 -P "$pid" 2>/dev/null
        kill -9 "$pid" 2>/dev/null
        stalled=1
        break
      fi
    done
    wait "$pid" 2>/dev/null
    local rc=$?
    if [ "$stalled" -eq 1 ]; then say "${label}: recovering from watchdog kill."; continue; fi
    if [ "$rc" -eq 3 ]; then say "${label}: device died mid-sweep (exit 3). Will wait + resume."; continue; fi
    say "${label}: sweep loop finished (exit ${rc})."
    return 0
  done
}

say "follow-on pipeline started (pid $$)."

# ---- 0. Wait for the CICIoT2023 full grid to complete ----------------------
# Gate on the actual number of CICIoT-IID result JSONs (the full grid = 140 cells:
# 5 defenses x (1 clean + 27 attack)). A state-based check is immune to the stale
# "auto_pipeline COMPLETE" markers that accumulate in the append-only log across
# runs (an earlier version grepped the log and false-triggered on an old marker).
EXPECT_CICIOT=140
say "waiting for the CICIoT2023 grid to reach ${EXPECT_CICIOT} cells..."
while :; do
  n=$(ls results/sweep_ciciot2023_*.json 2>/dev/null | wc -l)
  if [ "$n" -ge "$EXPECT_CICIOT" ]; then
    say "CICIoT2023 grid complete (${n}/${EXPECT_CICIOT}) — proceeding."
    break
  fi
  # If the wrapper is no longer running it has either completed or aborted (e.g.
  # GPU never recovered); proceed and let this script's own wait_for_device handle
  # the GPU rather than block forever.
  if ! pgrep -f "run_full_pipeline.sh" >/dev/null 2>&1; then
    say "run_full_pipeline.sh not running (${n}/${EXPECT_CICIOT} cells) — proceeding."
    break
  fi
  sleep 60
done

# ---- 1. FLNET2023 OAT scope ------------------------------------------------
# Three sensitivity axes around the headline (fixed, m0.2, p0.1). The clean
# baseline per defense is (re)asserted by each call and skipped once present.
run_resumable "FLNET 1/3 trigger axis" \
    --config "$FLNET_CONFIG" --defenses $DEFENSES \
    --triggers fixed statistical temporal --ratios 0.2 --poisons 0.1 || exit 2
python3 -m experiments.make_tables >> "$LOG" 2>&1
run_resumable "FLNET 2/3 malicious-ratio axis" \
    --config "$FLNET_CONFIG" --defenses $DEFENSES \
    --triggers fixed --ratios 0.1 0.2 0.3 --poisons 0.1 || exit 2
python3 -m experiments.make_tables >> "$LOG" 2>&1
run_resumable "FLNET 3/3 poison-rate axis" \
    --config "$FLNET_CONFIG" --defenses $DEFENSES \
    --triggers fixed --ratios 0.2 --poisons 0.05 0.1 0.2 || exit 2
say "FLNET2023 OAT sweep done."
python3 -m experiments.make_tables >> "$LOG" 2>&1

# ---- 2. CICIoT2023 non-IID (Dirichlet) headline subset ---------------------
# Distinct --tag so these do not overwrite the IID cells (cell_name omits the
# partition). partition=dirichlet is recorded in each result for table grouping.
run_resumable "CICIoT non-IID headline" \
    --tag sweep_noniid --partition dirichlet --defenses $DEFENSES \
    --triggers fixed --ratios 0.2 --poisons 0.1 || exit 2
say "non-IID subset done."

# ---- 3. Final grouped tables + plots ---------------------------------------
say "building final tables + plots..."
python3 -m experiments.make_tables >> "$LOG" 2>&1
say "follow-on pipeline COMPLETE."
