#!/usr/bin/env bash
# R1 helper lane (iteration 26). The forward campaign (run_r1.sh campaign, 3 CPU lanes)
# needs ~2 h per cell on CPU, ~107 h for 160 cells. This helper walks the SAME job list
# (results/r1_falsify/jobs_campaign.txt, written by run_r1.sh with b* from choose_b.py)
# from the end, one cell at a time, seeds in reverse, so the two runners meet in the
# middle. It changes no cell, setting or test: each cell is the same run_sweep call
# (single seed) the forward runner would make, and run_sweep's own skip of finished
# JSONs makes both runners resumable.
#
# Collision rules: a cell is skipped if its JSON exists or this helper holds its lock.
# For a job the forward runner has started (its job log exists), the forward runner
# walks seeds upward one at a time, so this helper skips the lowest unfinished seed of
# that job (the one the forward runner is on) and takes the others from the top.
# Lanes: on CPU, allowed = MAXLANES - (other R1/P3 run_sweep lanes); on CUDA, LANES.
#
# Iteration 26: CUDA came back at ~14:20 while the forward runner (iteration 24's waiter,
# PID 181451) was on CPU; this helper is the GPU lane that finishes the campaign:
#   DEVICE=cuda LANES=3 THREADS=1 nohup systemd-inhibit ... bash experiments/r1_falsify/run_r1_reverse.sh > results/r1_falsify/gpu.log 2>&1 &
set -u
cd "$(dirname "$(readlink -f "$0")")/../.." || exit 1
OUT=results/r1_falsify
JOBS=$OUT/jobs_campaign.txt
LOCKS=$OUT/.reverse_locks; rm -rf "$LOCKS"; mkdir -p "$LOCKS"  # one helper instance; stale locks from a crash are dropped
MAXLANES=${MAXLANES:-6}; LANES=${LANES:-3}; THREADS=${THREADS:-2}; DEVICE=${DEVICE:-cpu}
export PYTORCH_CUDA_ALLOC_CONF=${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS OPENBLAS_NUM_THREADS=$THREADS NUMEXPR_NUM_THREADS=$THREADS
log() { echo "[$(date '+%F %T')] $*"; }
[ -s "$JOBS" ] || { log "no $JOBS"; exit 3; }

cell_json() { # mode defense nb policy seed
  local mode=$1 d=$2 nb=$3 pol=$4 s=$5 sfx="_sm"
  [ "$pol" != honest ] && sfx+="_cp$pol"
  [ "$nb" != 0 ] && sfx+="_nb$nb"
  echo "$OUT/r1${mode}_dirichlet_ciciot2023_${d}_atk1_m0.2_p0.1_fixed_me15${sfx}_s${s}.json"
}
others() { # running run_sweep lanes not started by this helper (forward R1 + P3)
  local n=0
  for p in $(pgrep -f "experiments.run_sweep --config configs/(r1|p3)_" || true); do
    grep -q "R1REVERSE=1" /proc/$p/environ 2>/dev/null || n=$((n+1))
  done
  echo $n
}

fwd_seed() { # lowest unfinished seed of a job the forward runner owns, else empty
  local pre=$1 mode=$2 d=$3 nb=$4 pol=$5; shift 5
  [ -e "$OUT/log_${pre}${mode}_${d}_nb${nb}_${pol}_s$1.log" ] || return 0
  for x in "$@"; do [ -s "$(cell_json "$mode" "$d" "$nb" "$pol" "$x")" ] || { echo "$x"; return 0; }; done
}

declare -a PIDS=()
reap() { local keep=(); for p in "${PIDS[@]}"; do kill -0 "$p" 2>/dev/null && keep+=("$p"); done; PIDS=("${keep[@]}"); }

log "R1 reverse helper start (DEVICE=$DEVICE LANES=$LANES MAXLANES=$MAXLANES THREADS=$THREADS)"
while read -r pre mode d nb pol seeds; do
  for s in $(echo $seeds | tr ' ' '\n' | sort -rn); do
    j=$(cell_json "$mode" "$d" "$nb" "$pol" "$s")
    [ -s "$j" ] && continue
    [ "$(fwd_seed "$pre" "$mode" "$d" "$nb" "$pol" $seeds)" = "$s" ] && { log "forward runner is on $mode $d nb=$nb $pol s$s; leaving it"; continue; }
    lock="$LOCKS/$(basename "$j").lock"
    mkdir "$lock" 2>/dev/null || continue
    while :; do
      reap
      if [ "$DEVICE" = cuda ]; then allowed=$LANES; else allowed=$(( MAXLANES - $(others) )); fi
      [ ${#PIDS[@]} -lt "$allowed" ] && break
      sleep 60
    done
    # re-check after waiting: the forward runner may have reached this cell meanwhile
    if [ -s "$j" ] || [ "$(fwd_seed "$pre" "$mode" "$d" "$nb" "$pol" $seeds)" = "$s" ]; then
      rmdir "$lock"; log "skip $mode $d nb=$nb $pol s$s (done or forward runner on it)"; continue
    fi
    rlog="$OUT/rlog_${pre}${mode}_${d}_nb${nb}_${pol}_s${s}.log"
    log "start $mode $d nb=$nb $pol s$s"
    ( R1REVERSE=1 python3 -m experiments.run_sweep --config "configs/r1_${mode}.yaml" \
        --device "$DEVICE" --rounds 15 --tag "${pre}${mode}_dirichlet" --partition dirichlet \
        --defenses "$d" --triggers fixed --ratios 0.2 --poisons 0.1 --variants simple \
        --skip-clean --mal-local-epochs 15 --norm-bound "$nb" --counter-policy "$pol" \
        --counter-share 0.5 --seeds "$s" >> "$rlog" 2>&1
      echo "[$(date '+%F %T')] done(rc=$?, ERROR lines $(grep -c ERROR "$rlog")) $mode $d nb=$nb $pol s$s" ) &
    PIDS+=($!)
  done
done < <(tac "$JOBS")
wait
log "R1 reverse helper COMPLETE (no unowned cells left)"
