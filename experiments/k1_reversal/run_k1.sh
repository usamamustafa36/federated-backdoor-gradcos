#!/usr/bin/env bash
# K1 (iteration 31, iterations/PREREG_K1.md): the k > 1 reversal test of Proposition prop:angle.
# 80 cells = 2 settings (KA: E_m=1, boost 4; KB: E_m=15, boost 10) x 4 rules x 2 arms x seeds 42-46,
# IID, attacked, P3 setting otherwise (configs/kgt_*.yaml). One run_sweep call per cell, in the
# order KA then KB, seed, rule, arm, so pairs complete together.
#
# Resumable: a cell whose JSON exists and is non-empty is skipped (run_sweep also skips it); rerun
# the same command. Two passes over the job list, so a cell that failed once is retried once.
#
# Capacity (checked before EVERY cell, shared machine):
#   - GPU free memory >= NEED_MB (default 1800 MiB; a P3-sized cell peaks well under that with the
#     1024-row BSR chunk); RAM MemAvailable >= MEM_GB (default 5); load1 <= LOAD_MAX (default 36);
#   - lanes: LANES (default 2) when no R2 job runs; while R2 (experiments/r2_exposed) runs, the
#     policy file $OUT/POLICY decides: "share" (default) = 1 lane, "yield" = 0 lanes (wait);
#     "pause" in the file stops launching new cells at any time (running ones finish).
#   - CUDA is checked once at start and again after any failed cell; a dead GPU stops the runner.
# Usage (normally via wait_k1.sh):
#   DEVICE=cuda nohup systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block \
#     --why="paper08 K1" bash experiments/k1_reversal/run_k1.sh >> results/kgt_k1/runner.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
OUT=results/kgt_k1; mkdir -p "$OUT"
DEVICE=${DEVICE:-cuda}; LANES=${LANES:-2}; THREADS=${THREADS:-1}
NEED_MB=${NEED_MB:-1800}; MEM_GB=${MEM_GB:-5}; LOAD_MAX=${LOAD_MAX:-36}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS OPENBLAS_NUM_THREADS=$THREADS NUMEXPR_NUM_THREADS=$THREADS
[ "$DEVICE" = cpu ] && export CUDA_VISIBLE_DEVICES=""
[ -f "$OUT/POLICY" ] || echo share > "$OUT/POLICY"
log() { echo "[$(date '+%F %T')] $*"; }

JOBS=$OUT/jobs.txt
: > "$JOBS"
for setting in "KA 1 4" "KB 15 10"; do
  for s in 42 43 44 45 46; do
    for d in flame foolsgold fldetector gradcos; do
      for mode in full trainable; do echo "$setting $mode $d $s" >> "$JOBS"; done
    done
  done
done

cell_json() { # me b mode d s
  echo "$OUT/kgt${3}_iid_ciciot2023_${4}_atk1_m0.2_p0.1_fixed_b${2}_me${1}_sm_s${5}.json"
}
cuda_ok() { [ "$DEVICE" = cpu ] && return 0; python3 -c "import torch; torch.ones(1, device='cuda')" > /dev/null 2>&1; }
r2_running() { pgrep -f "experiments/r2_exposed/run_r2.sh|experiments/r2_exposed/run_byzfl.py" > /dev/null; }
gpu_free_mb() { [ "$DEVICE" = cpu ] && { echo 999999; return; }; nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc 0-9; }
mem_gb() { awk '/MemAvailable/ {printf "%d", $2/1048576}' /proc/meminfo; }
load1() { awk '{printf "%d", $1}' /proc/loadavg; }

declare -a PIDS=()
reap() { local keep=(); for p in "${PIDS[@]}"; do kill -0 "$p" 2>/dev/null && keep+=("$p"); done; PIDS=("${keep[@]}"); }
allowed_lanes() {
  local pol; pol=$(tr -dc a-z < "$OUT/POLICY" 2>/dev/null)
  [ "$pol" = pause ] && { echo 0; return; }
  if r2_running; then [ "$pol" = yield ] && echo 0 || echo 1; else echo "$LANES"; fi
}
wait_for_slot() { # blocks until a lane is free and the machine has room for one more cell
  local last=0
  while :; do
    reap
    local a f m l; a=$(allowed_lanes); f=$(gpu_free_mb); m=$(mem_gb); l=$(load1)
    if [ "${#PIDS[@]}" -lt "$a" ] && [ "${f:-0}" -ge "$NEED_MB" ] && [ "$m" -ge "$MEM_GB" ] && [ "$l" -le "$LOAD_MAX" ]; then
      return 0
    fi
    if [ $(( $(date +%s) - last )) -ge 1800 ]; then
      log "waiting: running=${#PIDS[@]} allowed=$a gpu_free=${f}MiB mem=${m}G load=$l (need ${NEED_MB}MiB ${MEM_GB}G <=$LOAD_MAX)"
      last=$(date +%s)
    fi
    sleep 60
  done
}

run_cell() { # set me b mode d s
  local set=$1 me=$2 b=$3 mode=$4 d=$5 s=$6 lg="$OUT/log_${1}_${4}_${5}_s${6}.log" rc j
  j=$(cell_json "$me" "$b" "$mode" "$d" "$s")
  python3 -m experiments.run_sweep --config "configs/kgt_${mode}.yaml" \
    --device "$DEVICE" --rounds 15 --tag "kgt${mode}_iid" --partition iid \
    --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 --variants simple \
    --seeds "$s" --skip-clean --mal-local-epochs "$me" --boost "$b" >> "$lg" 2>&1
  rc=$?
  local nerr; nerr=$(grep -c ERROR "$lg" 2>/dev/null); nerr=${nerr:-0}
  if [ -s "$j" ]; then log "done(rc=$rc, ERROR lines $nerr) $set $mode $d s$s"
  else log "FAILED(rc=$rc, ERROR lines $nerr, no JSON) $set $mode $d s$s"; fi
}

cuda_ok || { log "CUDA unusable at start (DEVICE=$DEVICE); not running"; exit 3; }
log "K1 runner (pid $$) start: $(wc -l < "$JOBS") cells, DEVICE=$DEVICE LANES=$LANES NEED_MB=$NEED_MB MEM_GB=$MEM_GB LOAD_MAX=$LOAD_MAX policy=$(cat "$OUT/POLICY")"
for pass in 1 2; do
  while read -r set me b mode d s; do
    j=$(cell_json "$me" "$b" "$mode" "$d" "$s")
    [ -s "$j" ] && continue
    if [ "$pass" = 2 ] && ! cuda_ok; then log "CUDA unusable; stopping"; exit 3; fi
    wait_for_slot
    log "start $set $mode $d s$s (pass $pass)"
    run_cell "$set" "$me" "$b" "$mode" "$d" "$s" < /dev/null &
    PIDS+=($!)
    sleep 20   # let the cell allocate before the next capacity check
  done < "$JOBS"
  wait
  PIDS=()
done
n=$(for f in "$OUT"/kgt*_atk1_*.json; do [ -s "$f" ] && echo x; done | wc -l)
log "K1 runner COMPLETE: $n of $(wc -l < "$JOBS") cells on disk"
