# Where this stands and what to do next

## Update, 21 October 2026 (iteration 1 of the improvement chain)

Read `iterations/LEDGER.md` first; it supersedes the section below wherever they differ.

- **CPU only** (user's decision). The GPU is in the CUDA zombie state; do not wait for it.
- **Pre-fix results archived.** All 321 pre-fix files are now in `results/_pre_counterfix/`
  (via `scripts/archive_pre_counterfix.sh`); the Sep-5 post-fix pilots (ab*/sd*/scb*/integ*)
  are in `results/_pilot_postfix_sep5/` (valid, but heterogeneous scale; see its README).
  The manuscript therefore shows `\PENDING` almost everywhere. That is the honest state.
- **P1 campaign running**: `experiments/postfix/run_p1.sh` -> `results/postfix_p1/`.
  Paired full-vs-trainable A/B, 12 defenses x {IID, Dirichlet} x clean/attacked x 10 seeds,
  CPU, 6 lanes x 2 threads. Resumable (re-run the script). Analyse with
  `python3 paper/analyse_postfix.py` -> `paper/numbers_postfix.tex` + `results/postfix_p1/summary_pairs.md`.
- **New per-round diagnostics** in every run: `buffer_norm_share`, `buffer_dist_share`,
  `pair_cos_full`, `pair_cos_sig` (src/fl/engine.py `_defect_diagnostics`, logging only).

---

## Written 6 September 2026 (historical)

Written 6 September 2026. Read this first; it is the index to everything else.

## Right now: blocked on the GPU

The 20-seed FoolsGold run died on launch. The machine **suspended** overnight (no reboot
since 5 Sep 00:15) which invalidated the CUDA context, and it is **on battery**, which is
what causes the suspend. This is the same failure documented in `SUBMISSION_STATUS.md` that
killed the 28 August and 3 September runs.

To resume:

    # 1. plug into mains
    # 2. reload the module (needs your password)
    sudo systemctl stop ollama && sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm
    # 3. relaunch -- resumable, skips completed cells
    bash /tmp/.../scratchpad/run_fg20.sh        # path in the session transcript
    # or re-create it: 20 seeds, foolsgold, non-IID, configs/_ab_{full,trainable}.yaml

Also worth closing: a VLC process has been playing a video for 28 hours at 274% CPU, and
Zoom for 34 hours. They will slow any re-run.

## What was found (the short version)

A single BatchNorm coordinate -- `num_batches_tracked` -- is transmitted in `state_dict()`
and carries **98.1% of the squared norm** of a real client update. It is **functionally
inert** under PyTorch's default momentum. Every cosine, distance and norm a Byzantine-robust
rule computes is dominated by it.

Read in this order:

| file | what it is |
|---|---|
| `CONTRIBUTION.md` | the claim at the precision the evidence supports, incl. retractions |
| `SURVEY.md` | which real implementations are affected (6 immune, 3 affected) |
| `QA_FINDINGS.md` | 20 defects found in the code and manuscript, by severity |
| `PUBLISHABILITY.md` | the four blockers to acceptance and their status |
| `REFRAME.md` | proposed new paper structure |

## Established, and safe to build on

- Counter dominance: 98.1% on the real config; 20-of-11,183,582 coords carrying 68-99% on
  ResNet-18/CIFAR-10
- Inertness: corrupting it by +100,000 leaves running stats and eval output bit-identical
- Compression: honest-client cosine 0.831 (parameters) vs 0.998 (full vector), ~96x
- The FoolsGold **mechanism**: identical inputs through both code paths give weights
  `[0,1,0,1,0,0,0,0,0,0]` vs `[.19,1,.74,1,0,1,0,.19,1,.77]` -- 8 clients zeroed vs 2 --
  reproduced in closed form. FoolsGold ends up training on whichever clients hold the most
  unusual amount of data.
- Detector fixed: CA 0.703 -> 0.81 by changing class weighting to `effective`, past a tuned
  RandomForest (0.786). Full four-scheme comparison in `configs/default.yaml`.
- The realizability audit is untouched by all of this and remains independently novel.

## NOT established -- do not write these up

- **Any outcome effect at p < 0.05.** FoolsGold attacked: +0.209, 95% CI [-0.030, +0.448],
  p=0.072 at n=5. Marginal. This is what the 20-seed run was for.
- **The scaling prediction is refuted.** The effect does not grow with batches per round:
  FoolsGold went +0.460 -> +0.085 -> **-0.189** as the counter's norm share rose 80->96->99%.
- **Generality across defenses.** Four of five showed <= 0.03.
- **"The field measures the wrong thing."** False. FoolsGold's and FLDetector's official
  implementations use gradients and are immune; so does DBA and Attack of the Tails, both
  cited in this manuscript.

## Code changes made

- `signal_subspace: trainable|full` (`configs/default.yaml`) -- decisions restricted to
  trainable parameters; `full` reproduces the defect for controlled comparison. Aggregation
  always uses the full vector.
- Applied across `gradcos.py`, `krum.py`, `flame.py`, `fltrust.py`, `foolsgold.py`,
  `robust_stats.py`, `fl/engine.py`, `attacks/evasion.py`.
- `training.class_weighting: effective` -- new, with the measured comparison in the config.
- `fldetector.py` -- new defense (KDD 2022), a third `CONSISTENCY_BASED` family.
- `run_sweep.py` -- per-cell timing was cumulative and is now per-cell (the campaign runtime
  estimates were built on the wrong numbers).
- `make_numbers.py` -- dedup was decided by filename sort order; field-level fallback;
  realizability and grid-floor macros generated rather than typed.
- `aggregate_multiseed.py` -- now reads live subdirectories, skips `_`-prefixed archives.

Verified: 33/33 then 48/48 smoke cells across all 12 defenses, zero errors.

## The campaign has NOT been restarted

`scripts/archive_pre_counterfix.sh` is staged but **not run**. All 321 pre-fix result files
are still in `results/`. They were measured through the broken signal path and are not valid
for the reframed paper, but nothing has been moved or deleted.

`run_remediation.sh` gained a **lane 0** that re-runs the multi-seed headline first.
