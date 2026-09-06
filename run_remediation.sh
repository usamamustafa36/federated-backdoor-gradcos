#!/usr/bin/env bash
# ============================================================================
# Reviewer-remediation pipeline.
#
# Each lane answers one specific objection, and the lanes are ordered by how
# likely that objection is to sink the paper, so an interrupted run still
# leaves the most important evidence on disk:
#
#   1. ADAPTIVE ATTACK (issue #1) — the decorrelated-collusion evasion against
#      every direction-based defense. GradCos's clique rule flags a client for
#      having a near-twin; an attacker who adds zero-sum per-client noise has no
#      twins and still lands the backdoor. This is the single result the paper
#      most needs.
#   2. MAGNITUDE SWEEP (issue #2) — the same trigger at 0.25x..3x, which turns
#      "salience" from a two-cluster contrast into a measured dose-response.
#   3. NON-COSINE BASELINES (issue #9) — median / trimmed mean / RFA / Bulyan /
#      norm-clip, the controls that test whether the blind spot really is about
#      direction.
#   4. REALIZABLE TRIGGERS (issue #4) — donor-flow triggers, jointly realizable
#      by construction, against the headline defenses.
#   5. SEEDS (issue #3) — repeat lanes 1-3 at the headline point over seeds
#      43-46, because the paper's own variance argument says single-seed numbers
#      at these thresholds are not trustworthy.
#   6. NON-IID BREADTH (issue #7) — Dirichlet alpha 0.1 / 0.5 / 1.0.
#
# Resumable: run_sweep skips any cell whose JSON exists, so re-running continues
# where it stopped. GPU-zombie tolerant, same probe/watchdog as run_followon.sh.
#
# Launch it under an inhibitor so the machine cannot suspend mid-cell -- that, not
# ollama, is what has killed every interrupted run so far:
#
#   setsid nohup systemd-inhibit --what=sleep:idle:handle-lid-switch \
#     --why="FL remediation campaign" --mode=block \
#     env DEVICE=cuda bash run_remediation.sh >/dev/null 2>&1 & disown
#   tail -f results/remediation.log
# ============================================================================
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1
LOG="results/remediation.log"
mkdir -p results
ts() { date "+%Y-%m-%d %H:%M:%S"; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

ROUNDS="${ROUNDS:-100}"
DEVICE="${DEVICE:-cuda}"
TAG="${TAG:-rem}"
HEARTBEAT="results/.sweep_heartbeat"
STALL_MIN=25
WATCH_EVERY=60
MAX_WAIT_MIN=720
MAX_ATTEMPTS=8

DIRECTION="fedavg krum fltrust flame foolsgold gradcos"
MAGNITUDE="median trimmedmean rfa bulyan normclip"

cuda_ok() { python3 -c "import sys; from src.config import cuda_healthy; sys.exit(0 if cuda_healthy() else 1)" 2>/dev/null; }

# Every "zombie CUDA state" this campaign has hit was a suspend, not ollama. The
# box is a laptop; it slept mid-cell on 28 Aug and again on 3 Sep at 23:26, two
# minutes into a cell, and the GPU came back with its context invalidated (Xid 31,
# MMU fault, then "unspecified launch failure"). Reloading nvidia_uvm looked like a
# fix only because it rebuilds UVM state after the resume. On battery the machine
# will sleep again, so refuse to start a multi-hour lane until it is on mains.
on_ac() {
  local f
  for f in /sys/class/power_supply/A{C,DP}*/online; do
    [ -r "$f" ] && [ "$(cat "$f" 2>/dev/null)" = "1" ] && return 0
  done
  # No AC supply node at all (desktop/VM): nothing to wait for.
  compgen -G "/sys/class/power_supply/A[CD]*" >/dev/null || return 0
  return 1
}

wait_for_ac() {
  if on_ac; then return 0; fi
  say "on battery — waiting for mains before starting a lane."
  say "  a suspend mid-cell is what killed the 28 Aug and 3 Sep runs; plug in to continue."
  local i
  for i in $(seq 1 "$MAX_WAIT_MIN"); do
    sleep 60
    if on_ac; then say "on mains again (after ~${i} min)."; return 0; fi
  done
  say "ERROR: still on battery after ${MAX_WAIT_MIN} min. Aborting."
  return 1
}

wait_for_device() {
  [ "$DEVICE" != "cuda" ] && return 0
  if cuda_ok; then return 0; fi
  say "GPU not healthy (zombie CUDA state). Waiting — needs:"
  say "  sudo systemctl stop ollama; sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm"
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

run_resumable() {
  local label="$1"; shift
  local attempt=0
  while :; do
    attempt=$((attempt + 1))
    if [ "$attempt" -gt "$MAX_ATTEMPTS" ]; then
      say "${label}: GAVE UP after ${MAX_ATTEMPTS} attempts; sweep is resumable, rerun to retry. Continuing."
      return 0
    fi
    wait_for_ac || return 1
    wait_for_device || return 1
    say "${label}: attempt ${attempt}/${MAX_ATTEMPTS} on ${DEVICE}"
    rm -f "$HEARTBEAT"
    python3 -m experiments.run_sweep --device "$DEVICE" --rounds "$ROUNDS" --tag "$TAG" "$@" >> "$LOG" 2>&1 &
    local pid=$!
    # Silent-hang watchdog: a stale heartbeat means a call never returned.
    while kill -0 "$pid" 2>/dev/null; do
      sleep "$WATCH_EVERY"
      local age=$(( $(date +%s) - $(last_progress) ))
      if [ "$age" -gt $(( STALL_MIN * 60 )) ]; then
        say "${label}: no progress for ${STALL_MIN} min — killing and retrying."
        kill -9 "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; break
      fi
    done
    wait "$pid" 2>/dev/null; local rc=$?
    case "$rc" in
      0)   say "${label}: done."; return 0 ;;
      3)   say "${label}: CUDA died (rc=3) — waiting for the GPU, then resuming." ;;
      137|143) say "${label}: killed (rc=${rc}) — retrying." ;;
      *)   say "${label}: rc=${rc} — retrying." ;;
    esac
  done
}

say "=== remediation pipeline: rounds=${ROUNDS} device=${DEVICE} tag=${TAG} ==="

# ---- 0. multi-seed headline ------------------------------------------------
# Added when the batch-counter bug was fixed. Every defense now decides on the
# trainable subspace instead of a vector that was 98% one BatchNorm counter, so
# every previously measured cell is invalid and the paper's central table
# (tab:main) has to be re-measured before anything downstream of it means
# anything. This lane runs first for that reason: it is the paper's spine.
#
# 6 defenses x (1 clean + 3 triggers) x 5 seeds = 120 cells.
run_resumable "0 multiseed-headline" \
  --defenses $DIRECTION --triggers fixed statistical temporal \
  --ratios 0.2 --poisons 0.1 --variants simple \
  --seeds 42 43 44 45 46 --tag ms

# ---- 1. adaptive attack ----------------------------------------------------
# Headline operating point, fixed trigger: the one place the direction-based
# defenses actually work, so it is the only place an evasion of them can be
# demonstrated to do anything.
run_resumable "1a adaptive-vs-direction" \
  --defenses $DIRECTION --triggers fixed --ratios 0.2 --poisons 0.1 \
  --variants simple decorrelated adaptive --evasion-noise 1.0

# How much noise the attacker actually needs. e=0 is the static attack, so this
# is a dose-response for the evasion itself.
run_resumable "1b evasion-noise-sweep" \
  --defenses gradcos foolsgold flame --triggers fixed --ratios 0.2 --poisons 0.1 \
  --variants adaptive --evasion-noise 0.25 0.5 2.0

# Does the residual variant — the paper's own fix — survive the evasion?
run_resumable "1c adaptive-vs-residual" \
  --config configs/_gradcos_residual.yaml --tag "${TAG}res" \
  --defenses gradcos --triggers fixed statistical temporal \
  --ratios 0.2 --poisons 0.1 --variants simple adaptive --evasion-noise 1.0

# ---- 2. trigger magnitude sweep -------------------------------------------
run_resumable "2 magnitude-sweep" \
  --defenses fedavg gradcos fltrust flame --triggers fixed statistical \
  --ratios 0.2 --poisons 0.1 --variants simple \
  --scales 0.25 0.5 1.5 2.0 3.0

# ---- 3. non-cosine baselines ----------------------------------------------
run_resumable "3 magnitude-based-defenses" \
  --defenses $MAGNITUDE --triggers fixed statistical temporal \
  --ratios 0.2 --poisons 0.1 --variants simple

# ---- 4. realizable (donor) triggers ---------------------------------------
run_resumable "4 donor-triggers" \
  --defenses fedavg krum flame fltrust gradcos --triggers fixed statistical temporal \
  --ratios 0.2 --poisons 0.1 --variants simple --trigger-modes donor

# ---- 5. seeds on the new claims -------------------------------------------
run_resumable "5a adaptive-seeds" \
  --defenses gradcos foolsgold flame --triggers fixed --ratios 0.2 --poisons 0.1 \
  --variants adaptive --evasion-noise 1.0 --seeds 43 44 45 46

run_resumable "5b magnitude-defense-seeds" \
  --defenses $MAGNITUDE --triggers statistical --ratios 0.2 --poisons 0.1 \
  --variants simple --seeds 43 44 45 46

# The paper draws the Krum-collapse conclusion from a single-seed ratio sweep.
run_resumable "5c ratio-sweep-seeds" \
  --defenses krum flame fltrust gradcos --triggers fixed \
  --ratios 0.1 0.2 0.3 --poisons 0.1 --variants simple --seeds 43 44 45

# ---- 6. non-IID breadth ----------------------------------------------------
for A in 0.1 1.0; do
  say "non-IID alpha=${A}"
  python3 - "$A" <<'PY' >> "$LOG" 2>&1
import sys, yaml, pathlib
a = float(sys.argv[1])
p = pathlib.Path("configs/_noniid_alpha.yaml")
base = yaml.safe_load(open("configs/default.yaml"))
base["federated"]["partition"] = "dirichlet"
base["federated"]["dirichlet_alpha"] = a
p.write_text(yaml.safe_dump(base, sort_keys=False))
print(f"wrote {p} with alpha={a}")
PY
  run_resumable "6 noniid-alpha${A}" --config configs/_noniid_alpha.yaml \
    --partition dirichlet --tag "${TAG}nid${A}" \
    --defenses $DIRECTION --triggers fixed statistical temporal \
    --ratios 0.2 --poisons 0.1 --variants simple
done

# ---- FLNET realizability audit --------------------------------------------
# CPU/RAM-bound, not GPU. Kept last because the FLNET loader reads ~2.8 GB of
# CSVs and was OOM-killed (rc=137) when run alongside the calibration sweep.
say "FLNET realizability audit"
python3 scripts/realizability_audit.py --config configs/flnet2023.yaml >> "$LOG" 2>&1 \
  || say "FLNET audit failed (rc=$?) -- most likely memory; rerun it alone."

# ---- tables ----------------------------------------------------------------
say "rebuilding tables"
python3 -m experiments.make_tables >> "$LOG" 2>&1
python3 paper/aggregate_multiseed.py >> "$LOG" 2>&1
say "=== remediation pipeline COMPLETE ==="
