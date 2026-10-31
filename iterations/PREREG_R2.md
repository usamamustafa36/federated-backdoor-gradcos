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

## Amendment 1 (2026-10-23 15:40 PKT, iteration 27): run count. No design change.

- **Arithmetic slip.** The Seeds paragraph says "+ 120 `trainable` runs (krum only)" and
  so implies 490 runs. The registered grid gives 3 c_frac x 2 p x 10 seeds = **60**
  `trainable` runs (krum only), so the campaign is 360 + 10 fedavg + 60 = **430 runs**.
  experiments/r2_exposed/run_r2.sh (committed with iteration 25, before any outcome)
  already generates exactly these 430 jobs (results/r2_exposed/jobs.txt); nothing about
  the arms, cells, tests or analysis changes. The sentence above is left as written and
  is superseded by this amendment.
- **Outcomes seen before this amendment** (none from the campaign; no campaign run has
  completed): the one-round plumbing run results/r2_exposed/plumb_krum_target_nonbt_le1_s3.json
  (iteration 26; `--local_ep 1`, not the authors' setting, so not a campaign cell): round-0
  counter_share_dist 0.168, Krum's choice 2 / 9 / 6 under full / nonbt / trainable. It is
  excluded from every test, as the smoke run is.
- **Device/timing.** R2 cannot share the GPU with R1's three lanes (iteration 26: one run
  did not finish a round in 10+ min); it is queued behind R1
  (experiments/r2_exposed/wait_r1_then_r2.sh). On CPU one round with `--local_ep 1` took
  about 11 min (plumbing run), so the authors' `local_ep 5` grid is GPU-only. Device does
  not change any test.

## Amendment 2 (2026-10-29 18:45 PKT, after iteration 33): second device. No design change.

- **Why.** The local GPU runs about 1.5 R2 runs per hour (3 lanes), so the 430-run grid would
  take about 12 days. The owner authorised Kaggle (2026-10-29).
- **Split, by whole seed.** The H1 runs (krum, `full` and `nonbt`, all c_frac x p) for seeds
  **9, 10, 11, 12** (48 runs) run on Kaggle (2x Tesla T4, kernel usamaa36/paper08-r2-kaggle,
  dataset usamaa36/paper08-r2-byzfl: run_byzfl.py and _ext/byzantineFL at acb1a9e, unchanged, plus
  data/medmnist/bloodmnist.npz). Same harness, same flags as run_r2.sh's run_one, and the same
  "complete" rule; the device is recorded in each kernel log. Every registered pair
  (full vs nonbt, same cell and seed) therefore runs on one device. Seeds 3-8 stay on the local
  GPU; results/r2_exposed/remote_jobs.txt lists the Kaggle jobs, and run_r2.sh skips them.
  Kaggle JSONs are copied into results/r2_exposed unchanged. Devices are reproductions, not
  bit-identical copies (as for P3/R1/K1). The remaining jobs (krum trainable, H2, fedavg) may be
  sent the same way, by whole seed, and logged in the ledger.
- **Outcomes seen:** none. analyse_r2.py last ran in iteration 33 (5 complete runs, every
  macro \PENDING). Since the relaunch only the "complete" flags and error strings of the JSONs
  have been read (15 complete), never a metric.

## Amendment 3 (2026-10-29 ~23:00 PKT, iteration 34): blinding guard. No design change.

`make numbers` (iteration 34) ran paper/analyse_r2.py over the 22 complete full/nonbt runs then on
disk; it wrote interim per-cell values into paper/numbers_r2.tex and results/r2_exposed/summary.json
and printed them into a build log. None of these was read: numbers_r2.tex was restored from git
(all \PENDING), and summary.json and the build log were deleted unread. To stop a routine rebuild
from unblinding R2, analyse_r2.py now scores a family only when all of its full/nonbt runs are
complete (H1 120, H2 240; `--final` overrides, for a write-up after a stopped campaign under the
registered missing-data rule). Until then it reports only run counts. Tests, cells and arms are
unchanged. **Outcomes seen:** none.

## Amendment 4 (2026-10-29 ~23:45 PKT, iteration 34): one duplicate run. No design change.

The Kaggle session (Amendment 2) completed all 48 seed-9-12 H1 runs in 3.8 h. One of them,
krum untarget c0.3 full s11, also existed as a complete local run (2026-10-24, first campaign); its
nonbt partner existed only from Kaggle. By Amendment 2's rule (both arms of a pair on one device)
the Kaggle run is used; the local one is kept, unread, in results/r2_exposed/superseded/ and is not
analysed. **Outcomes seen:** none (completeness flags only).

## Amendment 5 (2026-10-29 ~23:55 PKT, iteration 34): second Kaggle batch. No design change.

Kaggle ran ~12.6 runs/h against ~1.5 locally, so more of the grid moves there, again by whole seed
per family: H1 seeds 6, 7, 8; H2 (trimmed_mean, fang; full and nonbt) seeds 9-12; every krum
`trainable` run (reported, not tested); the 10 fedavg runs. 200 runs not yet complete
(kernel usamaa36/paper08-r2-kaggle v2, list in experiments/kaggle/paper08-r2-kaggle.py); runs it does
not finish within a session are re-sent in the next one. results/r2_exposed/remote_jobs.txt (250 lines)
lists every Kaggle job and run_r2.sh skips them; the local GPU keeps H1 seeds 3-5 and H2 seeds 3-8.
Every registered pair stays on one device. **Outcomes seen:** none.

## Amendment 6 (2026-10-30 ~13:30 PKT, iteration 35): the rest of the grid on Kaggle. No design change.

The local runner died at a reboot (~08:50); the owner asked for the rest to run on the Kaggle GPU. The
v2 session (Amendment 5) hit its 10.3 h launch limit with 124/200 complete (0 non-zero exits); those 124
JSONs were copied in unchanged, with no clashes (15 per-run logs could not be downloaded from Kaggle;
the kernel log has their start/end lines). Kernel v3 (experiments/kaggle/paper08-r2-kaggle.py) gets every
run not yet complete, 216: the remaining H2 pairs of seeds 3-8 and the 7 open seed-9 runs (registered
pairs first, seed-major), then the 9 fedavg and 60 krum `trainable` runs. One local pair was half done
(trimmed_mean target c0.2 s3: full complete, nonbt cut by the reboot); by the same-device pair rule
(Amendments 2, 4) both arms go to Kaggle and the local full run is kept unread in
results/r2_exposed/superseded/. The local GPU runs nothing more; remote_jobs.txt lists all 390 Kaggle jobs.
Runs a session does not finish are re-sent in the next one.
**Outcomes seen:** H1 reached 120/120 with these copies and was scored by analyse_r2.py under
Amendment 3's rule (H1 supported in 3 of 6 cells). That does not bear on this amendment, which moves only
H2 and unregistered runs between devices. H2: none (completeness flags only).

## Amendment 7 (2026-10-31, iteration 38): the last 19 `trainable` runs on the local GPU. No design change.

The Kaggle GPU quota (6 h a week) ran out at the v5 session with 19 krum `trainable` runs open; the next reset is 2026-11-07. Amendment 6 said the local GPU runs nothing more; this amendment reverses that for these 19 runs only, at the owner's request to finish now. They are listed in results/r2_exposed/local_jobs_am7.txt and run through the same harness and code. `trainable` is reported, not tested, and has no pair rule, so no registered test changes.
**Outcomes seen:** H1 and H2 complete and scored (3/6 and 6/12). `trainable`: completeness flags only; no `trainable` outcome has been read.
