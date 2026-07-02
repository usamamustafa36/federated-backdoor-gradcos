# Stealthy Backdoor Attacks on Federated IDS — Implementation

Code for the thesis *"Stealthy Backdoor Attacks on Federated Intrusion Detection
Systems and Byzantine-Resilient Defenses."* Federated CNN+LSTM intrusion
detector, network-flow backdoor attacks, four baseline Byzantine defenses, and
the proposed **GradCos** defense — evaluated on the **FLNET2023** and
**CICIoT2023** benchmarks (IID and non-IID).

## Research objectives → code

| Objective | Where |
|---|---|
| **O1** Backdoor attacks on FL-IDS (3 trigger types, varying malicious ratio / poison rate) | `src/attacks/` |
| **O2** Benchmark Byzantine defenses (FedAvg, Krum, FLTrust, FLAME) | `src/defenses/{krum,fltrust,flame}.py` |
| **O3** Propose + validate GradCos (no clean server data needed) | `src/defenses/gradcos.py` |
| **O4** Open-source release with one-command reproduction | `run_full_pipeline.sh`, this README |

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
  attacks/triggers.py     trigger design, data poisoning, BSR test set
  defenses/               krum, fltrust, flame, gradcos (Flower strategies)
  metrics/aggregate.py    summaries + comparison tables
experiments/              runnable entry points (see below)
results/                  output JSON + tables + plots
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
- **DR / FPR** malicious-client detection rate / honest-client false-positive rate
- **Stealthiness** = BSR × (1 − DR)

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
