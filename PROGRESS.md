# FIDA — Project Progress

_Snapshot: 2026-07-02_

Thesis: **"Stealthy Backdoor Attacks on Federated IDS and Byzantine-Resilient
Defenses."** Federated CNN+LSTM intrusion detector on CICIoT2023 (8 grouped
classes, 39 features), built on Flower `Strategy` objects driven by an in-process
synchronous round-loop (`src/fl/engine.py`). The proposed defense is **GradCos**
(in code as defense `gradcos`, default variant `gradcos_method: clique`).

---

## Overall status

- **Code implementation: essentially complete.** Attack, all 5 defenses, trigger
  redesign, and the FLAME fix are all done and saved.
- **Experiments: 106 / 140 sweep cells done (~76%).** 34 cells remain — the
  6 outstanding FLAME-temporal cells plus **all 28 GradCos cells** (the proposed
  method currently has 0 cells in the corrected full grid).
- **Blocked on GPU.** Last run aborted 2026-06-30 20:44 after the GPU fell into
  the recurring zombie CUDA state and never recovered. GPU is still zombie as of
  this snapshot.

---

## Completed

### Attack (Objective O1)
- CNN+LSTM model on CICIoT2023 (`src/models/cnn_lstm.py`).
- 3 triggers (`src/attacks/triggers.py`): `fixed`, `statistical`, `temporal`.
  - `statistical`/`temporal` were **redesigned** to be genuinely *learnable*
    backdoors (mixed-sign, ~1.5–2 sigma, in-distribution, clean-model BSR ≈ 0).
    The originals were out-of-distribution artifacts with clean-model BSR ≈ 1.0.
- Poison ratios {5, 10, 20%}, malicious-client ratios {10, 20, 30%}.
- Attack variants and non-IID (Dirichlet) partitioning coded.

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
- ⚠️ Not yet reflected in the full-grid comparison tables (0 GradCos cells on disk).

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
| flame    | 22 / 28    |
| gradcos  |  0 / 28 ⚠️ |
| **Total**| **106 / 140** |

This grid is the corrected one (redesigned learnable triggers + FLAME fix +
GradCos clique). Backups of superseded results are under `results/_*backup*/`.

---

## What's left

1. **Finish the sweep (34 cells).** 6 FLAME-temporal + all 28 GradCos cells.
   Blocked on the GPU zombie state. ~17 min/cell on the RTX 4060 ≈ ~10h.
   - Clear the GPU (no passwordless sudo, so the user must run this):
     `sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm` (or reboot).
   - Resume:
     `setsid nohup env DEVICE=cuda FULL_GRID=1 bash run_full_pipeline.sh >/dev/null 2>&1 & disown`
     (skips the 106 done cells).
2. **Regenerate final tables.** `make_tables` → `results/comparison.md`,
   `summary.csv`, `curves_*.png` (must include the GradCos rows once computed).
3. **TH1 gap tasks:**
   - FLNET2023 run — loader coded, blocked on data download (SharePoint auth gave
     0-byte files).
   - A non-IID (Dirichlet) run for the comparison.
   - Open-source packaging (Objective O4): git init, LICENSE, one-command repro.

---

## Known blockers / notes

- **GPU zombie CUDA state** recurs on this box (`cuda_healthy()` returns False while
  `nvidia_uvm` is wedged; `nvidia-smi` shows ~10 MiB, 0% util, no process holding it).
  Fix = reload `nvidia_uvm` or reboot. No passwordless sudo, so this needs the user.
- CPU-only fallback works but is ~23× slower on attack cells (~10.8h/cell), so GPU
  is the practical path.
- Repo is not yet a git repository.
