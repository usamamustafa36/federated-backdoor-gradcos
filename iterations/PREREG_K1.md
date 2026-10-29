# Pre-registration K1: does the counter-angle proposition predict a reversal at k > 1?

Written 2026-10-24, 01:45-02:40 PKT, by iteration 31, before any cell it tests exists
(`results/kgt_k1/` holds no result JSON at commit time). Committed, together with the runner
(`experiments/k1_reversal/run_k1.sh`), its waiter (`experiments/k1_reversal/wait_k1.sh`), the
analysis script (`paper/analyse_k1.py`) and a SHA-256 manifest of the baseline files it reads
(`iterations/PREREG_K1_manifest.txt`), BEFORE the waiter is started. Not to be edited after
that commit except by dated amendments appended at the bottom, each saying what changed and
which K1 outcomes had been seen.

## Why this exists

Proposition prop:angle (paper, Sec. Mechanisms; proof in the supplement) is an exact identity
for the cosine distance between two transmitted updates d_i = (c_i, e_i), c_i the BatchNorm
counter block, e_i the rest, theta_i the angle of d_i to its counter block:

    1 - cos(d_i, d_j) = [1 - cos(theta_i - theta_j)] + sin(theta_i) sin(theta_j) (1 - rho_ij).

With one angle per group and k = sin(theta_m)/sin(theta_h):
 (a) the attackers' mutual distance relative to honest pairs is k^2 times its content value;
 (b) an attacker's distance to honest clients is (Phi + k (1 - rho_mh)) / (1 - rho_hh) times
     the honest-pair distance, Phi -> (1 - k)^2 / 2.
tan(theta) = |e|/|c|, so tan(theta_m)/tan(theta_h) = t/E, with t the attackers' trainable-norm
ratio and E their batch-count ratio. Every attacked P3 cell has E = 15 and t ~ 3.7-6.6, so
k < 1, and the observed detection effects (P3, IID, attacked; see the table below) have the
k < 1 direction: the counter hides attackers from FLAME and lends FoolsGold detections.
Iteration 30 derived the proposition after those cells ran, so it is post hoc. Its unrun
consequence is that k > 1 reverses both effects. This file registers that prediction with
concrete cells, magnitudes and a test, before any of the cells run.

## What had been seen when this was written (non-blind)

- Every P3 result summarised in `results/postfix_p3/summary_pairs.md` and the per-seed
  last-five-round DR/FPR/BSR, trainable-norm ratio and pair-cosine ratio of the P3 IID
  attacked cells (both arms, seeds 42-46) of FLAME, FoolsGold, FLDetector and GradCos
  (read by this iteration at ~01:50; these are the k < 1 baseline, listed in the manifest).
  k < 1 baseline (mean over seeds 42-46, DR = mean of the last five rounds):

  | rule | DR defect (full) | DR fixed (trainable) | fixed-arm t (median) |
  |---|---|---|---|
  | FLAME | 0.00 | 0.86 | 5.1-6.6 |
  | FoolsGold | 1.00 | 0.00 | 3.7-4.0 |
  | FLDetector | 0.20 | 1.00 | 4.3-4.7 |
  | GradCos | 1.00 | 0.92 | 4.6-5.4 |

- The attacker norm ratio of the iteration-4 pilots (`results/pilot_attack_iter4/`, FedAvg,
  seed 42, attackers at the honest epoch count): t ~ 1.3-1.6 (IID p0.1: 1.58), used only to
  choose the boost below.
- Iteration 30's geometry checks (k^2 law on the P3 cells, the FLAME probe).
- No K1 cell, and no cell with an attacker boost on IID shards in this configuration, exists.
- Nothing from the P3X held-out cells (iterations/PREREG_P3X.md) is read or used here.

## Cells (all new; IID shards only)

Attacked setting exactly as P3 (configs/kgt_{full,trainable}.yaml = configs/p3_*.yaml with
out_dir results/kgt_k1): CICIoT2023, 10 clients, m = 0.2 (2 share-matched attackers),
p = 0.1, fixed trigger, 15 rounds, honest local epochs 1, round-one copy on. Two attacker
settings, each making k > 1 by construction:

| setting | attacker local epochs E_m | boost b (trainable part of the attacker update) | expected t = b * t(E_m) | E | expected k |
|---|---|---|---|---|---|
| KA (primary) | 1 | 4 | ~5-6.5 | 1 | ~4-7 |
| KB | 15 | 10 | ~37-66 | 15 | ~2-5 |

KA keeps the P3 attacker's trainable-norm ratio (~4-6.5 times an honest client's) but gives it
an honest batch count, so only the counter changes; KB is the P3 attacker itself with its
trainable update boosted (`attack.boost`, model-replacement-style scaling of the trainable
coordinates only; BatchNorm buffers, and so the counter, are left as trained).

Rules: FLAME, FoolsGold, FLDetector, GradCos (clique method, as in P3). Arms: defect
(`signal_subspace: full`) and fixed (`trainable`). Seeds 42-46. 2 x 4 x 2 x 5 = 80 cells,
run in the order KA then KB, seed, rule, arm (so pairs complete together).

Metrics, as in the paper: DR and FPR = mean over the last five rounds of
`history.detection_rate` / `history.false_positive_rate`; BSR and CA likewise (descriptive).

## Predictions and tests

Notation: G(r, s) = DR_defect - DR_fixed for rule r, seed s; G_K for setting K, G_P3 for the
P3 cell with the same rule and seed (the k < 1 baseline above). tau(FLAME) = +1,
tau(FoolsGold) = -1.

The proposition makes a sign prediction for FLAME and FoolsGold only:
- FLAME keeps the majority cluster of a cosine-distance clustering and so reads (b). At k > 1,
  Phi ~ (k - 1)^2 / 2 is far above 1 and the attackers are outliers in the full vector,
  whatever their content: the defect arm excludes them at least as often as the fixed arm.
- FoolsGold penalises mutual similarity of histories and so reads (a). At k > 1 the
  attackers' mutual distance is amplified by k^2 relative to honest pairs: in the full vector
  they look less alike than honest pairs and the defect arm stops flagging them.
- GradCos (clique) reads (a) in its clique stage but falls back to a mean-similarity outlier
  test, which reads (b), when no clique is found; FLDetector scores a Euclidean prediction
  error, which the proposition does not describe. No sign is registered for either; both are
  reported descriptively, and both enter M1 (geometry).

**M0 (manipulation check, per setting).** Per (rule, seed) pair,
k_hat = sin(atan((t/E) tan(theta_h))) / sin(theta_h), with t the fixed arm's median over
rounds 2-15 of `mal_norm_ratio` (trainable), tan(theta_h) = sqrt((1 - s)/s), s the defect
arm's median over rounds 2-15 of `buffer_norm_share`, and E = E_m. A setting passes iff the
median k_hat over its pairs (all four rules) exceeds 1. A setting that fails M0 does not test
the prediction and is excluded from H1/H2 (reported as a failed manipulation).

**H1 (primary; reversal relative to k < 1).** Per setting K passing M0:
Delta(r, s) = G_K(r, s) - G_P3(r, s), and T = sum over r in {FLAME, FoolsGold}, s in 42-46 of
tau(r) Delta(r, s) > 0. Exact one-sided paired sign-flip test over the n <= 10 pairs (all 2^n
sign assignments; p = share with T' >= T). Holm over the settings that pass M0 (at most KA, KB)
at alpha = 0.05. Supported for a setting iff its Holm-adjusted p <= 0.05.

**H2 (secondary; reversal within k > 1).** Pooled over the settings passing M0 (one test, no
correction): T2 = sum tau(r) G_K(r, s) > 0 over their FLAME and FoolsGold pairs (n <= 20); same
exact sign-flip test; supported iff p <= 0.05. H2 says whether the counter now acts in the
opposite direction, not just less in the old one. (Pooled because FoolsGold's fixed arm is
expected at DR 0, so its pairs may tie at G = 0 and carry no sign; with five informative pairs
per setting a Holm-corrected per-setting test could not reach 0.05.)

**Magnitude (registered expectations, descriptive, per setting):** FLAME mean DR_defect >= 0.9
(k < 1: 0.00); FoolsGold mean DR_defect <= 0.1 (k < 1: 1.00).

**M1 (geometry, secondary).** Per (rule, seed, setting) pair with both arms:
Q_obs = [defect arm's median over rounds 2-15 of (1 - mal_pair_cos)/(1 - honest_pair_cos)] /
[the fixed arm's], Q_pred = k_hat^2. Supported iff, pooled over all pairs, the median of
Q_obs/Q_pred lies in [0.5, 2] AND Q_obs > 1 in at least 80% of pairs. (Every IID P3 pair had
Q_obs < 1; Q_obs > 1 is the out-of-sample sign of the k^2 law.)

Descriptive only: per-cell DR/FPR/BSR/CA of all four rules, both arms; k_hat per setting.

## Missing data

A pair counts only if both arms' JSONs exist, are non-empty and hold 15 rounds of history.
Results are labelled interim until all 80 cells exist. If a setting cannot finish (GPU loss),
whatever pairs exist are analysed as registered and the count is reported.

## Interpretation and paper wording, committed now

- M0 fails for a setting: "Setting K did not produce k > 1 (median k_hat = x); it does not
  test the prediction."
- H1 supported (Holm) for at least one setting: "Registered before the cells ran, the
  proposition's k > 1 prediction held: with the attackers' trainable update large relative to
  their batch count (median k_hat = x), the counter's effect on detection reversed (FLAME's
  defect arm excluded the attackers, DR a against b at k < 1; FoolsGold's no longer did, DR c
  against d; n pairs, p after Holm)." The paper may then call the direction of the FLAME and
  FoolsGold detection effects a confirmed prediction of Proposition prop:angle for the
  settings tested, and no more.
- H1 not supported for any setting: "The registered k > 1 prediction failed (n pairs, p): the
  proposition describes the geometry [M1 result] but does not predict which rules detect; the
  detection effects remain observations of the E_m = 15 attacker." Any sentence calling the
  proposition predictive of detection goes.
- H2 supported as well: "...and reversed in sign: at k > 1 the counter exposes attackers to
  FLAME and hides them from FoolsGold." H2 not supported while H1 is: "the effect weakened or
  vanished but did not reverse in sign."
- M1 supported: "the k^2 law predicted the attackers' mutual-distance ratio out of sample
  (median observed/predicted x, n pairs, Q_obs > 1 in y)". Not supported: say so and give the
  numbers.
- A security reading registered now: KA is a standard model-replacement boost with an honest
  counter. If H1 holds, a rule's verdict on that attacker depends on whether the operator masks
  the counter, in the opposite direction to the E_m = 15 attacker.

## Code

`paper/analyse_k1.py` computes M0, H1, H2, M1 and the descriptives from results/kgt_k1 and the
P3 baseline cells and writes `paper/numbers_k1.tex` (\koHOneP..., \PENDING while cells are
missing). `experiments/k1_reversal/run_k1.sh` runs the cells on CUDA, one run_sweep call per
(setting, seed, rule, arm), resumable (finished JSONs are skipped), checking GPU memory, RAM
and load before each cell. `experiments/k1_reversal/wait_k1.sh` starts it only after the R1 GPU
helper (run_r1_reverse.sh) has exited.

## Amendment 1 (2026-10-24, ~03:05 PKT; clerical)

The header's "01:45-02:40" was the planned writing window; the file was committed at 01:54:36
(commit e7d1345), before the waiter was started (01:54:44). No design, test or wording changed.
No K1 cell existed when this amendment was written.

## Amendment 2 (2026-10-29, iteration 33): device. No cell, sign, test or wording changes.

The machine rebooted on 2026-10-28 and CUDA came back in the unusable state (`CUDA unknown
error`; recovery needs the module reload, which needs the owner's password). 26 of the 80 K1
cells had finished on the GPU. The runner was restarted on 2026-10-28 23:04 with
`DEVICE=cpu LANES=1 THREADS=2`; it skips finished cells, so the remaining cells run on the CPU.
The two devices are reproductions, not bit-identical copies (as for P3 and R1, PREREG_R1
Amendment 2). Pairs are formed within (rule, seed, setting) as registered; the device of each
cell is recorded in its log. **Outcomes seen:** none. `paper/analyse_k1.py` was run by
`make numbers` and printed only the cell count (26/80); no K1 JSON was opened.

## Amendment 3 (2026-10-29 19:15 PKT, after iteration 33): device. No cell, sign, test or wording changes.

At the owner's request the local CPU is freed: the K1 runner was stopped at 18:57 (44/80 cells on
disk; the cell in progress, KB full fldetector s42, had no JSON and was discarded). The 36
remaining cells (all KB) run on Kaggle (kernel usamaa36/paper08-p3k1-kaggle, 2x Tesla T4,
`--device cuda`, code tarball of src/ experiments/ configs/ at acb1a9e, dataset
usamaa36/paper08-p3k1-code; data/ciciot2023 parquet files unchanged, usamaa36/paper08-ciciot2023),
with run_cell's command line. The JSONs are copied back into results/kgt_k1 unchanged. Pairs are formed within
(rule, seed, setting) as registered. KB pairs whose full arm ran locally and whose trainable
arm runs on Kaggle: none (both arms of every pending pair are pending). Devices are reproductions,
not bit-identical copies (Amendment 2). **Outcomes seen:** none; only file existence was checked.
