# QA findings — implementation and manuscript

Session of 5 September 2026, run while the remediation campaign was executing.
Each finding lists the evidence that produced it and what would change if it is
accepted. Nothing here has been "fixed" in the code: these are diagnoses, and the
first one is large enough that the response is the author's call, not mine.

---

## The counter bug is fixed (5 September)

F1, F11, F13, F17 and F20 are all the same defect. It is fixed. Every decision a
strategy makes is now taken on the trainable parameters; **aggregation is unchanged** and
still averages the full vector, buffers included, because those are real model state that
has to be returned to the clients.

`DefenseStrategy` gained `set_signal_mask()` and `sig()`; `build_defense_strategy` attaches
the mask to every strategy it builds. What each defense now measures on the subspace:

| file | what moved to the trainable subspace |
|---|---|
| `gradcos.py` | pairwise cosine, and the residual variant's mean-centring |
| `krum.py` | pairwise distances (also forced to float64 — see F15) |
| `flame.py` | cosine clustering, the clip norm, and `S` which sets the DP noise scale |
| `fltrust.py` | the trust cosine and the `‖g0‖/‖gi‖` rescaling (F20) |
| `foolsgold.py` | history similarity (F17) |
| `robust_stats.py` | NormClip's clip norm and noise scale (F11); RFA's Weiszfeld weights; Bulyan's selection |
| `fl/engine.py` | `_update_geometry` (salience gap, pairwise cosines, norm ratio) and the attacker's norm-matching |
| `attacks/evasion.py` | the noise is scaled by the norm of the subspace it lands in, so `lambda=1` means what it says |

Coordinate-wise median and trimmed mean were left alone deliberately: they act per
coordinate, so the counter gets its own median and never contaminates the others.

### Verified on real data

A smoke run (40k rows, 10 clients, 3 rounds, all 11 defenses x simple + adaptive) with the
fix in place, against the same quantities measured through the broken path at full scale:

| logged geometry | before (broken, full scale) | after (fixed, smoke) |
|---|---|---|
| `salience_gap` | 0.000042 | **0.465** |
| `mal_pair_cos` | 0.999022 | 0.855 |
| `honest_pair_cos` | 0.998912 | 0.802 |
| `mal_norm_ratio` | 0.999973 | 1.062 |

The two runs are at different scales so the absolute values are not comparable, but the
structure is: the salience gap moves from 4.2e-5 to 0.465, and the malicious and honest
pairwise cosines separate in the *first* decimal instead of the fourth.

Under the adaptive attacker in the same smoke run, both mechanisms now do what they are
described as doing:

- colluder cosine falls **0.855 -> 0.236** while the honest cohort stays at 0.805 — the
  decorrelation is visible and effective, which over the raw vector it could not be,
  because the counter floored the cosine at 0.428;
- `mal_norm_ratio` lands at **1.000000** — norm-matching is now exact, where before it was
  matching a batch counter that was already identical.

`honest_pair_cos` of 0.802 here also agrees with the 0.831 measured on the instrumented
full-scale round, which is the cross-check that matters: the fix reproduces the real
honest-agreement figure rather than inventing one.

### The reduced-scale discrepancy is explained

Sec. 7.4 reports colluder cosine falling to 0.16-0.33 from a reduced-scale validation run
(6 clients, 3 rounds, 8k rows), while the full-scale cells gave 0.428 — a discrepancy the
paper flagged but could not account for.

The counter explains it exactly. That reduced run does `ceil(8000/6/256) = 6` batches per
client, so the counter contributes 6, not 79:

| run | counter | counter share of ‖Δ‖² | measured colluder cosine |
|---|---|---|---|
| reduced-scale validation | 6 | ~36% | 0.16-0.33 |
| full-scale campaign | 79 | ~99% | 0.428 |

At reduced scale the cosine was mostly real signal and the decorrelation showed. At full
scale the counter dominated and set a floor the noise could not push below. The paper's own
validation run was less contaminated than its headline runs, which is why the two disagreed
— the bug became visible with scale.

### Every previously measured number is void

Not "slightly shifted" — void. Every similarity, distance, norm, clip threshold and noise
scale in every completed cell was computed through the broken path. So all 321 committed
result files were archived to `results/_pre_counterfix/` (the `_` prefix is the project's
convention for superseded runs and is already excluded by both aggregators) and the
campaign restarted from zero.

The paper therefore goes almost entirely `\PENDING` until cells land again. That is the
honest state: the gate exists precisely so this is loud rather than silent.

`run_remediation.sh` gained a **lane 0** that re-runs the multi-seed headline (120 cells)
before anything else, because tab:main is the paper's spine and every other table is read
against it. Full re-run at the measured ~40 min/cell:

| lane | cells | time |
|---|---|---|
| 0 multi-seed headline | 120 | ~3.3 days |
| 1-6 remediation lanes | 287 | ~8 days |
| breadth grid (not yet scripted for re-run) | 140 | ~3.9 days |

The breadth grid is single-seed and feeds the grid means and the ratio sweep; it is not in
`run_remediation.sh` and will need its own pass.

## The fixes invalidate a third headline finding (5 September, preliminary)

An integration run with the counter fix and the corrected class weighting, at only **5
rounds** on a reduced smoke configuration, against the paper's 100-round numbers:

| defense | clean CA, 100 rounds (broken) | clean CA, 5 rounds (fixed) |
|---|---|---|
| FedAvg | 0.703 | 0.712 |
| Krum | 0.693 | 0.709 |
| FLTrust | **0.556** | **0.679** |
| FLAME | **0.499** | **0.725** |

**CORRECTION (added after a controlled A/B):** the recovery below is real but is *not*
mostly the counter fix. Isolating the counter fix with the `signal_subspace` toggle -- same
config, one flag -- gives FLAME **+0.012**, not +0.22. The class-weighting change, applied
in the same batch of edits, accounts for almost all of it. The two were varied together and
I read the joint effect as one of them. The paragraph below stands as a description of the
combined change only.

**FLAME's clean-accuracy deficit is gone.** The paper's third finding -- "no free lunch",
that FLAME's low backdoor rate is bought by discarding 40% of honest clients and that this
is where its 0.20 clean-accuracy deficit comes from -- rested on a deficit that was
substantially an artifact of F13. With sigma calibrated to the trainable subspace instead
of the batch counter, FLAME goes from 0.20 *below* FedAvg to 0.013 *above* it.

FLTrust recovers 12 points for the same class of reason (F20): its `||g0||/||gi||`
rescaling was the ratio of two batch counters.

So of the paper's four headline findings, the re-run puts three in question:

| finding | status |
|---|---|
| 1. salience decides robustness | axis was numerically degenerate (S = 4.2e-5); must be re-measured |
| 2. the collusion signal is cheap to remove | contradicted for Krum, which the evasion *repairs* (F18) |
| 3. FPR accounting -- "no free lunch" | the deficit it explains is largely an artifact (this section) |
| 4. realizability audit | **unaffected** -- a data-space analysis with no model updates in it |

Finding 4 stands. Findings 1-3 need re-measuring before anything is written about them.

**These are 5-round smoke numbers on a 40k-row, 10-client configuration.** They are not
results and must not be quoted. What they establish is direction and magnitude: the effect
is far too large to be noise, and it points the same way as the mechanism predicted in F13
and F20. The full campaign settles it.

## Findings at a glance

| # | Severity | Finding |
|---|---|---|
| F1 | CRITICAL | a batch counter is 99.7% of the "update direction" every defense reads |
| F11 | CRITICAL | the same counter makes every norm-based rule inert |
| F13 | CRITICAL | FLAME's DP noise is calibrated to the batch counter, not the model update |
| F17 | CRITICAL | FoolsGold's history similarity is 99.98% batch counter, which explains its bimodality |
| F18 | CRITICAL | the first evasion results contradict the paper's framing, and F1 predicts why |
| F20 | CRITICAL | FLTrust rescales every client update by the ratio of two batch counters |
| F2 | HIGH | the evasion is masked off the coordinates that dominate the signal |
| F7 | HIGH, fixed | deduplication was decided by filename sort order |
| F8 | HIGH, fixed | row-level fallback where field-level was needed |
| F9 | HIGH | the paper's central methodological claim about itself is false |
| F19 | MEDIUM, fixed | the realizability percentile was quoted past the resolution of its own sample |
| F3 | MEDIUM | zero-sum noise does not cancel under example-weighted aggregation |
| F4 | MEDIUM | non-IID makes the dominant coordinate track shard size |
| F14 | MEDIUM, fixed | reported per-cell runtimes were cumulative, and the campaign estimates were built on them |
| F5 | LOW, latent | `_tail_mean` averages the last 10 *present* values, not the last 10 rounds |
| F6 | LOW | residual GradCos falls back to the wrong similarity matrix |
| F10 | LOW | a stale figure in the project's own status document |
| F12 | LOW | inconsistent RNG seeding convention |
| F16 | LOW | the paper describes GradCos's homogeneity gate as doing something it does not |
| F15 | INFO | Krum's numerics are safe, but only by accident |
Ordered by severity below. `(fixed)` means the change is in the tree and
verified; everything else is a diagnosis left for you to decide on.

---

## F1 (CRITICAL) — a batch counter is 99.7% of the "update direction" every defense reads

`torch_utils.get_weights` sends the whole `state_dict`, and `DefenseStrategy.flatten`
concatenates it in that order. The flattened update therefore includes the BatchNorm
buffers of `conv.2`, one of which is **`num_batches_tracked`** — an int64 counter that
increments by the number of batches each client processed.

At the committed configuration (`configs/default.yaml`: 400k rows, 20 clients,
batch 256, 1 local epoch) that is `ceil(20000/256) = 79` per round, on **one
coordinate**, for **every client**.

Measured decomposition of a single client update (CPU reproduction, same
architecture, `CNNLSTM(num_features=39, num_classes=8)`):

| block | coords | ‖Δ‖ | share of ‖Δ‖² |
|---|---|---|---|
| `conv.2.num_batches_tracked` | 1 | 8.00 | **76.7%** |
| `conv.2.running_var` | 64 | 4.05 | 19.7% |
| `conv.2.running_mean` | 64 | 1.33 | 2.1% |
| all LSTM weights | 98,304 | 1.05 | 1.3% |
| everything else trainable | 9,168 | 0.31 | 0.1% |

That run used 8 batches. The real runs use **79**, so the counter's share rises to
**~99.67%** of the squared norm.

### MEASURED on the real pipeline (this supersedes the estimates above)

One instrumented round was run through the real loader, the real config and the real
CICIoT2023 data: `configs/default.yaml`, 399,436 train rows, 20 IID clients of 19,972 rows,
batch 256, one local epoch, three clients. Measured, not simulated:

| quantity | measured |
|---|---|
| `num_batches_tracked` delta | **79.0** exactly, every client |
| ‖Δ‖ total | 79.75 |
| ‖Δ‖ trainable | **8.01** |
| ‖Δ‖ buffers | 79.35 |
| **counter share of ‖Δ‖²** | **98.1%** |
| buffer share of ‖Δ‖² | 99.0% |
| pairwise cosine, full state_dict | **0.998234** |
| pairwise cosine, trainable only | **0.831** |

The measured full-vector cosine of 0.9982 matches the `honest_pair_cos ~ 0.9989` the real
runs log, which closes the loop: the instrumented round reproduces what the campaign sees.

**Two of my own earlier figures were wrong and are corrected here.** I estimated the
trainable norm at ~1.1 from a synthetic reproduction; it is **8.01** on real data. That puts
the counter at **98.1%** of the squared norm, not the 99.7% I quoted. The conclusion is
unchanged — one coordinate out of 108,617 carrying 98% of the norm — but the number should
be 98.1%.

The second correction matters more, and it cuts *in the paper's favour*. On synthetic data
the trainable-only cosine was 0.489, which made GradCos's premise look weak. On real data it
is **0.831**: honest clients genuinely do agree strongly once the counter is removed. The
premise in Sec. 5.3 is sound. What is broken is the measurement, not the idea.

That is the cleanest statement of the whole finding:

    honest agreement, trainable only   0.831      discriminative range 0.169
    as the defenses measure it         0.998234   discriminative range 0.001766
                                                  --> compressed 96x

The signal these defenses need is real and has a usable dynamic range. The counter
compresses it by a factor of ~96 into the third and fourth decimal places, which is where
every threshold in the paper ends up operating.

### The bound does not depend on the simulation

The table above comes from a CPU reproduction, which is fair to discount. The conclusion
does not rest on it. Adam's per-step update is `lr * mhat/(sqrt(vhat)+eps)`, and
`|mhat/sqrt(vhat)| <= ~1` outside the first few steps, so over one local epoch
`|dtheta_i| <= lr * n_batches = 1e-3 * 79 = 0.079` per parameter. Across all 108,488
trainable coordinates that bounds the trainable block at

    ||d_trainable|| <= 0.079 * sqrt(108488) = 26.0

and that bound is attained only if **every** parameter moves at Adam's maximum rate,
monotonically, for all 79 batches. The counter's contribution is exactly 79, by
construction, with no bound needed.

So even in that impossible worst case the counter is **at least 90.2%** of the squared
norm. At the trainable norm actually observed (~1.1) it is 99.7%. There is no data
distribution and no training outcome that makes this coordinate small, because it is not a
function of the data at all — it is a count of batches.

**This is confirmed in the real result files, not only in simulation.** The three runs
that log update geometry report `honest_pair_cos` = 0.998912, 0.998919, 0.998943 — a
spread of 3e-5 across independent runs. That is the signature of a shared constant
coordinate dominating the vector, not of gradient agreement.

### What it affects

Every quantity the paper's argument is built on is computed over this vector.

- **The salience gap `S`**, the paper's central measured axis. In
  `rem_ciciot2023_fedavg_atk1_m0.2_p0.1_fixed.json` — the **fixed** trigger, the
  conspicuous one, at the headline operating point — the logged value is
  **`salience_gap = 0.000042`**. The paper says robustness tracks this quantity and
  sweeps trigger magnitude along it. At the point where the defenses succeed it is
  4.2e-5, because a rotation of the genuine update barely moves a vector that is
  99.7% constant.
- **The collusion signal.** In the same run `mal_pair_cos = 0.999022` against
  `honest_pair_cos = 0.998912`. GradCos's clique test, FLAME's HDBSCAN clustering and
  FoolsGold's history similarity are separating colluders on a **fourth-decimal**
  difference. They do succeed (GradCos BSR 0.004, DR 0.97 on fixed), because the
  median/MAD thresholding is scale-free and the tiny difference is real. But the
  mechanism is not the one the paper describes.
- **`mal_norm_ratio`**, and therefore the norm-matching the `adaptive` variant
  performs. Matching "the median honest norm" is ~99.7% matching a batch counter.
- **The GradCos premise** as stated in Sec. 5.3 — "honest clients optimize the same
  objective on similar-distribution data, so their update directions are mutually
  well-aligned". With a learnable target and 6 honest clients, mean pairwise cosine
  measures **0.989** over the full state_dict but **0.489** over trainable parameters
  only. The alignment the premise asserts is real but roughly half as strong as the
  logged number; the rest is buffers.

### Recommended fix

Restrict `DefenseStrategy.flatten` — or add a mask applied by every defense and by
`FederatedEngine._update_geometry` — to trainable parameters. `trainable_flat_mask`
already exists in `src/defenses/base.py:45` and is currently used only by FLAME, and
only to restrict its DP *noise*. At minimum exclude `num_batches_tracked`, which
carries no information about the model or the data; excluding all buffers is the
defensible choice and is what the "update direction" language in the paper means.

This changes reported numbers. `S` becomes a quantity with real dynamic range
(cosines move from ~0.999 to ~0.5), which is what the dose-response figure needs in
order to be a figure at all. **Whether the defense rankings survive is an empirical
question and has to be re-run.** That is the uncomfortable part and the reason this is
flagged rather than patched.

---


## F11 (CRITICAL) — the same counter makes every norm-based rule inert

F1's consequence for the magnitude family, which is the paper's control group and the
subject of lane 3. Norm-based rules measure `||delta||`, and that norm is ~99.7% the batch
counter. Using the measured block norms (counter 79, running_var 4.05, running_mean 1.33,
trainable 1.10):

| malicious client's trainable update | norm a magnitude rule measures |
|---|---|
| 1.5x larger | +0.012% |
| 2x larger | +0.029% |
| 5x larger | +0.232% |
| **10x larger** | **+0.952%** |
| 50x larger | +21.8% |

A colluder could make its actual model update **ten times larger** and move the quantity
norm-clip thresholds on by under one percent.

So:

- **Norm-clip is effectively a no-op.** Clipping to the median norm cannot constrain a
  trainable update that is 1.4% of the vector being clipped. Whatever it does in lane 3
  will be its Gaussian noise, not its clipping.
- **FLAME's clipping stage is inert for the same reason**, which matters because the
  paper attributes FLAME's clean-accuracy loss to the *clustering* stage and treats
  norm-clip as the control isolating the magnitude stage. If the magnitude stage cannot
  act, that control does not isolate what it is meant to isolate.
- **`mal_norm_ratio` is structurally pinned near 1.** The logged value for the static
  attack is 0.999973 — read as "the malicious updates are magnitude-indistinguishable",
  when it mostly says the counter is identical. The paper's "what a magnitude rule sees"
  logging is uninformative for static attacks.
- **Norm-matching in `constrained` / `adaptive` is close to a no-op for static poisoning**,
  since the norms already match to five decimals. It does real work only against
  `decorrelated`, where the injected noise is scaled to the counter-dominated norm and so
  is genuinely large (measured ratio 1.32).

**Falsifiable prediction for lane 3.** If F1 and F11 hold, norm-clip should land close to
undefended FedAvg on all three triggers rather than partway between FedAvg and FLAME. The
coordinate-wise rules (median, trimmed mean) are *not* affected — they act per coordinate,
so the counter gets its own median and never contaminates the others — and RFA and Bulyan
are largely unaffected because they work from pairwise *differences*, in which the shared
counter cancels. That asymmetry is itself a clean test: if norm-clip behaves like FedAvg
while median and trimmed mean do not, the cause is the norm, not the trigger.

This prediction is worth checking before the magnitude-family paragraph is written, because
the natural reading of "norm-clip fails too" is "magnitude rules share the blind spot",
and the actual cause would be that the magnitude was never measured.


## F13 (CRITICAL) — FLAME's DP noise is calibrated to the batch counter, not the model update

`FlameDefense.aggregate_fit` sets the noise scale from the median admitted **norm**:

```python
S = float(np.median(adm_norms))     # ~79, i.e. the counter (F1)
sigma = self.noise_lambda * S
noise = self.rng.normal(0.0, sigma, size=agg_delta.shape) * self.noise_mask
```

`S` is meant to stand for the magnitude of the model update. Because of F1 it is ~72x
larger than that. With the committed `flame_noise_lambda: 0.001`:

| quantity | value |
|---|---|
| `S` as computed | 79.12 |
| `S` if it measured the model update | 1.10 |
| per-coordinate noise std | 0.0791 |
| per-coordinate aggregate update | 0.0033 |
| **noise / signal, per coordinate** | **23.7x** |
| total injected noise norm | 26.06 |
| aggregate trainable update norm | 1.10 |

The noise added to the global model each round has ~24x the magnitude of the update it is
added to. The mask correctly keeps it off the BatchNorm buffers, so it lands entirely on
the 108,488 trainable coordinates — the ones that carry the model.

### Why this matters for a headline claim

The paper's "no free lunch" section attributes FLAME's 0.20 clean-accuracy deficit
(0.499 against FedAvg's 0.702) to the **clustering** stage: "A defense discarding two
honest updates in five is training on roughly 60% of the federation, which is a sufficient
explanation for its 0.499 clean accuracy."

It may be sufficient, but it is no longer the only candidate, and it is probably not the
largest one. A 24x noise-to-signal ratio applied every round for 100 rounds is an ample
explanation on its own. The paper hedges in the right direction already ("supported for the
clustering mechanism and provisional as to the noise scale"), but the hedge treats the noise
scale as an untuned hyperparameter. It is not: it is coupled to a measurement bug, and no
value of `flame_noise_lambda` chosen by calibration will decouple it, because calibration
would only be compensating for the 72x inflation rather than removing it.

`NormClip` takes the same `noise_lambda` and the same median-norm scaling
(`robust_stats.py:174`), so lane 3 will carry the same defect.

### The decisive experiment is one cell

Run FLAME at the headline point with the noise switched off, leaving clustering and
clipping intact:

```bash
python3 -m experiments.run_sweep --device cuda --rounds 100 --tag qa \
  --defenses flame --triggers fixed --ratios 0.2 --poisons 0.1 --variants simple
# with flame_noise_lambda: 0.0 in the config
```

If clean accuracy stays near 0.50, the deficit really is the clustering and the paper's
account stands. If it recovers toward 0.70, the deficit is the noise, and the "no free
lunch" mechanism — one of the paper's four headline findings — needs rewriting.

I have not run it: the GPU is committed to lane 1a and this would preempt it. It is ~25
minutes whenever a slot is free, and it should be run before that section is finalised.


## F17 (CRITICAL) — FoolsGold's history similarity is 99.98% batch counter, which explains its bimodality

The sharpest instance of F1, because history similarity *is* FoolsGold's entire signal.

`FoolsGoldDefense` accumulates `self.history[cid] += delta` and then down-weights clients
whose accumulated histories are mutually similar. The counter accumulates exactly linearly
(79 per round, 7900 by round 100) while the trainable component partially cancels as the
model converges. Bounding the trainable part both ways — `sqrt(R)` if successive updates
are uncorrelated, linear if perfectly aligned — the counter is **99.98% of the squared norm
at every R**, because both terms scale together:

| R | counter | trainable (sqrt-R .. linear) | counter share of ‖history‖² |
|---|---|---|---|
| 10 | 790 | 3.5 .. 11.0 | 99.9806% |
| 50 | 3950 | 7.8 .. 55.0 | 99.9806% |
| 100 | 7900 | 11.0 .. 110.0 | 99.9806% |

So the pairwise cosine between any two client histories is >= 0.9998 for **every** pair,
colluding or honest. `maxcs = cs.max(axis=1)` is ~0.9998 for everyone, and the pardoning
loop then compares near-identical values. FoolsGold's weights are decided by residue in the
fourth or fifth decimal place.

**This gives a mechanism for a result the paper already reports but explains differently.**
Sec. 7.11: "FoolsGold on the fixed trigger has s.d. 0.489 (BSR range 0.003-0.926): it either
locks onto the colluders' shared history early or never does." That bimodality is exactly
what a detector separating on floating-point residue would produce. The paper reads it as a
property of FoolsGold; on this evidence it is a property of the vector FoolsGold is given.

The same reading applies to the paper's use of FoolsGold as corroboration: "That FoolsGold
— built precisely to catch colluding sybils by cosine similarity — also fails underlines
that the blind spot belongs to the *signal*, not to one defense's tuning." The conclusion
may survive, but the argument currently rests on a defense that was never shown the
signal it was designed to read.

## F18 (CRITICAL) — the first evasion results contradict the paper's framing, and F1 predicts why

Lane 1a reached Krum. Measured, at the headline point on the fixed trigger:

| attacker | BSR | DR | FPR | malicious norm ratio |
|---|---|---|---|---|
| static (`simple`) | 0.948 | 0.18 | 0.20 | ~1.00 |
| **`decorrelated`** | **0.001** | **1.00** | **0.00** | 1.32 |

The evasion does not defeat Krum. It **repairs** it — from a defense that is backdoored
(BSR 0.948, catching 18% of colluders while falsely flagging 20% of honest clients) to one
that is perfect (every colluder caught, no honest client flagged, backdoor gone).

The abstract currently says "Every direction-based rule here, including our own, is
evaluated against it", and the paper's argument is that the evasion removes the signal
these rules depend on. For Krum that is now false in the strongest possible way, on the
paper's own headline configuration.

Part of this the paper already anticipates: Sec. 7.4 notes `decorrelated` "inflates the
malicious update norms, so a magnitude rule could still see it", which is why the
`adaptive` variant norm-matches. So the decisive cell is Krum vs `adaptive`, running now.

**F1 predicts that norm-matching will not save the attacker either.** `adaptive` rescales
the *whole* malicious delta to the median honest norm — and that norm is the batch counter.
At the measured ratio of 1.32 the rescale factor is 1/1.32, which drags the malicious
counter coordinate from 79 to 59.8. That single coordinate then contributes
`(79 - 59.8)^2 = 367` to every malicious-honest squared distance, against true
honest-honest distances of ~5 (F15). The attacker ends up roughly **73x further from the
honest cluster than honest clients are from each other**, on the counter alone.

**Prediction, recorded before the cell completed:** Krum vs `adaptive` should also give
DR ~1.0, FPR ~0.0 and BSR near 0. Norm-matching cannot hide an attacker from a *distance*
test when the norm being matched is dominated by a coordinate every honest client shares
exactly — rescaling to match it necessarily moves that coordinate away from everyone.

### The prediction was confirmed

Cell 8 landed. Krum vs `adaptive`: **BSR 0.001, DR 1.00, FPR 0.00** — exactly as predicted,
and the prediction was written into this file before the cell finished.

The decisive detail is the norm ratio: **0.99**. The attacker's norm-matching *worked* —
the malicious updates are magnitude-indistinguishable from honest ones by the measure the
attack targets. And Krum caught every one of them anyway, with no false positives.

Full picture for Krum at the headline point, fixed trigger:

| attacker | BSR | DR | FPR | malicious norm ratio | malicious pairwise cosine |
|---|---|---|---|---|---|
| static | 0.948 | 0.18 | 0.20 | ~1.00 | 0.999 |
| `decorrelated` | 0.001 | 1.00 | 0.00 | 1.32 | 0.428 |
| `adaptive` | **0.001** | **1.00** | **0.00** | **0.99** | 0.421 |

Norm-matching hides the attacker from a *norm* test and simultaneously exposes it to a
*distance* test, because the norm being matched is dominated by a coordinate every honest
client shares exactly. Rescaling the vector to match that norm necessarily moves the
counter away from everyone. There is no setting of the attack that escapes both.

So the mechanism behind Table 5 is not "the evasion beats direction-based rules". It is
"the evasion perturbs the batch counter, and whether a defense notices depends entirely on
whether it reads that counter as **direction** (cosine rules: blinded, because a shared
constant dominates every cosine) or as **distance** (Krum: alerted, because the constant
cancels in differences and the perturbation does not)".

That is a different paper from the one currently written. It is also a considerably more
interesting one — but it needs the F1 fix first, because on a buffer-free update vector all
of these numbers change, and the honest version of this table cannot be written until they
are re-measured.

This also means the abstract's second finding ("Every direction-based rule here, including
our own, is evaluated against it", with the implication that all of them fall) is already
contradicted by the paper's own headline configuration.

## F20 (CRITICAL) — FLTrust rescales every client update by the ratio of two batch counters

`FLTrust.aggregate_fit` does `agg += ts * (gi / ||gi||) * ||g0||` — each client update is
renormalised to the length of the server's own update. Both lengths are dominated by
`num_batches_tracked` (F1), and the server and the clients run wildly different numbers of
batches:

| | rows | batches per round | resulting ‖·‖ |
|---|---|---|---|
| server root set | 300 | **2** | ~2 |
| each client shard | 20,000 | **79** | ~79 |

So every client update is scaled by `||g0|| / ||gi|| ~ 2/79 = 0.025` — **shrunk by about
40x** — and the model update inside it is shrunk by the same factor. FLTrust should
therefore learn roughly 40x more slowly than FedAvg on identical data, for reasons having
nothing to do with trust.

### The saved learning curves show exactly that

Clean runs, mean over the five seeds:

| defense | acc @ round 10 | acc @ 50 | final | slope over last 20 rounds |
|---|---|---|---|---|
| FedAvg | 0.689 | 0.680 | 0.703 | +0.00002 /round |
| **FLTrust** | **0.367** | 0.645 | 0.559 | **+0.00025 /round** |
| FLAME | 0.689 | 0.620 | 0.663 | **-0.00436 /round** |

FedAvg is at its final accuracy by round 10 and flat thereafter. FLTrust starts at
**0.367** — barely half — and is still climbing at round 100, with a slope 12x FedAvg's.
That is the signature of a model being trained too slowly, not of a model converging to a
worse optimum.

The paper's explanation is different: "honest updates that disagree with a 300-sample root
direction are attenuated too". If that were the mechanism, FLTrust would converge to a
worse place, not crawl toward a similar one. The curve shape favours the rescaling.

*Caveat, stated because it cuts against a clean story:* FLTrust's mean accuracy at round 50
(0.645) is higher than at round 100 (0.559), so the trajectory is not monotone and the
across-seed variance is large. The round-10 gap and the slope are the solid parts of this
evidence; the exact endpoint is not.

### It also corroborates F13

FLAME's slope over the final 20 rounds is **negative** (-0.0044/round): it is getting worse
as training continues. That is what a defense injecting noise at ~24x the magnitude of the
update it is added to (F13) would do — damage accumulating faster than learning repairs it.
Two independent findings predicting the same curve shape, both observed.

## F2 (HIGH) — the evasion is masked off the coordinates that dominate the signal

`zero_sum_noise` (`src/attacks/evasion.py:38`) takes `mask=self._trainable_mask()`, so
the noise is placed only on trainable parameters — correctly, since noising
`running_var` can drive it negative and produce NaN predictions. But the cosine the
evasion is trying to destroy is computed **with** the buffers (F1). The attacker
cannot decorrelate the component that dominates the measurement.

The noise magnitude is `scale * ||delta||` where `||delta||` is the **full** update
norm, ~99.7% counter, while the noise lands entirely on the trainable block whose own
norm is ~1.1. So `evasion_noise: 1.0` is not "noise the size of the update"; it is
roughly **70x the trainable update**. The paper describes it as "independent isotropic
noise nu_j scaled to lambda||delta_j||", which is literally what the code does, but a
reader will not take that to mean a 70x perturbation of the weights.

This is the mechanism behind the discrepancy already flagged in `SUBMISSION_STATUS.md`:
the abstract claims colluder cosine falls "below 0.35", the reduced-scale validation
gave 0.16–0.33, and the first full-scale cells give **0.428** (decorrelated) and
**0.420** (adaptive). The evasion is fighting a constant it cannot touch.

Once F1 is fixed, `lambda` becomes interpretable and these numbers change again.

---


## F7 (HIGH, fixed) — deduplication was decided by filename sort order

`make_numbers.py` reduced `summary.csv` to one row per configuration with

```python
if key not in ss_grid or str(r.get("run_tag")) == GRID_TAG:
```

"take the `sweep` grid row, otherwise keep whatever arrived first". `load_results`
yields files in filename order, so for a configuration with **no** `sweep` row but both
an `ms` replicate and a `rem` remediation run, `ms_` won on alphabetical order alone.

The `ms` campaign predates per-round geometry logging, so its row carries `nan` for
`mal_pair_cos`, `honest_pair_cos`, `mal_norm_ratio` and `salience_gap`. The `rem` row
is the only one that has them. Result: those macros stayed `\PENDING` **even after the
lane that produces them had already run** — a gate that could never open.

Fixed: `TAG_RANK = {sweep: 0, rem: 1, ms: 2}` and an explicit `_tag_rank` comparison,
so the grid stays authoritative and sort order never decides. Verified no regression:
all nine GradCos fixed-trigger grid cells still come from `sweep` and the mean is
unchanged at 0.1706.


## F8 (HIGH, fixed) — row-level fallback where field-level was needed

Same family of bug, one level up. The adaptive-attacker block did

```python
r = pick(ms, ...) or spick(...)
```

which short-circuits on the multi-seed row **existing**, never on it being useful. For
the static (`simple`) column that row exists and carries `nan` geometry, so
`adMalCos*Simple`, `adHonCos*Simple` and `adNormRatio*Simple` reported `\PENDING`
while the numbers sat on disk in the remediation run.

Fixed: fall back per field, skipping `None`, `nan` and empty. `adMalCosfedavgSimple`
now resolves to 0.999 (from `rem`) while `adBSRfedavgSimple` still takes the 5-seed
mean 0.968 from the multi-seed campaign — each macro sourced from the best available
run for that specific quantity.


## F9 (HIGH) — the paper's central methodological claim about itself is false

Sec. 6 states: "Every number quoted in this paper---in the prose and in every
table---is a macro generated from the committed result JSONs ... nothing is
hand-entered." A scan of the prose and captions, excluding table bodies and anything
containing a macro, finds **28 distinct hand-typed decimal values**.

**Three of them were wrong:**

- **"every one of the 27 attack cells has BSR $\geq 0.90$"** (Sec. 7.1). The weakest
  undefended cell is **0.8992** (`fixed`, m=0.1, p=0.05). The claim is false by 0.0008.
  Now generated as `\gridAttackCells` and `\gridMinBSRfedavg`, and reads
  "$\geq 0.899$".
- **"FLNET2023, where the same architecture reaches macro-F1 $0.9994$"** (Sec. 8). The
  generated value is **0.9996**. Now `\flCleanFonegradcos`.
- **"can still sit beyond the $99.99$th percentile of joint benign variation"** — in the
  **abstract**, one of the four headline findings, and repeated in Sec. 4.1 and in the
  project README. The audit file records
  `joint_mahalanobis_pctile_vs_benign = 99.974`. That is beyond the 99.9th percentile,
  not the 99.99th. All three sites now read `\rzPctileFixedQtr` = 99.97.

Five more that merely duplicated existing macros — and so could silently drift out of
sync with the tables they restate — are now wired to those macros: FLAME's backdoor
rate and FPR in the abstract, FLTrust's rate in the introduction, FoolsGold's seed s.d.
and range, and GradCos's CICIoT s.d. Two new macros were added for the range
(`msBSRmin*`, `msBSRmax*`) and one for the percentage form (`msFPRpct*`).

**Since fixed:** the whole of Table 3 and the realizability prose in Sec. 4.1 are now
generated from `results/realizability_ciciot2023.json` via a new `rz*` macro family (44
macros), as is GradCos's `+0.15` clean-accuracy advantage and FLAME's `0.20` deficit,
both of which are differences between two table entries and were typed in three places
between them.

**Still hand-entered (5 values):** the four donor clean-model BSRs
(0.006 / 0.000 / 0.008 / 0.001 and the 1.000 outlier) in Sec. 4.1, and the FLNET seed
spread `{0.98, 0.18, 0.008, 0.008}` in Sec. 8. Their source data is committed but is not
routed through the generator. Sec. 6's claim is still not literally true until they are.

`tools/check_manuscript.py` now enforces this: any literal decimal in prose or a caption
that is not on an explicit allowlist fails the check. The allowlist has 24 entries, each
annotated with why it is legitimately a literal (experiment parameter, reduced-scale
figure pending lane 1a, a hypothetical in the limitations, or one of the five above).
It caught two values I had missed on the first pass.


## F19 (MEDIUM, fixed) — the realizability percentile was quoted past the resolution of its own sample

`realizability.py:39` caps the benign reference at `_MAX_ROWS = 20000`. The percentile is
then `(ref_m < trig_m).mean() * 100`, so the finest value the sample can express is
1/20000 = 0.005%.

The reported 99.974% therefore means **~5 of 20,000 benign rows** exceeded the trigger's
Mahalanobis distance. A Poisson 95% interval on a count of 5 is [1.6, 11.7], i.e. a
percentile anywhere in **[99.94%, 99.99%]**. Two decimal places imply a precision that five
observations do not carry — and the paper's original "beyond the 99.99th percentile" was
both numerically wrong and past the resolution limit entirely.

Fixed by quoting the count instead. The abstract now reads "can still be further from the
benign mean than all but 5 of 20,000 real benign flows", and Sec. 4.1 says why the count is
given rather than a percentile. Both numbers are generated (`\rzExceedFixedQtr`,
`\rzRefRows`). The claim is unchanged in force and now survives being checked.

If a sharper number is wanted, raising `_MAX_ROWS` costs one cheap re-run of the audit —
it is a CPU diagnostic, not part of the experiment grid.

## F3 (MEDIUM) — zero-sum noise does not cancel under example-weighted aggregation

`DefenseStrategy.weighted_average` (`base.py:72`) weights by `num_examples`. The noise
sums to zero **unweighted** across the malicious cohort, so the cancellation the paper
relies on — "the perturbation sums to zero over M and contributes nothing to the
aggregate" (Sec. 7.4, Eq. 3) — is exact only when the colluders hold equally sized
shards.

Under IID (`_iid` uses `np.array_split`) shards differ by at most one row, so this is
harmless today. Under Dirichlet (`_dirichlet`) shard sizes vary substantially, and the
residual is proportional to that variation.

No current result is wrong, because the evasion lanes are IID only. It becomes wrong
the moment the adaptive attacker is run non-IID. Either state the equal-shard
assumption in the threat model, or make the noise zero-sum in the aggregation weights.

---


## F4 (MEDIUM) — non-IID makes the dominant coordinate track shard size

Following F1 and F3: under Dirichlet partitioning clients hold different numbers of
rows, so `num_batches_tracked` increments differently per client. The coordinate that
dominates the cosine geometry then varies with **shard size**, which is uncorrelated
with maliciousness.

The paper reports that heterogeneity flips Krum from robust to backdoored and treats
this as evidence that "non-IID data changes the geometry these defenses read". That
conclusion may be right for the wrong reason: Krum scores on pairwise distances, and
under Dirichlet the largest term in every pairwise distance is the difference in batch
counts. Worth re-checking after F1.

---


## F14 (MEDIUM, fixed) — reported per-cell runtimes were cumulative, and the campaign estimates were built on them

`experiments/run_sweep.py` set `t0 = time.time()` once **before** the cell loop and then
printed `time.time() - t0` after every cell. Each cell therefore reported the elapsed time
of the entire sweep so far, not its own cost. The numbers grow monotonically and look like
per-cell durations getting worse.

Verified against file mtimes for the current run (started 00:32):

| logged | reads as | actual mtime | real duration |
|---|---|---|---|
| 1793 s | "30 min cell" | 01:02 | 29.9 min |
| 6100 s | "102 min cell" | 02:14 | 71.8 min |
| 8505 s | "142 min cell" | 02:54 | 40.1 min |

Fixed: time each cell from its own start, and print both (`| 2405s (cum 8505s)`). The
running sweep already has the old code loaded, so the fix takes effect on the next process.

**This matters beyond tidiness.** The project's planning numbers come from these values.
`SUBMISSION_STATUS.md` reasons from "roughly 25 to 30 minutes per cell" and "the first cell
of the restarted run took 33.5 minutes" — the first-cell reading happens to be correct
under the bug (its cumulative time *is* its duration), which is exactly why the error
survived: the one number anyone checked was the one number the bug did not corrupt.

Real cost is **~30-45 minutes per cell**, not 25-30. The 287-cell campaign is therefore
closer to **190 GPU-hours than 120**, and lane 1a alone needs ~13 more hours from 5/24, not
the ~7 the old numbers implied. I had repeated the wrong figure earlier in this session too.


## F5 (LOW, latent) — `_tail_mean` averages the last 10 *present* values, not the last 10 rounds

`src/metrics/aggregate.py:28` filters `None`/NaN first and then takes `xs[-k:]`. If a
series is ever partially missing, the reported "mean of the last 10 rounds" silently
becomes the mean of the last 10 rounds *that reported a value*, drawn from an
arbitrarily earlier window.

Swept all 314 committed histories: **no series is partially missing**, so nothing
reported today is affected. It is worth guarding anyway, because the FLAME BatchNorm
NaN bug this project already hit is exactly the condition that would trigger it, and
it fails silently rather than loudly.

---


## F6 (LOW) — residual GradCos falls back to the wrong similarity matrix

In `GradCosDefense.aggregate_fit`, `method == "residual"` computes `rcos` from
mean-centred updates and passes it to `_clique_keep`. But the safety floor below
(`base.py` logic at `gradcos.py:79-85`) ranks clients by `mean_sim` computed from
`cos`, the **full-vector** matrix, not `rcos`. If the residual path ever trips the
floor, the clients it keeps are chosen by the signal the residual variant exists to
replace. Rarely reached, but inconsistent.

---


## F10 (LOW) — a stale figure in the project's own status document

`SUBMISSION_STATUS.md` (3 September entry) records the fixed-trigger grid mean for
GradCos as 0.154. Recomputed from the nine committed `sweep` cells it is **0.1706**,
and all nine files are unchanged since July. The paper is unaffected because it quotes
the generated macro, but the status document is wrong about a number in a passage whose
subject is the elimination of transcription errors.


## F12 (LOW) — inconsistent RNG seeding convention

`poison_local_data` is seeded `base_seed + cid` (`src/attacks/__init__.py:71`), so
`(seed=42, cid=3)` and `(seed=45, cid=0)` draw the same stream. Across the five-seed band
42-46 and 20 clients, seeds collide between (seed, client) pairs. The engine's evasion RNG
uses the safer `seed * 1000 + rnd` (`engine.py:157`).

Impact is small — each client holds a different shard, so the same RNG stream selects
different samples — but it weakens the independence of the five-seed replicates slightly,
and the fix is one character.


## F16 (LOW) — the paper describes GradCos's homogeneity gate as doing something it does not

Sec. 5.3: "A homogeneity gate keeps everyone when most clients have a twin (early
training, or a benign IID cohort where all updates align)."

The code does not keep everyone. When more than `n * (1 - min_keep_fraction)` clients have
a twin, `_clique_keep` **defers to `_meansim_keep`** (`gradcos.py:118-123`), which applies
its own outlier test and can still flag clients — for a roughly normal spread it keeps
about 93% and flags the rest. That is a different behaviour from "keeps everyone", and it
is the more likely origin of GradCos's non-zero FPR on the triggers where the clique test
finds nothing.

Two related notes:

- `GradCos.__init__` defaults `method="cluster"`, while the paper calls `clique` the
  default variant. `configs/default.yaml` sets `clique`, so every run is correct; only
  someone instantiating the class directly gets the other one.
- **Only the final round's `gradcos_method` is saved.** Across the seed-42 multi-seed runs
  it reads `clique` for all three triggers, so the clique path is genuinely active on the
  low-salience triggers and the paper's "flagging at close to chance" characterisation is
  supported — I had suspected the deferral was masking it, and the evidence says otherwise.
  But one round out of a hundred is thin. Logging the chosen path per round costs nothing
  and would let Sec. 7.2 say how often the clique test actually ran, which is a stronger
  claim than the one currently made.


## F15 (INFO) — Krum's numerics are safe, but only by accident

Worth writing down because I chased it as a bug and it is not one, and because the reason
it is not one is load-bearing and undocumented.

`KrumDefense` scores clients on pairwise squared distances computed as
`sq[:,None] + sq[None,:] - 2*(V @ V.T)` over **raw weight vectors**. Those vectors contain
the cumulative `num_batches_tracked`, which at round 100 is 79 x 100 = 7900, so
`||v||^2 ~ 6.2e7` while the true pairwise squared distances between clients are ~5. That is
a textbook catastrophic-cancellation setup: subtracting two nearly equal large numbers to
recover a small one.

In **float32** it would be fatal. Simulated at the real dimensions: absolute error ~522
against a true distance of ~5.4, Krum's selection differs from the exact computation, and
the rank correlation of Krum scores against the exact ones is **-0.21** — Krum would be
selecting essentially at random.

It does not happen, because `get_weights` returns `num_batches_tracked` as **int64**
alongside float32 weights, and `np.concatenate` promotes the mix to **float64**. At float64
the relative error is 1.3e-6 % and the selection is identical to a cancellation-free
computation. Verified.

So Krum is correct today because an integer buffer happens to force a dtype promotion.
Two things follow:

- If the update path is ever narrowed to float32 — an obvious bandwidth optimisation, and
  `pack()` already casts the server's *outgoing* weights to float32 — Krum breaks silently
  and looks like a bad defense rather than a broken one.
- **This interacts with the F1 fix.** Masking the buffers out of `flatten`, which is what
  F1 recommends, leaves only float32 arrays and so makes `flatten` return float32. That is
  safe *in this case* only because removing the counter also removes the large shared
  constant that caused the cancellation. Whoever implements F1 should assert the dtype
  rather than rely on that coincidence: `flatten` should cast to float64 explicitly.

## Confirmed correct (checked, no defect)

- `FLTrust` genuinely measures its exclusions: `flagged` is appended only when the
  ReLU trust score is `<= 0.0` (`fltrust.py:73`). The paper's claim that DR = FPR = 0
  because no client ever scores exactly zero is a real measurement, not a default.
  I suspected otherwise because `base.py:21` initialises `last_flagged_cids` to `[]`
  rather than `None`; every defense does set it explicitly, and the three
  coordinate-wise rules correctly set `None` so the engine records N/A.
- `_defense_metrics` computes DR/FPR against ground truth correctly and returns NaN
  (reported as N/A) when a strategy exposes no per-client decision.
- The evasion RNG is seeded per round (`engine.py:157`,
  `RandomState(seed*1000 + rnd)`), so the noise differs across rounds. FoolsGold's
  history-similarity signal is genuinely attacked rather than accidentally preserved.
- No partially-missing metric series in any of the 314 committed histories.

---

## Note on the campaign

Cell 4 of lane 1a took 6100 s against ~1500 s for cells 2 and 3. That slowdown is my
fault: the CPU reproductions above ran multi-threaded torch alongside the sweep and
competed for CPU during the client-fit and aggregation phases. Later QA was kept
light. The campaign itself never faltered — GPU utilisation stayed at 93-98%, the
heartbeat never went stale, and no CUDA fault occurred.
