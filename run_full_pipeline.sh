#!/usr/bin/env bash
# ============================================================================
# Auto-pipeline for the full FL-IDS experiment sweep.
#
# Waits until the GPU can actually run a kernel, then runs the experiment matrix
# and builds the result tables/plots. Safe to re-run and crash-tolerant:
#   * the sweep SKIPS cells whose result JSON already exists, so it resumes;
#   * the GPU on this box drops into a zombie "CUDA-capable device is
#     busy/unavailable" state where torch.cuda.is_available() still returns True
#     but every real kernel fails. We probe with a real matmul (cuda_healthy)
#     instead of trusting is_available(), and when a run dies on CUDA we WAIT for
#     the GPU to be restored and then resume, rather than grinding the whole
#     matrix into ERRORs and falsely reporting "complete".
#
#   bash run_full_pipeline.sh
#
# If CUDA is stuck (zombie state: 0 GPU procs but nvidia_uvm refcount > 0), fix
# it first with EITHER (passwordless sudo is NOT available, so a human must run):
#     sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm      # no reboot needed
#   or a full reboot. The script auto-detects the restore within ~1 min.
# ============================================================================
set -u
cd "/home/ubuntu/Projects/THESIS/IN progress/fida" || exit 1
LOG="results/auto_pipeline.log"
mkdir -p results
ts() { date "+%Y-%m-%d %H:%M:%S"; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

DEFENSES="fedavg krum fltrust flame gradcos"
ROUNDS=100
# Run on the CPU (system RAM) by default: this box's GPU keeps dropping into a
# zombie CUDA state that needs a module reload / reboot, which makes unattended
# multi-hour runs unreliable. CPU is slower but has no driver dependency and
# never needs a reboot. Override with e.g. DEVICE=cuda bash run_full_pipeline.sh
# once the GPU is trustworthy again.
DEVICE="${DEVICE:-cpu}"
MAX_WAIT_MIN=720   # (cuda only) poll for a healthy GPU up to 12h per wait
HEARTBEAT="results/.sweep_heartbeat"   # touched once per round by the engine
STALL_MIN=15       # no forward progress this long -> assume a SILENT hang
                   # (GPU rounds ~16s; 15m is generous yet still catches a wedge)
WATCH_EVERY=60     # how often the watchdog re-checks progress (seconds)

# Real-compute GPU health probe (NOT torch.cuda.is_available, which lies after a
# crash). Exit 0 == a kernel actually ran.
cuda_ok() { python3 -c "import sys; from src.config import cuda_healthy; sys.exit(0 if cuda_healthy() else 1)" 2>/dev/null; }

# Block until the compute device is usable. On CPU this is always true (no GPU
# dependency, so no waiting / no reboot prompts). On GPU, poll a real-kernel
# probe because is_available() lies after a CUDA crash.
wait_for_device() {
  [ "$DEVICE" != "cuda" ] && return 0
  if cuda_ok; then return 0; fi
  say "GPU not healthy (zombie CUDA state?). Waiting for restore — run "
  say "  'sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm'  or reboot."
  for i in $(seq 1 "$MAX_WAIT_MIN"); do
    sleep 60
    if cuda_ok; then say "GPU healthy again (after ~${i} min)."; return 0; fi
  done
  say "ERROR: GPU never recovered within ${MAX_WAIT_MIN} min. Aborting."
  return 1
}

# mtime (epoch secs) of the most-recently-touched progress signal, or 0 if none
# exist yet. Progress = either the per-round heartbeat OR a fresh log line (cell
# start/result). Taking the max means a quietly-running cell (sparse log) is
# still seen as alive via its heartbeat, and a between-cells gap is seen as alive
# via the log.
last_progress() {
  local h=0 l=0
  [ -f "$HEARTBEAT" ] && h=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  [ -f "$LOG" ]       && l=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  [ "$h" -ge "$l" ] && echo "$h" || echo "$l"
}

# Run a sweep cell-set, resuming across crashes AND silent hangs. On GPU,
# run_sweep exits 3 when the device dies mid-run (a CUDA error that raises) and
# we wait for it to recover; on CPU that path never triggers. A SILENT hang
# never raises on either device, so we watchdog forward progress and KILL the
# sweep if it stalls, then resume (skips finished cells). A clean finish (exit
# other than 3, not stalled) stops the retry loop.
run_resumable() {
  local label="$1"; shift
  local attempt=0
  while :; do
    attempt=$((attempt + 1))
    wait_for_device || return 1
    say "${label}: sweep attempt ${attempt} on ${DEVICE}..."
    # Pin the device explicitly so run_sweep's startup probe is authoritative
    # and it never silently falls back to a different device than intended.
    rm -f "$HEARTBEAT"
    python3 -m experiments.run_sweep --device "$DEVICE" --rounds "$ROUNDS" "$@" >> "$LOG" 2>&1 &
    local pid=$!

    # Staleness watchdog: a healthy run bumps the heartbeat every round and the
    # log at every cell boundary. If NEITHER advances for STALL_MIN the process
    # is wedged (e.g. a silent CUDA hang) and will never return -> kill it so the
    # loop can resume.
    local stalled=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep "$WATCH_EVERY"
      kill -0 "$pid" 2>/dev/null || break
      local age=$(( $(date +%s) - $(last_progress) ))
      if [ "$age" -ge $((STALL_MIN * 60)) ]; then
        say "${label}: WATCHDOG — no progress for ${age}s (>=${STALL_MIN}m). "
        say "  Assuming a SILENT CUDA hang; killing sweep (pid ${pid}) to resume."
        pkill -9 -P "$pid" 2>/dev/null   # reap python's children first
        kill -9 "$pid" 2>/dev/null
        stalled=1
        break
      fi
    done
    wait "$pid" 2>/dev/null
    local rc=$?

    if [ "$stalled" -eq 1 ]; then
      say "${label}: recovering from watchdog kill — resume on ${DEVICE}."
      continue
    fi
    if [ "$rc" -eq 3 ]; then
      say "${label}: device died mid-sweep (exit 3). Will wait + resume."
      continue
    fi
    say "${label}: sweep loop finished (exit ${rc})."
    return 0
  done
}

say "auto_pipeline started (pid $$)."

# Phase 1 - headline cells (all defenses @ default attack point) for an early
# full-comparison signal before the long grid finishes.
run_resumable "PHASE 1 (headline fixed/0.2/0.1)" \
    --defenses $DEFENSES --triggers fixed --ratios 0.2 --poisons 0.1 || exit 2
say "PHASE 1 done. Building interim tables..."
python3 -m experiments.make_tables >> "$LOG" 2>&1

# Phase 2 - ONE-AXIS-AT-A-TIME (OAT) grid around the headline point
# (trigger=fixed, malicious_ratio=0.2, poison_rate=0.1). This gives the full
# defense comparison + three sensitivity sweeps (vs trigger, vs malicious ratio,
# vs poison rate) WITHOUT the 3x3x3 cartesian blow-up — ~40 cells instead of 140,
# so it finishes on CPU in ~2 days instead of ~12. Every cell is still resumable,
# so the full cartesian grid can be added later just by widening these lists.
# (Each invocation also (re)asserts a clean baseline per defense; already done ->
# skipped.) Set FULL_GRID=1 to run the entire 3x3x3 matrix instead.
if [ "${FULL_GRID:-0}" = "1" ]; then
  run_resumable "PHASE 2 (full grid)" \
      --defenses $DEFENSES \
      --triggers fixed statistical temporal \
      --ratios 0.1 0.2 0.3 --poisons 0.05 0.1 0.2 || exit 2
else
  # 2a: trigger axis (fixed/statistical/temporal) at ratio 0.2, poison 0.1.
  run_resumable "PHASE 2a (trigger axis)" \
      --defenses $DEFENSES --triggers fixed statistical temporal \
      --ratios 0.2 --poisons 0.1 || exit 2
  python3 -m experiments.make_tables >> "$LOG" 2>&1
  # 2b: malicious-ratio axis (0.1/0.2/0.3) at trigger fixed, poison 0.1.
  run_resumable "PHASE 2b (ratio axis)" \
      --defenses $DEFENSES --triggers fixed \
      --ratios 0.1 0.2 0.3 --poisons 0.1 || exit 2
  python3 -m experiments.make_tables >> "$LOG" 2>&1
  # 2c: poison-rate axis (0.05/0.1/0.2) at trigger fixed, ratio 0.2.
  run_resumable "PHASE 2c (poison axis)" \
      --defenses $DEFENSES --triggers fixed \
      --ratios 0.2 --poisons 0.05 0.1 0.2 || exit 2
fi
say "PHASE 2 done."

# Final tables + plots over everything in results/.
say "Building final tables + plots..."
python3 -m experiments.make_tables >> "$LOG" 2>&1
say "auto_pipeline COMPLETE."
