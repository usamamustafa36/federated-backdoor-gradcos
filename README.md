# Trigger Salience, Not Attacker Count, Governs Backdoor Robustness in Federated IDS

Stealthy backdoor attacks on a federated CNN+LSTM network-flow intrusion detector, the
Byzantine-robust defenses meant to stop them, and **GradCos** — a reference-free defense that needs no
clean server-side data.

Evaluated on **CICIoT2023** and **FLNET2023**, IID and non-IID, across **190 attack/defense
configurations** plus a complete **120-cell five-seed campaign** at the headline operating point.

## The finding

The standard framing is that backdoor danger scales with the number of compromised clients. It does
not. **The axis that decides whether a defense holds is the salience of the trigger.**

Holding the malicious fraction fixed at 20% and changing only the trigger:

| trigger | FLTrust | FLAME | Krum | FoolsGold | GradCos |
|---|---|---|---|---|---|
| **fixed** (conspicuous) | 0.004 | 0.015 | 0.951 | 0.375 | **0.004** |
| **statistical** (low-salience) | 0.015 | 0.934 | 1.000 | 1.000 | 1.000 |
| **temporal** (low-salience) | 0.802 | 0.810 | 1.000 | 1.000 | 1.000 |

*Backdoor success rate, mean over seeds 42–46. Same attacker count in every row.*

A conspicuous fixed-pattern trigger is filtered by every similarity-based defense. Low-salience,
in-distribution triggers leave a poisoned update almost collinear with an honest one and defeat Krum,
FLAME, FoolsGold **and GradCos alike**.

The attack is also genuinely stealthy: undefended averaging is subverted in every configuration
(backdoor success 0.90–1.00) while clean accuracy is untouched, so the poisoning is invisible to
accuracy monitoring.

## GradCos, and where it fails

GradCos flags the colluding minority from the pairwise cosine structure of client updates, with no
reference dataset on the server. At the headline operating point over five seeds it is the best
defense on fixed-pattern backdoors: it ties FLTrust's 0.004 backdoor rate while keeping **+0.13
higher clean accuracy**, and holds where Krum collapses.

**It inherits the same blind spot on low-salience triggers.** That is stated here rather than worked
around.

The cause is diagnosable: the shared main-task gradient dominates the update and masks the backdoor
direction. Mean-centring the updates before comparison restores it:

| trigger | detection | backdoor rate |
|---|---|---|
| fixed | 1.000 | 0.003 |
| statistical | 1.000 | 0.081 |
| temporal | 1.000 | 0.358 |

Near-complete on the statistical trigger, only partial on temporal.

## Two methodological points

**Report clean accuracy alongside backdoor success.** Two baselines buy their low backdoor rate with
a badly degraded model — FLTrust sits around 0.56 clean accuracy where FedAvg, Krum, FoolsGold and
GradCos are near 0.70. A defense that stops the backdoor by breaking the detector has not defended
anything.

**Seeds matter, and single-seed results in this area are not trustworthy.** FoolsGold swings from a
backdoor rate of **0.003 to 0.944 across seeds on the same cell**. FLAME is worse on the temporal
trigger, ranging **0.087 to 0.999**, with clean accuracy at 0.663 ± 0.128.

## Layout

```
src/
  data/          streaming load, cleaning, IID / Dirichlet partitioning
  models/        Conv1D -> LSTM -> Dense classifier
  fl/            synchronous round-loop over Flower strategies
  attacks/       trigger design, data poisoning, backdoor test set
  defenses/      krum, fltrust, flame, foolsgold, gradcos
  metrics/       summaries and comparison tables
experiments/     runnable entry points
configs/         experiment configuration
results/         run outputs (JSON), tables, plots
```

## Reproducing

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

python -m experiments.run_sweep --config configs/default.yaml \
  --device cuda --rounds 100 --tag ms \
  --defenses fedavg krum fltrust flame gradcos foolsgold \
  --triggers fixed statistical temporal --ratios 0.2 --poisons 0.1 \
  --seeds 42 43 44 45 46
```

Measured cost is roughly 42 minutes per cell on an RTX 4060.

## What is and is not evaluated

The shipped results cover the `simple` data-poisoning attack. The `constrained` (norm-matching) and
`distributed` (DBA) variants are implemented and runnable but were **not** swept at scale. FLNET2023
is a one-at-a-time sweep along each axis rather than the full grid, and the non-IID slice is a single
configuration. Nothing is claimed from sweeps that were not run.

Training is capped at 400,000 rows per the config, not the full corpus — a compute budget, and the
reason clean accuracy sits near 0.70 rather than higher.

Datasets are not redistributed here.

## License

MIT — see `LICENSE`.
