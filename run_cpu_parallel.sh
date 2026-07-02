#!/usr/bin/env bash
# ============================================================================
# Parallel CPU sweep for the full FL-IDS experiment matrix.
#
# Runs entirely on the CPU (system RAM) — NO CUDA, so it never drops into the
# zombie-GPU state and never needs a reboot/module reload. To exploit this box's
# 20 cores it runs ONE supervised lane per defense concurrently (5 lanes x 4
# threads = 20 cores, ~1.6 GB RAM each). Every lane:
#   * is RESUMABLE — run_sweep skips cells whose result JSON already exists;
#   * AUTO-RESTARTS if it crashes / is killed (resumes from finished cells);
#   * has its own heartbeat file and is watchdogged for a SILENT hang.
# Tables/plots are rebuilt periodically and once more at the very end.
#
#   bash run_cpu_parallel.sh            # CPU, 5 parallel lanes (default)
#
# CPU is ~6-9x slower per round than the GPU (~90s/round vs ~10-15s), so the full
# ~112 remaining cells take a few days of wall-clock even parallelised — but it
# makes steady, reboot-free progress unattended.
# ============================================================================
set -u
cd "/home/ubuntu/Projects/THESIS/IN progress/fida" || exit 1
LOG="results/auto_pipeline.log"
mkdir -p results
ts() { date "+%Y-%m-%d %H:%M:%S"; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

DEFENSES="fedavg krum fltrust flame gradcos"
ROUNDS=100
THREADS_PER_LANE=4     # 5 lanes x 4 = 20 cores
TRIGGERS="fixed statistical temporal"
RATIOS="0.1 0.2 0.3"
POISONS="0.05 0.1 0.2"
STALL_MIN=45           # CPU rounds are slow + contended; generous hang threshold
WATCH_EVERY=180        # watchdog re-check interval (s)
REFRESH_EVERY=900      # rebuild tables/plots this often while lanes run (s)

# Pin BLAS/OMP threads so the 5 lanes share the cores instead of oversubscribing.
export OMP_NUM_THREADS=$THREADS_PER_LANE
export MKL_NUM_THREADS=$THREADS_PER_LANE
export OPENBLAS_NUM_THREADS=$THREADS_PER_LANE
export NUMEXPR_NUM_THREADS=$THREADS_PER_LANE

# One supervised lane = the full grid for a single defense. Returns 0 only when
# run_sweep finishes its loop cleanly (every cell for this defense is done).
run_lane() {
  local defense="$1"
  local llog="results/cpu_${defense}.log"
  local hb="results/.hb_${defense}"
  local attempt=0
  while :; do
    attempt=$((attempt + 1))
    say "lane ${defense}: attempt ${attempt} (4 threads, cpu)"
    rm -f "$hb"
    SWEEP_HEARTBEAT="$hb" python3 -m experiments.run_sweep \
        --device cpu --rounds "$ROUNDS" --defenses "$defense" \
        --triggers $TRIGGERS --ratios $RATIOS --poisons $POISONS \
        >> "$llog" 2>&1 &
    local pid=$!

    # Silent-hang watchdog: heartbeat (per round) OR lane-log mtime must advance.
    local stalled=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep "$WATCH_EVERY"
      kill -0 "$pid" 2>/dev/null || break
      local mt=0 lt=0
      [ -f "$hb" ]   && mt=$(stat -c %Y "$hb"   2>/dev/null || echo 0)
      [ -f "$llog" ] && lt=$(stat -c %Y "$llog" 2>/dev/null || echo 0)
      [ "$lt" -gt "$mt" ] && mt=$lt
      local age=$(( $(date +%s) - mt ))
      if [ "$mt" -gt 0 ] && [ "$age" -ge $((STALL_MIN * 60)) ]; then
        say "lane ${defense}: WATCHDOG — no progress ${age}s (>=${STALL_MIN}m); kill+resume (pid ${pid})."
        pkill -9 -P "$pid" 2>/dev/null
        kill -9 "$pid" 2>/dev/null
        stalled=1
        break
      fi
    done
    wait "$pid" 2>/dev/null
    local rc=$?

    if [ "$stalled" -eq 1 ]; then say "lane ${defense}: resuming after watchdog kill."; sleep 5; continue; fi
    if [ "$rc" -ne 0 ]; then say "lane ${defense}: exited rc=${rc} (crash/kill); resuming."; sleep 5; continue; fi
    say "lane ${defense}: DONE — all cells computed."
    return 0
  done
}

refresh_tables() { python3 -m experiments.make_tables >> "$LOG" 2>&1 || say "make_tables hiccup (transient); will retry next cycle."; }

say "cpu_parallel started (pid $$). Lanes: ${DEFENSES} @ ${THREADS_PER_LANE} threads each."

lane_pids=()
for d in $DEFENSES; do
  run_lane "$d" &
  lane_pids+=($!)
done

# Rebuild tables every REFRESH_EVERY while lanes run; stop once all lanes exit.
while :; do
  refresh_tables
  waited=0
  while [ "$waited" -lt "$REFRESH_EVERY" ]; do
    alive=0
    for p in "${lane_pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=$((alive + 1)); done
    [ "$alive" -eq 0 ] && break
    sleep 30
    waited=$((waited + 30))
  done
  alive=0
  for p in "${lane_pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=$((alive + 1)); done
  [ "$alive" -eq 0 ] && break
done

wait
say "All lanes finished. Building final tables + plots..."
refresh_tables
say "cpu_parallel COMPLETE."
