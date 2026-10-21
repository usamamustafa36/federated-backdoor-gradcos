# Stealthy Backdoor Attacks on Federated IDS — Implementation

Code for the thesis *"Stealthy Backdoor Attacks on Federated Intrusion Detection
Systems and Byzantine-Resilient Defenses."* Federated CNN+LSTM intrusion
detector, network-flow backdoor attacks, four baseline Byzantine defenses, and
the proposed **GradCos** defense — evaluated on the **FLNET2023** and
**CICIoT2023** benchmarks (IID and non-IID).

## The manuscript

The paper built from this code targets the **Journal of Information Security and
Applications** (Elsevier), subscription track. The submission package lives in
`paper/` — Elsevier `elsarticle` source, `refs.bib`, declarations, Highlights, cover
letter and build targets. Start with **`paper/README.txt`**, which covers how to rebuild
it and the four things that still need a human decision before it can go out.

Every number in the manuscript is generated from the files in `results/` by
`paper/make_numbers.py`; none is typed by hand. `cd paper && make check` reports what is
still unresolved, grouped by the lane of `run_remediation.sh` that resolves it.

## Research objectives → code

| Objective | Where |
|---|---|
| **O1** Backdoor attacks on FL-IDS (3 trigger types, varying malicious ratio / poison rate) | `src/attacks/` |
| **O2** Benchmark Byzantine defenses (FedAvg, Krum, FLTrust, FLAME) | `src/defenses/{krum,fltrust,flame}.py` |
| **O3** Propose + validate GradCos (no clean server data needed) | `src/defenses/gradcos.py` |
| **O4** Open-source release with one-command reproduction | `run_full_pipeline.sh`, this README |

## What is and isn't evaluated

The shipped results (`results/summary.csv`, 190 cells) cover the `simple` data-poisoning
attack only. The `constrained` (norm-matching), `distributed` (DBA) and the two
defense-aware variants (`decorrelated`, `adaptive`) are implemented and runnable but
not yet swept at scale. FLNET2023 is a one-at-a-time sweep along each axis rather than
the full 3×3×3 grid, and the non-IID slice is a single configuration. See
`PROGRESS.md` for the measured results and limitations — including where GradCos does
**not** win: it holds against the `fixed` trigger up to 30% malicious clients but is
largely defeated by the low-salience `statistical` and `temporal` triggers.

**Read `REMEDIATION.md` before trusting any claim in the paper.** It tracks the 13
issues from the pre-submission review, what was fixed, and which experiments are still
queued in `run_remediation.sh`. Anything unfinished is marked `\PENDING` in
`paper/main.tex`; deleting that macro's definition turns every unfinished claim into a
compile error, on purpose.

### Two things the audit already overturned

- **Trigger realizability.** `scripts/realizability_audit.py` shows marginal σ says
  almost nothing about joint plausibility: the `fixed` trigger at 0.25× has a largest
  marginal deviation of 0.5σ and still sits at the 99.97th percentile of joint
  benign variation, while `donor` triggers have 9–16σ marginals and are jointly
  typical. The `temporal` trigger is jointly implausible by ~250×. The threat model is
  feature-space only, and the paper now says so.
- **False positives.** FPR was computed all along but never tabulated. FLAME flags
  **40% of honest clients** to reach its low backdoor rate, and on low-salience
  triggers GradCos's detector is at chance (DR 0.11 vs FPR 0.12).

## Layout

```
configs/default.yaml      experiment configuration (data, FL, model, attack, defense)
data/ciciot2023/          train.parquet + test.parquet  (38.5M rows, 39 features)
src/
  config.py               config loader, seeding, device
  data/preprocess.py      memory-safe streaming load + clean + scale
  data/partition.py       IID / non-IID (Dirichlet) client partitioning
  models/cnn_lstm.py      Conv1D -> LSTM -> Dense -> Softmax classifier
  fl/engine.py            synchronous round-loop driving Flower strategies
  fl/torch_utils.py       weights<->ndarrays, local train, evaluate
  fl/build.py             client + strategy factories
  attacks/triggers.py     trigger design (sigma + donor modes), poisoning, BSR test set
  attacks/evasion.py      defense-aware colluder decorrelation (adaptive attacker)
  attacks/realizability.py joint-plausibility statistics for a trigger
  defenses/               direction-based: krum, fltrust, flame, foolsgold, gradcos
  defenses/robust_stats.py magnitude/order-statistic controls: median, trimmedmean,
                          rfa, bulyan, normclip
  metrics/aggregate.py    summaries + comparison tables
experiments/              runnable entry points (see below)
scripts/calibrate_defenses.py   held-out hyperparameter protocol
scripts/realizability_audit.py  stand-alone trigger audit
run_remediation.sh        prioritised, resumable reviewer-remediation run plan
results/                  output JSON + tables + plots
results/artifact/         generated long tables cited by the supplement (written by
                          paper/make_numbers.py; e.g. realizability_ciciot2023.md, the
                          full trigger audit). Do not edit by hand.
```

## Federated learning + Flower

Aggregation uses **real Flower `Strategy` objects** (`flwr.server.strategy.FedAvg`
and our `DefenseStrategy` subclasses). A thin in-process round-loop
(`src/fl/engine.py`) trains clients and hands their genuine `FitRes` updates to
`strategy.aggregate_fit` — full Flower aggregation semantics without the Ray
backend (faster + debuggable on one laptop, and side-steps the global env's
protobuf conflict).

## Setup

```bash
pip install -r requirements.txt
```

GPU note: if `torch.cuda.is_available()` is False on a machine that has an NVIDIA
GPU, reload the kernel module:

```bash
sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm
```

**What actually causes this on a laptop: suspend, not another process.** Sleeping
mid-run powers the GPU down under a live CUDA context; it comes back with the
context invalidated (`Xid 31`, MMU fault), and the next call fails with
`unspecified launch failure` or `CUDA unknown error`. Reloading `nvidia_uvm`
works because it rebuilds UVM state after the resume, which is why stopping
`ollama` at the same time looked like the fix — it was not. Before a long sweep,
run it on mains under an inhibitor:

```bash
systemd-inhibit --what=sleep:idle:handle-lid-switch --why="sweep" --mode=block \
  env DEVICE=cuda bash run_full_pipeline.sh
```

## Run

```bash
# 0. sanity-check the data pipeline
python -m experiments.smoke_data

# 1. quick end-to-end check (tiny, ~1 min): attack + a defense
python -m experiments.smoke_integration gradcos

# 2. clean federated baseline
python -m experiments.run_baseline --rounds 100

# 3. one attack/defense cell
python -m experiments.run_experiment --attack --defense gradcos \
    --malicious-ratio 0.2 --poison-rate 0.1 --trigger fixed --rounds 100

# 4. the full matrix (defenses x triggers x ratios x poison rates)
python -m experiments.run_sweep --rounds 100 \
    --defenses fedavg krum fltrust flame gradcos \
    --triggers fixed statistical temporal \
    --ratios 0.1 0.2 0.3 --poisons 0.05 0.1 0.2

# 5. build result tables + plots from results/
python -m experiments.make_tables
```

Add `--quick` to `run_sweep` to validate the whole matrix on tiny data first.

### One-command reproduction

`run_full_pipeline.sh` runs the full resumable sweep (skips cells whose result
JSON already exists) and rebuilds the tables/plots. It is crash- and
GPU-zombie-tolerant (real-kernel health probe + staleness watchdog):

```bash
# CICIoT2023, full 3x3x3 grid on the GPU (resumes if interrupted)
DEVICE=cuda FULL_GRID=1 bash run_full_pipeline.sh

# FLNET2023 (primary dataset): fetch the CSVs, then sweep with its config
python3 scripts/fetch_flnet2023.py
python -m experiments.run_sweep --config configs/flnet2023.yaml --device cuda --rounds 100 \
    --defenses fedavg krum fltrust flame gradcos \
    --triggers fixed statistical temporal --ratios 0.1 0.2 0.3 --poisons 0.05 0.1 0.2

# non-IID (Dirichlet) slice — distinct --tag so it doesn't overwrite IID cells
python -m experiments.run_sweep --tag sweep_noniid --partition dirichlet --device cuda \
    --rounds 100 --triggers fixed --ratios 0.2 --poisons 0.1
```

`experiments/make_tables.py` groups the comparison tables by
`(dataset, partition)`, so CICIoT-IID, CICIoT-non-IID, and FLNET results stay
separate.

## Metrics

- **CA** clean accuracy (non-triggered traffic)
- **BSR** backdoor success rate (triggered attack classified benign)
- **DR / FPR** malicious-client detection rate / honest-client false-positive rate.
  **Always report these together** — a defense that flags clients turns a false
  positive into lost training signal, so DR alone says nothing about what the detector
  cost. Defenses that never single out a client report both as N/A, not 0.
- **Stealthiness** = BSR × (1 − DR)
- **salience_gap** how far the backdoor rotates a poisoned update off the honest
  consensus direction — the quantity a cosine filter has to resolve, logged per round
  so outcomes can be regressed on it instead of on a trigger's name
- **mal_pair_cos / honest_pair_cos** the collusion signal GradCos, FoolsGold and FLAME
  read; the adaptive attacker exists to drive the first of these down to the second
- **mal_norm_ratio** median malicious / median honest update norm — what a
  magnitude-based rule sees

## Datasets

- **CICIoT2023** — full 38.5M rows, 39 features; `label` binary / `Label`
  34-class / `attack_class` 8-class. Set `data.label_mode` in the config.
  Ships as `data/ciciot2023/{train,test}.parquet`.
- **FLNET2023** (primary FL-IDS benchmark) — fetch the CICFlowMeter CSVs
  (~2.8 GB, PCAPs skipped) with `python3 scripts/fetch_flnet2023.py`; they land
  under `data/flnet2023/<Category>/…` where `load_flnet2023` picks them up.
  Labels come from the top-level category folder (DDoS/DoS/Infiltration/Web/
  Normal; Normal = benign). Use `configs/flnet2023.yaml`.

Both datasets are excluded from git (large / licensed) via `.gitignore`.
