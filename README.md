# A Silent Measurement Hazard in PyTorch Federated Learning

Code, registrations and result files for "A Silent Measurement Hazard in PyTorch Federated Learning: When Byzantine-Robust Aggregators Decide on a BatchNorm Counter" (U. Mustafa, I. Rashid).

When clients send a `state_dict()`, BatchNorm's `num_batches_tracked` enters the vector that robust aggregation rules compare. This repository measures what that changes, and contains the mask that removes it.

## Layout

| Path | Contents |
|---|---|
| `src/` | Federated pipeline, attacks and the thirteen aggregation rules |
| `experiments/` | Campaign drivers, probes, and the re-run of a published pipeline (`experiments/r2_exposed/`) |
| `results/` | Result files and per-run logs behind every number in the paper |
| `iterations/PREREG_*.md` | Registration documents, with their amendments and hash manifests |
| `paper/` | LaTeX sources, generated `numbers*.tex`, figure and analysis scripts |
| `SURVEY.md` | Notes from the survey of public implementations, with line references |
| `tests/` | Unit tests |

## Reproducing

```
pip install -r requirements.txt
PYTHONPATH=. pytest -q tests
cd paper && make numbers && make && make check
```

`make numbers` regenerates the tables' and text's outcome numbers and the figures from `results/`. Datasets are not included: CICIoT2023, CIFAR-10 and BloodMNIST are public and fetched separately.

## Status of the published-pipeline re-run

Registered families are complete: H1 120/120 runs and H2 240/240. Of the 60 Krum `trainable` runs, which are reported but not tested, 45 are complete in this version; the other 15 are still open.
