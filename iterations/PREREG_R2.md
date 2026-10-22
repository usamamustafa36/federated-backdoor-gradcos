# PREREG_R2: an exposed published pipeline re-run with and without the counter mask

Written 2026-10-23 03:00 PKT (iteration 25), before any R2 outcome was seen. The only
R2 run started before this file was a one-round plumbing smoke (Krum, targeted, c_frac
0.3, seed 3, full arm; `results/r2_exposed/smoke_*.json`); its contents were not read
before this file was committed. It is excluded from every test below.

## Why this pipeline
Blind review 1 (item 3, question 2): "Does any published number change under the mask?"
The survey (SURVEY.md) found two exposed public pipelines with reported numbers:
AlignIns (CVPR 2025; CIFAR-100 VGG-9, Tiny-ImageNet ResNet-18) and yjlee22/byzantineFL
(Lee, Park, Kang, "Security-Preserving Federated Learning via Byzantine-Sensitive
Triplet Distance", ISBI 2024, arXiv:2210.16519). We start with byzantineFL because

* its rules (Krum, trimmed-mean, Fang) compare **full `state_dict` models** through
  `multi_vectorization`, which concatenates every entry, `num_batches_tracked` included;
* it uses torchvision ResNet-18 (L = 20 BatchNorm layers) and **quantity skew** (each
  client draws 500-1000 samples, so with drop_last batch size 20 and 5 local epochs,
  B_i ranges over about 125-250 local batches): exactly the unequal-B case in which
  Corollary 2 predicts the distance term L (B_i - B_j)^2;
* BloodMNIST (28x28, 11,959 train) is small enough to run the authors' whole grid on
  one GPU, and pilot rounds on CPU.
AlignIns (VGG-9/CIFAR-100, 20 clients, Dirichlet) is the second target, GPU only; it
gets its own amendment when R2-byzFL is complete.

## What is run (authors' code, unmodified)
`_ext/byzantineFL` at commit c6d8de379317a3b9ce30f2372e9321a8e0a89b97, executed by
`experiments/r2_exposed/run_byzfl.py` through runpy. The harness changes only: dataset
root (data/medmnist; file MD5 7053d0359d879ad8a5505303e11de1dc = medmnist's), a stub for
the unused tensorboard import, logging, and in the masked arms the one function
(`utils.byzantine_fl.multi_vectorization`) through which all three rules read clients.
What the rules aggregate (and copy into the global model) is the authors' code in every arm.

Arms (paired by seed: same partition, same compromised clients, same initialisation):
* `full`: the authors' behaviour (counter in the decision vector);
* `nonbt`: `num_batches_tracked` removed from the decision vector only (primary fix);
* `trainable`: all BatchNorm buffers removed from the decision vector (secondary;
  reported, not tested).

Grid: the authors' `execute/run1.sh` (Fig. 3 of the paper): method in {krum,
trimmed_mean, fang} (fedavg once per seed as reference; its arms are identical by
construction), c_frac in {0.1, 0.2, 0.3}, p in {target, untarget}, `--quantity_skew`,
all other options at the authors' defaults (alpha 10, 10 clients, frac 1.0, local_ep 5,
local_bs 20, lr 0.001, global_ep 200, early stopping patience 8 / delta 0.01, mp_alpha
10, mp_lambda 10). The DCA method itself is not run (its code stops at an `ipdb` trace).
Seeds: 3 (authors' default) and 4-12, ten in all. 3 rules x 3 c_frac x 2 p x 2 arms x 10
seeds = 360 runs + 10 fedavg + 120 `trainable` runs (krum only).

## Outcome (the paper's reported quantity)
Fig. 3 of the paper plots the **minimum test error rate over rounds**, 1 - max_t acc_t/100.
That is the outcome Y. Also reported: final-round accuracy and rounds to early stop.

## Mechanism predictions (from Prop. 1 / Cor. 2, signed, made now)
M1. In the `full` arm the counter carries a large share of the pairwise squared distances
    between received models: median over rounds and seeds of `counter_share_dist` > 0.5
    for krum/trimmed_mean, targeted attack. (One-sided sign test over seeds of the
    per-seed median against 0.5.)
M2. On the same received models, Krum's choice under `full` differs from its choice under
    `nonbt` in a nonzero fraction of rounds (counterfactual, logged every round); trimmed
    mean's kept set likewise.
M3. Untargeted MPAF writes (count - noise) x 10 into the attacker's counter, so in the
    `full` arm MPAF clients are far from everyone *through the counter*; with the counter
    masked they are still far through their parameters. Prediction: Krum/trimmed-mean
    exclude MPAF clients in both arms, so Y does not differ for p = untarget.

## Outcome tests
H1 (primary family, 6 tests): Krum, each (c_frac, p): Y_full - Y_nonbt != 0. Exact
two-sided paired sign-flip test over the 10 seeds, Holm across the 6.
H2 (secondary family, 12 tests): the same for trimmed_mean and fang. Holm across the 12.
No direction is registered for Y: Prop. 1 signs the decision change, not whether
selection by batch count helps or hurts accuracy. Effect sizes (mean paired difference,
sign counts) are reported for every cell whether or not significant.
Reported against the paper: we compare the `full` arm's Y with Fig. 3's curves only
qualitatively (the paper gives figures, not tables); the claim we can make is whether the
quantity the paper plots moves under the mask, not that a printed value is wrong.

## Compute and stopping
GPU when CUDA works (one run is minutes); CPU otherwise at <= 2 threads per lane within
the ~12-core budget. Resumable: a run whose JSON has `finished` is skipped. A run that
errors is retried once and then recorded as missing; missing seeds are reported, never
imputed. The analysis (paper/analyse_r2.py, to be written before the campaign's results
are read) applies exactly the tests above.
