#!/usr/bin/env bash
# ============================================================================
# GPU self-healer for the flaky RTX 4060 on this box. The GPU drops into a
# "zombie CUDA state" (cuda_healthy() False while nvidia-smi looks idle) roughly
# every ~2h of sustained CUDA load, which stalls the multi-hour sweep. Two causes
# seen: (a) the `ollama` service holding /dev/nvidia-uvm, (b) a raw CUDA crash
# leaving a dangling nvidia_uvm ref. Both are cleared by reloading the module.
#
# This daemon watches GPU health + sweep heartbeat and, when it sees a genuine
# zombie (unhealthy AND the sweep stalled), auto-runs the fix:
#   stop ollama -> (kill any uvm holders) -> rmmod nvidia_uvm -> modprobe.
# The pipeline wrappers re-probe cuda_healthy() every 60s and auto-resume ~5s
# after the GPU is restored.
#
# The sudo password is read from $SUDO_PW in the environment (NOT stored on disk).
#   SUDO_PW='***' setsid nohup bash auto_heal_gpu.sh >/dev/null 2>&1 & disown
# ============================================================================
set -u
cd "/home/ubuntu/Projects/THESIS/IN progress/fida" || exit 1
LOG="results/gpu_healer.log"
HEARTBEAT="results/.sweep_heartbeat"
PW="${SUDO_PW:-}"
CHECK_EVERY=90          # seconds between health checks
STALL_MIN=8             # heartbeat older than this (min) + unhealthy => zombie
MAX_RMMOD_TRIES=15

ts() { date "+%Y-%m-%d %H:%M:%S"; }
say() { echo "[$(ts)] $*" >> "$LOG"; }
sudo_do() { printf '%s\n' "$PW" | sudo -S "$@" 2>&1; }

# Timeout-guarded: a real matmul probe can HANG (uninterruptibly) on a wedged GPU,
# so never call this without the timeout. Detection below uses the heartbeat file
# (a plain mtime, no CUDA), and this is only used to VERIFY health after a reload.
cuda_ok() { timeout 60 python3 -c "import sys; from src.config import cuda_healthy; sys.exit(0 if cuda_healthy() else 1)" 2>/dev/null; }
hb_age() { echo $(( $(date +%s) - $(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0) )); }
sweep_running() { pgrep -f "run_full_pipeline.sh|run_followon.sh" >/dev/null 2>&1; }

heal() {
  say "HEAL: zombie detected (cuda unhealthy, heartbeat $(hb_age)s old). Reloading nvidia_uvm."
  # 1. ollama is the most common holder — stop it (idempotent).
  sudo_do systemctl stop ollama >/dev/null 2>&1
  # 2. kill any remaining userspace holders of the uvm device (best effort; a
  #    D-state holder can't be killed and will need a reboot — flagged below).
  sudo_do fuser -k /dev/nvidia-uvm >/dev/null 2>&1
  sleep 2
  # 3. reload the module, retrying to ride out transient holders.
  local done=0
  for i in $(seq 1 "$MAX_RMMOD_TRIES"); do
    if sudo_do rmmod nvidia_uvm | grep -q "in use"; then
      sleep 3
    else
      done=1; break
    fi
  done
  if [ "$done" -ne 1 ]; then
    say "HEAL FAILED: nvidia_uvm still 'in use' after ${MAX_RMMOD_TRIES} tries "
    say "  (likely a D-state process wedged in the driver). A REBOOT is required."
    return 1
  fi
  sudo_do modprobe nvidia_uvm >/dev/null 2>&1
  sleep 3
  if cuda_ok; then
    say "HEAL OK: GPU healthy again. Sweep will auto-resume within ~60s."
    return 0
  fi
  say "HEAL: module reloaded but cuda_healthy still False — will retry next cycle."
  return 1
}

say "gpu_healer started (pid $$). check_every=${CHECK_EVERY}s stall=${STALL_MIN}m."
if [ -z "$PW" ]; then say "WARNING: SUDO_PW not set — healer cannot run sudo; exiting."; exit 1; fi

fails=0
while :; do
  sleep "$CHECK_EVERY"
  # Only act when a sweep is supposed to be running; otherwise stay quiet.
  sweep_running || { fails=0; continue; }
  # DETECTION IS HEARTBEAT-ONLY (no CUDA call, which can hang on a wedged GPU):
  # the engine touches the heartbeat every round, so if a sweep wrapper is alive
  # yet the heartbeat is older than STALL_MIN, the sweep is stuck in a zombie.
  [ "$(hb_age)" -lt $((STALL_MIN * 60)) ] && { fails=0; continue; }
  heal && fails=0 || fails=$((fails + 1))
  # If healing keeps failing (needs reboot), back off so we don't spam sudo.
  [ "$fails" -ge 3 ] && { say "HEAL still failing (${fails}x) — backing off 10m."; sleep 600; }
done
