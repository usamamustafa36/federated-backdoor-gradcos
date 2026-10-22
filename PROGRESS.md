# FIDA — Project Progress

_Snapshot: 2026-07-23 (base) · 2026-07-28 (publication-hardening) · **2026-08-27 (reviewer remediation)**_

> **2026-08-27 — reviewer-remediation pass.** A hostile pre-submission review
> raised 13 issues. Code and paper for all 13 are in; the experiments for 6 of
> them are queued and waiting on the GPU. See `REMEDIATION.md` for the
> issue-by-issue status. Headline changes: an **adaptive (defense-aware)
> attacker** that decorrelates the colluding cohort with zero-sum noise
> (`src/attacks/evasion.py`); a **measured salience axis** logged every round
> (`FederatedEngine._update_geometry`) plus a trigger-magnitude sweep, so the
> salience claim stops being a two-group contrast; **five non-cosine defenses**
> as the control family (`src/defenses/robust_stats.py`); a **joint-plausibility
> audit** of the triggers (`src/attacks/realizability.py`) which finds the
> "in-distribution" premise unsupported and the temporal trigger jointly
> implausible by ~250x; a **held-out tuning protocol**
> (`scripts/calibrate_defenses.py`); and **FPR reported everywhere**, which
> reveals FLAME flags 40% of honest clients and GradCos is at chance on
> low-salience triggers. The paper was rewritten around these
> (`paper/main.tex`; previous version kept as `main.tex.pre-remediation.bak`).

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
  non-IID (Dirichlet) partitioning implemented, and selectable from both
  runners: `run_sweep.py --variants …` / `run_experiment.py --variant …`
  (non-`simple` cells get a `_v{variant}` filename suffix; tables gain a `variant`
  column when present).
  **Evaluation scope: `simple` only.** Every reported cell except one uses
  `simple`. A 20-cell `constrained`/`distributed` sweep was attempted on
  2026-07-11 and died on its 3rd cell with a CUDA `unspecified launch failure`
  (`results/variants.log:10`, `rc=3` on both dataset legs — the trailing
  "COMPLETE" line in that log is misleading). One cell survives
  (`…fedavg_atk1_m0.2_p0.1_fixed_vconstrained.json`). Deliberately **not**
  re-run — see *Scope and limitations*.

### Defenses (Objective O2)
- FedAvg, Krum, FLTrust, FLAME implemented (`src/defenses/`).
- **FLAME NaN bug fixed**: DP noise was hitting BatchNorm `running_var` buffers,
  driving them negative → NaN models. Noise is now masked to trainable params
  only (`base.py: trainable_flat_mask`, `flame.py: noise_mask`). Every prior
  FLAME cell (incl. clean baseline) had been invalid; now valid.
- Metrics: BSR / CA / DR / FPR + Stealthiness = BSR*(1-DR) (`metrics/aggregate.py`).

### Proposed defense — GradCos (Objective O3)
- Three detection methods implemented (`src/defenses/gradcos.py`):
  - `meansim` (v1) — the method as written in TH1 (mean pairwise cosine
    similarity vs an adaptive threshold). Fails under collusion at 20–30%
    malicious: colluding attackers prop up each other's mean similarity.
  - `cluster` (v2) — ablation; no real detection gain at full scale.
  - **`clique` (v3, current default)** — reference-free, collusion-robust.
- **Deviation from TH1 to declare in the thesis:** TH1 specifies `meansim`; the
  evaluated default is `clique`. Present `clique` as the stated refinement and
  keep `meansim` as the v1 ablation.
- All **28 GradCos cells** are present on the CICIoT2023 grid
  (`results/comparison.md`, `summary.csv`, `curves_*.png`).
- Measured behaviour — see *Headline findings* below. GradCos is strong on the
  `fixed` trigger and weak on `statistical`/`temporal`; it does **not** lead
  across all configurations.

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

## Headline findings (what the data actually says)

Source: `results/summary.csv`, CICIoT2023 / IID, mean BSR over each trigger's
9 attack cells (lower = better defense).

| trigger | fedavg | krum | flame | fltrust | **gradcos** |
|---|---:|---:|---:|---:|---:|
| fixed       | 0.945 | 0.595 | 0.045 | 0.010 | **0.154** (DR 0.80) |
| statistical | 1.000 | 0.799 | 0.906 | **0.001** | 0.893 (DR 0.19) |
| temporal    | 1.000 | 0.671 | 0.705 | 0.568 | 0.999 (DR 0.12) |

1. **The attack works.** Undefended FedAvg is backdoored in every configuration
   (BSR 0.90–1.00) with clean accuracy unchanged (0.699 clean vs 0.693 under
   attack) — i.e. the backdoor is genuinely stealthy, which is TH1's premise.
2. **GradCos's limiting axis is trigger type, not malicious ratio.** On `fixed`
   it holds at 20–30% malicious where Krum collapses:

   ```
   m=0.2 p=0.2   fedavg=0.999  krum=0.150  flame=0.010  fltrust=0.004  gradcos=0.004
   m=0.3 p=0.1   fedavg=1.000  krum=0.995  flame=0.074  fltrust=0.004  gradcos=0.078
   m=0.3 p=0.2   fedavg=1.000  krum=1.000  flame=0.056  fltrust=0.004  gradcos=0.004
   ```
   On the redesigned `statistical`/`temporal` triggers it mostly fails: those
   triggers are in-distribution and low-magnitude, so a poisoned update's
   *direction* barely departs from an honest one and the cosine signal vanishes.
   Two `fixed` outliers remain: m0.2/p0.05 (BSR 0.482) and m0.3/p0.05 (0.946).
3. **Low BSR is not free.** On CICIoT, FLAME's and FLTrust's *clean* models are
   degraded (CA 0.550 / 0.514, macro-F1 0.334 / 0.413) against FedAvg's
   0.700 / 0.566. Part of their low BSR is a weakened model, not detection
   quality. GradCos and Krum keep FedAvg-level clean accuracy (0.709 / 0.686).
   Any defense comparison in the thesis must report CA and macro-F1 alongside
   BSR, or it flatters FLAME/FLTrust.
4. Seed sensitivity at borderline operating points is real: the FLNET
   gradcos/fixed/m0.2/p0.1 cell gives BSR {seed42: 0.98, 43: 0.18, 44: 0.008,
   45: 0.008}. The committed grid keeps the worst-case draw (seed 42) rather
   than cherry-picking.

### O3 claim — how it must be worded

TH1 says GradCos is superior "across all evaluated attack configurations". That
is **not supported**: across the 35 attack configurations GradCos has the
strictly-lowest-or-tied BSR in only one. Supported claim instead:

> GradCos matches the strongest baselines (FLAME, FLTrust) against fixed-pattern
> backdoors at up to 30% malicious clients — where Krum collapses — while
> requiring no clean server-side reference data and preserving clean accuracy
> that FLTrust and FLAME sacrifice. Low-salience statistical and temporal
> triggers defeat its cosine-similarity signal and remain an open limitation.

---

## Scope and limitations (as evaluated)

- **Attack variants: `simple` only.** `constrained` and `distributed` are
  implemented and runnable but not evaluated at scale (one `constrained` cell
  exists). TH1's "three attack variants are evaluated" therefore overstates the
  evaluation; scope it to `simple` in the write-up, or reduce the claim to
  "three variants are implemented; `simple` is evaluated".
- **FLNET2023 is a one-at-a-time sweep**, not the full 3×3×3 grid: 7 attack
  configurations per defense along the trigger / ratio / poison axes.
- **non-IID is a single headline point** (fixed, m0.2, p0.1) × 5 defenses.
- **CICIoT2023 clean accuracy is ~0.70 with macro-F1 ~0.55** for the 8-class
  grouped task under this 20-client / 100-round / 400k-row budget. Comparisons
  across defenses are internally consistent, but this is not a state-of-the-art
  centralized IDS number and should not be presented as one. FLNET2023 reaches
  CA 0.9995 / macro-F1 0.9994.
- **O4 is not finished:** the repo has a MIT LICENSE, README and one-command
  reproduction, but no public remote — nothing is actually published yet, so
  "release ... enabling the research community to verify" is unmet until it is
  pushed.

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

- **GPU zombie CUDA state** recurs on this box, and the cause was misdiagnosed for
  weeks. It is **system suspend**, not `ollama`. Confirmed 2026-09-04 from
  `journalctl`: the box suspended at 23:26:31 on 3 September, two minutes into a
  cell, resumed at 07:25:05, and `dmesg` shows `Xid 31` MMU faults naming our own
  `python3` PID. The 28 August failure has the same shape. `ollama` was already
  stopped during the 3 September run and it failed anyway. Reloading `nvidia_uvm`
  fixes it because it rebuilds UVM state after the resume, which is what made the
  ollama theory look right.
  Fix = run on mains, under an inhibitor:
  `systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block env DEVICE=cuda bash run_remediation.sh`.
  `run_remediation.sh` now refuses to start a lane while on battery. Recovery
  after a suspend still needs the module reload, and there is no passwordless
  sudo, so the user runs that.
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
- Objective O4 is **partially** done: git repo + MIT LICENSE + README +
  one-command repro are present, but there is no git remote — the code has not
  been published anywhere yet.
