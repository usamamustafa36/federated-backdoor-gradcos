# Pre-registration P3X: do the exploratory detection effects of P3 replicate on held-out seeds?

Written 2026-10-23, 15:40-16:05 PKT, by iteration 28, before any of the cells it tests exist.
Committed before the runner that produces them (experiments/postfix/run_p3_tail.sh) is
started, together with a SHA-256 manifest of every P3 result file then on disk
(`iterations/PREREG_P3X_manifest.txt`). Not to be edited after that commit except by dated
amendments appended at the bottom, each saying what changed and which outcomes had been
seen.

## Why this exists

P3's registered family (PREREG_P3.md) covers FLTrust exclusions and NormClip/FLAME clean
accuracy. Its exploratory cells show something the registered family does not: in attacked
runs the counter changes *whether* several rules catch the attackers, in both directions.
At the time of writing (P3 at 751/1040 cells, `results/postfix_p3/summary_pairs.md` of
15:3x, 2026-10-23), exploratory paired DR (fixed - defect), attacked runs:

| rule | part | n | defect DR | fixed DR | signs (+/-) |
|---|---|---|---|---|---|
| FLAME | IID | 10 | 0.000 | 0.860 | 10/0 (FPR 0.485 -> 0.267, 0/10) |
| FLDetector | IID | 10 | 0.200 | 1.000 | 10/0 |
| FLAME | Dirichlet | 5 (s47-51) | 0.000 | 0.300 | 5/0 |
| FLDetector | Dirichlet | 5 (s42-46) | 0.280 | 0.800 | 4/1 |
| AlignIns | Dirichlet | 5 (s42-46) | 0.080 | 0.680 | 5/0 |
| AlignIns | IID | 5 (s47-51) | 1.000 | 0.820 | 0/5 |
| FoolsGold | IID | 5 (s42-46) | 1.000 | 0.000 | 0/5 (BSR 0.013 -> 0.973, 5/0) |

These were found by looking, not predicted, so they are exploratory. The IID FLAME and
FLDetector cells are complete and cannot be tested blind. The others have seeds that have
not run. This file registers, before those seeds run, that the direction seen on the run
seeds will hold on the held-out ones.

## What had been seen (non-blind) when this was written

- Every pair summarised in `results/postfix_p3/summary_pairs.md` at 15:3x (all rules,
  both partitions, clean and attacked); every earlier agent had the same summaries.
- Per-seed last-five-round DR/FPR/BSR of FLAME, FLDetector and FoolsGold attacked runs, both
  arms, every seed on disk (read by this iteration at ~15:45), including the **fixed arm of
  FLAME Dirichlet s42-46**, whose defect arm has not run. FLAME Dirichlet s42-46 is therefore
  partly unblinded and is NOT in the test below (reported descriptively).
- Every result file in the manifest counts as seen.

## Held-out cells (both arms absent from disk at commit time)

| id | rule | partition | seeds | predicted sign of DR(fixed) - DR(defect) |
|---|---|---|---|---|
| h1 | FLDetector | Dirichlet | 47-51 | + |
| h2 | AlignIns | Dirichlet | 47-51 | + |
| h3 | AlignIns | IID | 43-46 | - |
| h4 | FoolsGold | IID | 47-51 | - |

19 paired seeds. AlignIns IID s42 is excluded (its defect-arm file exists; not read).
Attacked setting exactly as in P3 (configs/p3_{full,trainable}.yaml, m=0.2, p=0.1, fixed
trigger, share-matched attackers, E_m=15, 15 rounds). Metrics as in the paper: mean over
the last five rounds of `history.detection_rate` and `history.false_positive_rate`.

## Hypotheses and tests

- **X1 (primary).** Pooled over h1-h4, with sigma_k = +1 for h1, h2 and -1 for h3, h4:
  T = sum_k sigma_k [DR_fix(k) - DR_def(k)] > 0. Exact one-sided paired sign-flip test over
  the pairs (all 2^n sign assignments; n <= 19). Supported iff p <= 0.05.
- **X2 (secondary).** The same with Youden's J = DR - FPR in place of DR (so that a change in
  DR bought by excluding everyone does not count). Supported iff p <= 0.05. X1 and X2 are not
  Holm-combined: X1 is the claim; X2 says whether it is detection or blanket exclusion.
- **X3 (registered direction, descriptive).** FoolsGold IID s47-51, attacked BSR:
  fixed > defect (the counter makes FoolsGold catch the attackers it otherwise lets implant).
  Reported as means and sign count; n = 5 cannot carry a test after X1/X2.
- Per-cell means and sign counts for h1-h4 are reported, never tested one by one.

## Interpretation committed now

- X1 supported: "On seeds held out when the direction was recorded, removing the counter from
  the decision vector moved detection rates in the recorded direction (n pairs, p)." The
  paper may then say the counter changes whether some rules detect, in both directions,
  citing X1, and keep the IID FLAME/FLDetector cells labelled exploratory.
- X1 not supported: the paper says the exploratory detection effects did not replicate on
  held-out seeds and states the registered FLTrust family as the only confirmed effect.
- X2 not supported while X1 is: the paper says the change is in exclusion rates, not in
  detection quality.
- Missing data: a pair counts only if both arms' JSONs exist, are non-empty and hold 15 rounds
  of history (run_sweep writes a JSON only for a cell that finished). The result is labelled
  interim until all 19 pairs exist.

## Code

`paper/analyse_p3x.py` (committed with this file) computes X1-X3 from results/postfix_p3 and
writes `paper/numbers_p3x.tex` (\pxXOneP, \pxXOneN, \pxXOneSup, ...). The P3 cells run in the
order of `results/postfix_p3/jobs_tail.txt` (held-out cells first).
