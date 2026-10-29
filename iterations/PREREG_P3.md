# Pre-registration: confirmatory hypotheses for the P3 controlled A/B

Written 2026-10-21, 19:10-19:40 PKT, by iteration 14, while P3 (results/postfix_p3,
1,040 cells) was about 69 cells in. Committed in the same commit as the code that
evaluates it (paper/analyse_postfix.py, `--prereg`). It is not to be edited after that
commit except to append dated amendments at the bottom, each saying what changed and
which outcomes the author had seen when making it.

## Why this exists

With 10 paired seeds the exact two-sided sign-flip test cannot go below p = 2^-9 =
0.0020, and Holm over the 13 rules of a (partition, attack, metric) family then needs
almost perfect sign consistency (iteration 13). Most of the 13 x 2 x 2 x 5 comparisons
have no prediction behind them. Testing all of them with equal standing spends the
error budget on questions nobody asked. This file restricts the confirmatory claims to
the comparisons the paper's theory (Prop. 1, Cor. 1-4, Lemma 1, Eq. (norm)) predicts
with a sign, before those cells are complete. Everything else the campaign measures is
exploratory and is reported as such.

## What was already visible when this was written (non-blind)

Every P3 result file on disk at commit time is listed with its SHA-256 in
`iterations/PREREG_P3_manifest.txt`; all of them count as seen, whether or not anyone
read them. From the ledger (iterations 10-13), these P3 summaries had actually been
read by earlier agents and appear in the manuscript:

- FLTrust, Dirichlet, clean and attacked, seeds 42-46: FPR (clean) 0.000 defect vs
  0.716 fixed, 5/5 seeds fixed > defect; attacked DR 0.000 vs 0.525, FPR 0.000 vs 0.631.
- FLAME, Dirichlet, clean, seeds 42-46: exclusions and CA indistinguishable between arms.
- FedAvg, Dirichlet, clean (4 paired seeds; arms agree) and attacked (fixed arm only,
  seeds 43-46; read for the implant set).
- Krum, Dirichlet (clean s42-45 defect arm, s42 fixed arm; attacked s42-43 defect arm,
  s42 fixed arm) and AlignIns IID clean (fixed arm) were on disk but not summarised
  (no paired seeds yet). They are in the manifest; no hypothesis below uses them.
- FoolsGold, Dirichlet, clean, seeds 42-44: both arms exclude most clients.
- The Corollary 3 counter-share log (q_0, q_i, bound) of the defect-arm FLTrust runs.

No IID cell of FLTrust, FLAME or NormClip, and no NormClip cell at all, existed when
this was written. Hypotheses on those cells are **blind**. Hypotheses on Dirichlet cells
whose seeds 42-46 were read are **partly unblinded** (5 of 10 seeds seen); their
direction was predicted in the manuscript (Cor. 3, iteration 10) before P3's FLTrust
cells ran, but the observation of seeds 42-46 is part of why we are confident in them,
and the report says so.

## Theory to prediction

1. **Cor. 3 (FLTrust).** Whenever q_i + q_0 > 1 the defect arm gives client i a
   positive trust score whatever its trainable update, so it excludes no one. The fixed
   arm reads the trainable cosine and excludes whichever clients point away from the
   root update. Prediction: the defect arm's exclusion rates are lower, on honest
   clients (FPR) and on malicious ones (DR), in both partitions (the corollary does not
   depend on the partition). The size of the effect is whatever the fixed arm excludes;
   if the fixed arm excludes no one in a partition, the hypothesis fails there, and we
   report that.
2. **Eq. (norm) (noise scale of NormClip and FLAME).** Both rules set the Gaussian
   noise scale to lambda * S with S the median update norm, and add the noise to the
   trainable coordinates in both arms. In the defect arm S is the full-vector norm, which
   Eq. (norm) inflates by 1/sqrt(1 - s) (about 8x at the measured buffer share; the macro
   \pfDiagNormInflDir), in both partitions, because the counter dominates every update.
   Larger noise on the same trainable coordinates predicts lower clean accuracy in the
   defect arm. This prediction is weaker than (1): the defect arm also clips less (its
   clip factor min(1, S/||d_i||) tracks batch counts, and in IID clean runs it clips no
   one), which pushes the other way, and FLAME's clean Dirichlet CA was already seen to
   be indistinguishable between arms. It is registered as a secondary family so that it
   cannot dilute the primary one.

## What the theory does NOT predict with a sign (exploratory by design)

- **Krum, Bulyan, RFA.** Cor. 2 says they read the counter iff batch counts differ.
  Under Dirichlet partitions they do. **Correction made while writing this:** in
  *attacked* runs they differ in every partition, because the attackers train E_m = 15
  local epochs and so report a counter about 15x an honest client's (the engine counts
  every forward pass; `src/fl/engine.py::_client_fit`). The paper's statement that the
  IID runs are the distance rules' null holds only for **clean** IID runs. Under attack,
  the defect arm hands these rules a batch-count outlier signal; but the attackers'
  trainable updates are also ~16-50x the honest median norm in the FedAvg calibration
  runs (results/calib_iter6, me15, median per seed 15.9-49.9), so both arms are expected
  to see them as outliers, and no sign of the DR/BSR difference is predicted.
- **FLAME's clustering, FoolsGold, GradCos.** Cor. 1 and Lemma 1 say their input is
  compressed; whether the decision moves, and which way, depends on how the rule
  normalises (FLAME's ordering argument; FoolsGold's logit). No sign predicted.
- **AlignIns.** The TDA filter is predicted to select by batch count under unequal
  shards; this is a statement about which clients are kept, not about a reported metric.
- **FLDetector.** Not covered by the decomposition.
- **BSR of every rule.** No rule's BSR difference has a predicted sign: the counter
  changes both which clients are admitted and how they are scaled (Cor. 3's B_0/B_i
  rescaling shrinks a 15-epoch attacker's step), and these interact.
- **Negative controls** (FedAvg, median, trimmed mean): arms run the same computation.
  Their differences are reported as the nondeterminism floor, not tested as hypotheses.

## Analysis plan

- Unit: per-seed paired difference d = fixed - defect of the metric's last-5-round mean
  (as in analyse_postfix.py). All seeds 42-51 present in both arms are used; DR, FPR and
  CA are not subject to the implant filter (that applies to attacked BSR only).
- Test: exact **one-sided** paired sign-flip permutation test in the predicted direction
  (p = share of the 2^n sign vectors whose signed sum is at least the observed one).
  One-sided because the direction is registered here. Floor 2^-n (0.00098 at n = 10).
- Multiplicity: Holm within each family. Primary family: P1-P4 (alpha 0.05). Secondary
  family: S1-S4 (alpha 0.05, separately). A hypothesis is "supported" iff its Holm p
  <= 0.05. Sensitivity: Holm over the blind hypotheses of each family alone is reported
  too. Holm always uses the registered family size: an untested hypothesis enters with
  p = 1, so an interim result is never corrected for fewer tests than the final one.
- Reporting: every hypothesis is reported, supported or not, with n, the sign counts,
  the mean difference and the one-sided p. The paper states which are partly unblinded.
- Timing: the confirmatory result is the one computed when every cell of the eight
  hypotheses has n = 10 (or the campaign is declared finished with fewer; then the
  achieved n is reported and nothing is re-run to rescue a hypothesis). Interim values
  printed before that are labelled interim in the manuscript.
- The two-sided analysis over all 13 rules (iteration 13) stays, relabelled exploratory.

## Hypotheses (machine-readable; parsed by paper/analyse_postfix.py)

Format: id | family | defense | partition | attack (0/1) | metric | direction (+ means
fixed > defect) | blind (yes / partial) | source

```prereg
P1 | primary   | fltrust  | dirichlet | 0 | FPR | + | partial | Cor. 3
P2 | primary   | fltrust  | iid       | 0 | FPR | + | yes     | Cor. 3
P3 | primary   | fltrust  | dirichlet | 1 | DR  | + | partial | Cor. 3
P4 | primary   | fltrust  | iid       | 1 | DR  | + | yes     | Cor. 3
S1 | secondary | normclip | dirichlet | 0 | CA  | + | yes     | Eq. (norm), noise scale
S2 | secondary | normclip | iid       | 0 | CA  | + | yes     | Eq. (norm), noise scale
S3 | secondary | flame    | dirichlet | 0 | CA  | + | partial | Eq. (norm), noise scale
S4 | secondary | flame    | iid       | 0 | CA  | + | yes     | Eq. (norm), noise scale
```

## Amendments

### Amendment 1 -- 2026-10-22, iteration 21 (interpretation only; no test changed)

**Seen when written:** every P3 result file on disk (480 of 1,040 cells), including
P1-P4 at n = 5 (each 5+/0-, one-sided p = 0.031, Holm 0.125, not supported), S2 final
(not supported), and the fixed-arm FLTrust IID "shutdown" reported by iteration 20
(all 10/10 fixed-arm IID runs, clean and attacked, give every client zero trust from
round 6-15 on; Dirichlet 2/10).

**What was found:** a CPU replay of two clean IID cells (experiments/fltrust_shutdown/,
results/fltrust_shutdown/replay_*.json) reproduces the shutdown in the same rounds.
It is not a code bug and not a vanishing root update. The server's root set is
class-balanced (disclosed in the paper, but not what Cao et al. assume); once the
global model fits the majority classes, the balanced root update points against every
IID client's update (cosines -0.38 to -0.13; a second balanced draw agrees), while a
root of the same size drawn from the training distribution would give every client
+0.64 to +0.81. With all trust zero the implementation keeps the global model, so the
shutdown is absorbing.

**Consequence for the registered hypotheses.** P2 (IID FPR) and P4 (IID DR) predict
that the fixed arm excludes more than the defect arm. Under the shutdown it excludes
everyone, so the predicted sign is met for a reason the registration did not
anticipate (the registration foresaw only the opposite degenerate case, "the fixed
arm excludes no one"). **Nothing in the analysis plan changes**: same tests, families,
Holm correction, n = 10 timing; P2/P4 are not dropped, re-scored or replaced, because
doing so after seeing the outcome would be the very flexibility this file exists to
prevent. What changes is the reporting rule:
1. If P2 or P4 is supported, the paper states that it confirms Corollary 3's literal
   prediction (the fixed arm reads the trainable cosine and excludes clients that
   point away from the root update) and NOT that the fixed arm detects attackers; it
   must not be cited as detection evidence.
2. Beside P1-P4 the paper reports, per arm and partition, how many runs end in total
   exclusion (macros \csFltShut*, paper/make_numbers_calib6.py), so a reader can see
   how much of P1/P3 (Dirichlet) is also shutdown (2/10 runs at this writing).
3. Runs with a training-distribution root (configs/fltrust_natroot.yaml,
   defense.fltrust_root: natural; results/fltrust_shutdown/natroot_*) are exploratory,
   outside both families, and cannot rescue or replace any registered hypothesis.


### Amendment 2 -- 2026-10-29 19:15 PKT, after iteration 33 (device only; no test changed)

**Seen when written:** nothing new; only file existence of the tail cells was checked (70 of the
289 tail jobs on disk). The P3 tail (results/postfix_p3/jobs_tail.txt, CPU since iteration 28)
was stopped at 18:57 at the owner's request (local CPU freed); its 219 pending jobs run on Kaggle
(kernel usamaa36/paper08-p3k1-kaggle, 2x Tesla T4, `--device cuda`, the command of run_p3.sh
run_job with MAL_EPOCHS=15) and the JSONs are copied back into results/postfix_p3 unchanged. The
P3 cells were registered on the GPU; the device of each cell is in its log. Reproductions, not
bit-identical copies.
