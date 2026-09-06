# Is this publishable at 2027 standards?

Assessment of 5 September 2026, written while the post-fix campaign was being prepared.
Every number below was measured in this session, not estimated. Where I got something
wrong earlier in the session I say so rather than quietly restating it.

**Short answer: not yet.** Four blockers, three of them fixable with work that is already
scoped. None of them is fatal to the research idea, which is good; the idea is the
strongest thing here.

---

## B1. The detector is weak, and the paper never says how weak

Reported: CA 0.703, macro-F1 0.564 (5 seeds, CICIoT2023 8-class).

The number that matters and is missing from the paper: **the majority-class floor is
0.652.** DDoS alone is 64.7% of the training set. A classifier that always answers "DDoS"
scores 0.652. The paper's detector scores 0.703 — **+0.066 over answering with a constant.**

Nowhere does the paper give the reader that floor. A reviewer who computes it will conclude
the detector barely works, and every downstream claim about update geometry inherits that
doubt.

### Diagnosis, by elimination

| setup | CA | macro-F1 |
|---|---|---|
| majority-class floor | 0.652 | — |
| federated CNN+LSTM, 100 rounds (the paper) | 0.703 | 0.564 |
| centralized CNN+LSTM, same data and loss | 0.720-0.751 (oscillating) | 0.619-0.635 |
| MLP, no sequence assumption | ~0.731 | ~0.612 |
| RandomForest, same 39 features | **0.786** | **0.650** |

What this rules in and out:

- **Not federated learning.** Centralized training of the same model lands in the same
  band. FL is not costing much here.
- **Not mainly the architecture.** I said earlier in this session that the CNN+LSTM was
  likely the cause, because it treats 39 unordered tabular columns as a length-39 sequence
  (`Conv1d(kernel=3)` convolving unrelated adjacent columns, an LSTM over feature indices,
  and `h_n[-1]` discarding all but the final state, which makes the classifier's view
  depend on arbitrary column order). That criticism is still valid on its own terms and a
  reviewer may raise it. But **it is not what is costing the accuracy**: a plain MLP with
  no sequence assumption reaches ~0.731, essentially the same. I was wrong to lead with it.
- **Partly the training budget.** The federated run plateaus by round 10 and gains
  **+0.0136 across the remaining 90 rounds**. Centralized training with more effective
  epochs reaches 0.751. The federated configuration (100 rounds x 1 local epoch) is
  undertraining the model.
- **Partly the loss.** Every neural run oscillates in a 0.60-0.75 band while RandomForest
  sits stable at 0.786. Inverse-frequency class weighting on a 121x imbalance gives
  BruteForce ~24x DDoS's weight; a 256-row batch holds ~1.4 BruteForce rows, so a couple of
  rare-class samples dominate each gradient step. (A comparison of four weighting schemes
  was running when this was written; see `results/` for the outcome.)
- **Partly the task.** RandomForest -- a strong, stable tabular baseline -- only reaches
  0.786 itself. Its per-class report shows why: **DoS sits at F1 0.51** (precision 0.52,
  recall 0.50) and is being confused with DDoS. Those two classes are 85% of the test set.
  The 8-class grouping merges attack families whose flow signatures genuinely overlap.

### Why "but the literature reports 0.99 on CICIoT2023" is not the objection it looks like

Those results are binary (attack vs benign) or 34-class with the DDoS subtypes kept
separate, and several have duplicate-row leakage between train and test. They are not
measuring this task. **The paper should say so explicitly and show the RandomForest
baseline**, so 0.786 reads as the task ceiling rather than 0.703 reading as incompetence.

### The loss is the biggest single lever, and it is a one-line change

Measured (centralized, 200k rows, batch 512, 15 epochs, same architecture):

| class weighting | CA | macro-F1 | CA swing over last 10 epochs |
|---|---|---|---|
| **none** | **0.8068** | 0.5606 | **0.0088** |
| inverse frequency (what the paper uses) | see federated 0.703 / 0.564 | | wild |

Dropping the inverse-frequency weighting takes accuracy from **0.703 to 0.807** — past
RandomForest's 0.786 — while macro-F1 is unchanged (0.561 vs 0.564), and the oscillation
that made every neural run bounce through a 0.15-wide band collapses to a 0.0088 swing.

The weighting was buying nothing. On a 121x imbalance it hands BruteForce ~24x DDoS's
weight, so a 256-row batch containing about 1.4 BruteForce rows has its gradient set by
those rows. The result was a model that traded away majority-class accuracy and did not
gain minority-class F1 for it.

This single change moves the detector from "+0.066 over a constant classifier" to
"+0.155 over a constant classifier, and better than a tuned RandomForest on the same
features". It removes B1 as a rejection risk almost by itself.

Two caveats before adopting it: this is centralized, and it uses batch 512 rather than the
configured 256, so both need confirming in the federated setting. Whether a gentler scheme
(sqrt-inverse, effective-number) recovers macro-F1 without giving the accuracy back was
still running when this was written.

### Fix

0. **Drop or soften the class weighting** — the largest and cheapest win available.
1. Raise the training budget (more local epochs, or more rounds) -- the model is still
   improving when the run stops.
2. Use a gentler class-weighting scheme if the comparison confirms it stabilises training.
3. **Report the majority-class floor and a RandomForest baseline in the paper.** This is
   the cheapest and highest-value change here: it converts an unexplained weak number into
   a characterised task difficulty.
4. Either justify the CNN+LSTM or note the MLP result. Do not leave the sequence-over-
   tabular-columns choice unaddressed.

---

## B2. The newest defense evaluated is from 2022

Evaluated: FedAvg (2017), Krum (2017), coordinate median / trimmed mean (2018), Bulyan
(2018), norm-clip (2019), FoolsGold (2020), FLTrust (2021), RFA (2022), FLAME (2022).

Cited but never evaluated: DeepSight (2022), FLDetector (2022), CRFL (2021), 3DFed (2023),
Yang et al. (2024), Fang et al. (2025), SecFedNIDS (2022), Merzouk et al. (2023), WeiDetect
(2025).

For a 2027 submission that evaluates nothing from 2023-2026, "no comparison against the
state of the art" is a standard rejection line, and the bibliography makes it worse: the
paper demonstrably knows about the recent work and still does not test against it.

**Fix:** implement FLDetector (cross-round update consistency -- and notably outside the
paper's own direction/magnitude taxonomy, which the Discussion already concedes) and at
least one 2024-25 defense as evaluated baselines.

---

## B3. The batch-counter bug (fixed, re-run pending)

See `QA_FINDINGS.md` F1/F11/F13/F17/F20. Every similarity, distance, norm, clip threshold
and DP noise scale was computed over a vector that is 98.1% one BatchNorm batch counter.
Fixed and verified (33/33 smoke cells, zero errors; salience gap 4.2e-5 -> 0.465). All 321
committed result files are void and the campaign restarts from zero.

---

## B4. The headline claim is contradicted by the paper's own data

Krum under the evasion: BSR 0.948 -> **0.001**, DR 0.18 -> **1.00**, FPR 0.20 -> **0.00**.
The evasion repairs Krum rather than defeating it, and it does so even when the attacker
successfully norm-matches (ratio 0.99). The abstract says every direction-based rule falls.

This one is an opportunity rather than a defect. The mechanism -- cosine rules are blinded
by a shared constant while distance rules are alerted by it -- is a sharper and more
interesting claim than "these defenses fail". But it has to be re-measured after B3 and the
paper rewritten around it.

---

## What is genuinely strong, and should not be lost in the rewrite

- The generator discipline: no number typed by hand, a gate that fails loudly, `\PENDING`
  markers that cannot be forgotten. Most submitted papers cannot make this claim.
- Reporting FPR beside DR, and the finding that it changes what two established baselines
  look like.
- The realizability audit. Marginal sigma saying nothing about joint plausibility is a real
  contribution, and the paper is honest that it corrects its own earlier premise.
- The willingness to report the proposed method's failures. Keep this; it is the paper's
  distinguishing quality and reviewers respond well to it.

---

## Recommended order

1. Settle the detector configuration (B1) -- budget, weighting, and the baselines to report.
2. Add the missing defenses (B2).
3. **Then** launch the full re-run once, with the fixed signal path, the better detector and
   the fuller defense set, so the campaign is not spent twice.
4. Rewrite the narrative around the direction-vs-distance split (B4) as the numbers land.

Launching the 15-day campaign before 1 and 2 means running it again afterwards.
