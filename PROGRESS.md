# FIDA — Project Progress

_Snapshot: 2026-07-09_

Thesis: **"Stealthy Backdoor Attacks on Federated IDS and Byzantine-Resilient
Defenses."** Federated CNN+LSTM intrusion detector on CICIoT2023 (8 grouped
classes, 39 features), built on Flower `Strategy` objects driven by an in-process
synchronous round-loop (`src/fl/engine.py`). The proposed defense is **GradCos**
(in code as defense `gradcos`, default variant `gradcos_method: clique`).

---

## Overall status

- **Code implementation: complete.** Attack (incl. constrained + distributed
  variants), all 5 defenses, trigger redesign, FLAME fix, FLNET2023 loader, and
  the non-IID (Dirichlet) path are all implemented and verified end-to-end.
- **Experiments — 190 / 190 cells DONE. ✅** Finished 2026-07-09 on the GPU.
  - CICIoT2023 IID full grid: **140 / 140.** ✅ (all 5 defenses ×28, incl. GradCos.)
  - FLNET2023 OAT sweep: **40 / 40.** ✅ (clean + trigger/ratio/poison axes.)
  - CICIoT2023 non-IID (Dirichlet) headline subset: **10 / 10.** ✅
  - Tables (`comparison.md`, `summary.csv`, `curves_*.png`) regenerated
    **2026-07-09** from all 190 cells. Verified: no NaN/degenerate cells (the 15
    blank `BSR` entries are clean baselines, where BSR is N/A by definition).
- The earlier CPU follow-on run was a dead end (watchdog death-loop — a single
  CPU round exceeded the 15-min stall watchdog). It was stopped and the sweep was
  finished on the GPU after a one-time zombie-CUDA heal (stop ollama + reload
  `nvidia_uvm`), taking ~5.5 h for the last 14 cells.

---

## Completed

### Attack (Objective O1)
- CNN+LSTM model on CICIoT2023 (`src/models/cnn_lstm.py`).
- 3 triggers (`src/attacks/triggers.py`): `fixed`, `statistical`, `temporal`.
  - `statistical`/`temporal` were **redesigned** to be genuinely *learnable*
    backdoors (mixed-sign, ~1.5–2 sigma, in-distribution, clean-model BSR ≈ 0).
    The originals were out-of-distribution artifacts with clean-model BSR ≈ 1.0.
- Poison ratios {5, 10, 20%}, malicious-client ratios {10, 20, 30%}.
- 3 attack variants (`simple`, `constrained` norm-matching, `distributed`/DBA) and
  non-IID (Dirichlet) partitioning implemented, and now selectable from both
  runners: `run_sweep.py --variants …` / `run_experiment.py --variant …`
  (non-`simple` cells get a `_v{variant}` filename suffix; tables gain a `variant`
  column when present). The 140-cell grid uses `simple`; variant sweeps are
  available to run on demand.

### Defenses (Objective O2)
- FedAvg, Krum, FLTrust, FLAME implemented (`src/defenses/`).
- **FLAME NaN bug fixed**: DP noise was hitting BatchNorm `running_var` buffers,
  driving them negative → NaN models. Noise is now masked to trainable params
  only (`base.py: trainable_flat_mask`, `flame.py: noise_mask`). Every prior
  FLAME cell (incl. clean baseline) had been invalid; now valid.
- Metrics: BSR / CA / DR / FPR + Stealthiness = BSR*(1-DR) (`metrics/aggregate.py`).

### Proposed defense — GradCos (Objective O3)
- Three variants implemented (`src/defenses/gradcos.py`):
  - `meansim` (v1, original TH1 baseline) — fails under collusion at 20–30% malicious.
  - `cluster` (v2) — failed ablation, no real detection gain at full scale.
  - **`clique` (v3, current default)** — validated in standalone full-scale runs
    (400k / 100 rounds, fixed trigger): DR≈0.97–1.00, BSR≈0.004, low FPR at
    10/20/30% malicious, where meansim/Krum/FLAME all fail. Reference-free.
- Now reflected in the full-grid tables: all **28 GradCos cells present** on the
  CICIoT2023 grid (`results/comparison.md`, `summary.csv`, `curves_*.png`).

### Infrastructure
- Resumable sweep (`run_sweep.py` skips existing result JSONs; `--force` overrides).
- Atomic result writes; heartbeat + staleness watchdog in `run_full_pipeline.sh`.
- Hardened CUDA handling: real-matmul `cuda_healthy()` probe, exit-3 abort on fatal
  CUDA errors, watchdog kill on silent hangs.

---

## Sweep status (140-cell corrected full grid)

Grid = 5 defenses × (1 clean + 3 triggers × 3 ratios × 3 poisons) = 5 × 28 = 140.

| Defense  | Cells done |
|----------|-----------:|
| fedavg   | 28 / 28 ✅ |
| krum     | 28 / 28 ✅ |
| fltrust  | 28 / 28 ✅ |
| flame    | 28 / 28 ✅ |
| gradcos  | 28 / 28 ✅ |
| **Total**| **140 / 140 ✅** |

This grid is the corrected one (redesigned learnable triggers + FLAME fix +
GradCos clique). Backups of superseded results are under `results/_*backup*/`.

---

## What's left

Nothing required — all 190 planned cells are done and the tables are current.

Optional (TH1 nice-to-haves, runnable on demand, not needed for the core thesis):
- Full-scale `constrained` / `distributed` attack-variant sweeps
  (`run_sweep.py --variants constrained distributed …`).
- More non-IID points (other defenses/ratios beyond the headline subset).

### How to resume

The whole thing is resumable (`run_sweep` skips cells whose JSON already exists).
`run_followon.sh` re-runs every axis and skips the done cells, so it re-attempts
the 10 missing FLNET cells **and** the 4 missing non-IID cells, then rebuilds
tables.

1. Heal the GPU (needs your sudo — this is the practical path):
   ```
   sudo systemctl stop ollama && sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm
   ```
2. Stop any thrashing CPU run and relaunch on GPU:
   ```
   cd "/home/ubuntu/Projects/THESIS/IN progress/fida"
   pkill -f run_followon.sh
   setsid nohup env DEVICE=cuda bash run_followon.sh >/dev/null 2>&1 & disown
   tail -f results/followon.log
   ```
On the RTX 4060 the 14 cells finish in a few hours. CPU is only viable if the box
is otherwise idle (~10.8h/attack cell).

---

## Known blockers / notes

- **GPU zombie CUDA state** recurs on this box: `cuda_healthy()` False while
  `ollama` holds `nvidia_uvm`. Fix = stop ollama + reload the module (or reboot).
  No passwordless sudo, so the user runs it.
- **CPU path is unreliable under load.** A CPU attack cell is ~10.8h; when the box
  is CPU-contended (or torch oversubscribes threads, as on 2026-07-09), a single
  round exceeds the 15-min stall watchdog and cells are killed before they write.
  Prefer GPU.
- **FIXED 2026-07-09 — exit-137 treated as success + unbounded retries.**
  `run_followon.sh:run_resumable` previously only retried exit 3; a SIGKILL/OOM
  (137) or watchdog kill (143) was read as a clean finish (`return 0`), which
  silently abandoned the FLNET poison-axis on 2026-07-06. It now retries on
  137/143 too, and a `MAX_ATTEMPTS=8` cap stops a persistently-stalling cell from
  looping forever (the CPU watchdog death-loop that was live on 2026-07-09).
- Repo IS a git repository now (Objective O4 done): LICENSE + README + one-command
  repro present.
