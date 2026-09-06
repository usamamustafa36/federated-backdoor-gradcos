# The paper you actually have

Written 5 September 2026, after the batch-counter finding turned out to generalise.

## The problem with the current framing

Ranked as a reviewer will see them, the current contributions are:

| # | contribution | how it reads |
|---|---|---|
| 1 | salience decides robustness | near-tautological; the manuscript concedes this itself |
| 2 | zero-sum noise evasion | **not novel** -- Related Work calls it "standard in the sybil literature", 3DFed and Yang et al. do stronger versions, and it is now contradicted for Krum |
| 3 | report FPR beside DR | good practice, not a research contribution |
| 4 | realizability audit | genuinely novel and checkable |
| 5 | GradCos | signal admittedly not new, fails on the triggers that matter, evadable, bimodal on one dataset |

The paper leads with 1, 2 and 5, and buries 4. That ordering is why it reads as a reject:
the headline claims are the weakest ones.

## The contribution that is actually there

In the canonical PyTorch federated pipeline, clients transmit `state_dict()`. That includes
BatchNorm's **`num_batches_tracked`** -- an integer counter incremented once per batch.

Three facts, each measured in this session:

**1. It dominates the update vector.** Measured on real CICIoT2023 with the committed
config: 79 per round on one coordinate out of 108,617, carrying **98.1% of the squared
norm**. On ResNet-18/CIFAR-10 -- the standard FL robustness benchmark -- **20 coordinates
out of 11,183,582 carry 68.6% at 500 samples per client and 99.4% at 5,000.**

**2. It is functionally dead.** Under PyTorch's default `momentum=0.1`, corrupting
`num_batches_tracked` by +100,000 leaves `running_mean`, `running_var` and eval-mode output
bit-identical. It is read only under `momentum=None`. The coordinate that dominates every
robustness decision has no effect on the model.

**3. It gets worse as the setting gets more realistic.** The share is analytic:

        counter share of ||delta||^2  =  L*B^2 / (L*B^2 + T^2)

with `L` BatchNorm layers, `B` batches per local round, `T` the norm of the real update.

| model | L | B=8 | B=16 | B=64 | B=157 |
|---|---|---|---|---|---|
| CNN+LSTM / CICIoT2023 | 1 | 49.9% | 80.0% | 98.5% | 99.7% |
| ResNet-18 / CIFAR-10 | 20 | 99.3% | 99.8% | 99.99% | ~100% |
| ResNet-50 / CIFAR-10 | 53 | 99.5% | 99.9% | 99.99% | ~100% |

More local data means more batches means more domination. The defect is mild in a toy
sanity check and total at deployment scale -- the worst possible failure mode for an
evaluation methodology, because it passes every small-scale test you would think to run.

### Scope -- read SURVEY.md before writing a word of this

The survey of real implementations came back mixed, and it rules out the strongest
framing. FoolsGold's and FLDetector's official code work from **gradients**, and RFCL uses
`model.parameters()`; all three are immune, because buffers never enter their vectors.

So **do not claim the field is measuring the wrong thing.** It is not, and two open repos
disprove it in a reviewer's first ten minutes.

What is true, and is enough: the defect is a property of the **transmission convention**.
Pipelines that ship `state_dict()` are affected; pipelines that ship gradients or
`parameters()` are not. And `state_dict()` is the convention Flower's own PyTorch example
uses -- `ArrayRecord(model.state_dict())`, verified on flwr 1.30 to carry
`num_batches_tracked` as an int64 on the wire -- so it is the default for anyone building
on the most widely adopted FL framework. `yjlee22/byzantineFL` (Krum, trimmed-mean, Fang,
on ResNet-18) is a published example that flattens every state_dict key.

The contribution is therefore a **silent measurement hazard in the canonical PyTorch FL
path**, not an indictment of prior results.

### Why it is a contribution and not a bug report

Every cosine-, distance- and norm-based Byzantine-robust rule assumes the transmitted
vector is a model update in a space where angle and distance carry meaning. In a
`state_dict()` pipeline it is not. The consequences are measurable, and we measured them:

| observation | previously attributed to | actually |
|---|---|---|
| FLAME's 0.20 clean-accuracy deficit | its clustering discarding 40% of honest clients ("no free lunch") | its DP noise scale `sigma = lambda * S`, where `S` is the counter-dominated median norm. Corrected: FLAME goes from 0.20 *below* FedAvg to 0.013 *above* |
| FLTrust's clean-accuracy deficit | attenuating honest updates that disagree with the root direction | `\|\|g0\|\|/\|\|gi\|\|` is the ratio of two batch counters -- the server runs 2 batches on 300 root rows, clients run 79 -- shrinking every update ~40x. Corrected: 0.556 -> 0.679 |
| FoolsGold's seed bimodality (s.d. 0.489, BSR range 0.003-0.926) | "it either locks onto the shared history early or never does" | history cosine is >= 0.9998 for every client pair; the weighting is decided by 4th-decimal residue |
| honest updates are "mutually well-aligned" at cos ~0.99 | clients optimising the same objective | 0.998 measured over the full vector, **0.831** over the trainable parameters -- the real agreement, compressed ~96x |
| Krum failing at m=0.2 and being repaired by a decorrelation attack | -- | distances cancel the shared constant, so Krum reads the real signal where cosine rules cannot |

That last row is the mechanism worth building the paper on: **cosine rules are blinded by a
shared constant, distance rules are alerted by it.** Whether a defense notices an attack
depends on which it reads, and nobody has been in a position to see that because the
constant was invisible.

## Proposed structure

Title, working: *"A Silent Measurement Hazard in PyTorch Federated Learning: When
Robust Aggregators Decide on a Bookkeeping Counter"*. Note the hedge in "PyTorch" and in
"when" -- both are load-bearing and neither should be dropped for punchiness.

1. **The defect.** What `state_dict()` transmission puts in the update vector; the analytic
   share; the measurements on CICIoT2023 and ResNet-18/CIFAR-10; the proof that the
   coordinate is inert.
2. **Scope, stated honestly.** This affects pipelines that transmit `state_dict()` with a
   BatchNorm model. The canonical Flower PyTorch pattern does exactly this. Approaches that
   transmit `parameters()` sidestep it (and then never sync BN statistics, a separate known
   problem); FedBN-style methods that keep BN local sidestep it too. **Which published
   implementations are affected is an empirical question this paper should answer by
   checking them, not assert.**
3. **Consequences.** The table above, each row re-measured on the corrected pipeline.
4. **The corrected picture.** Direction-vs-distance: what each family reads once the
   constant is gone, and how that changes the salience and evasion results.
5. **Trigger realizability.** Keep as-is. It is independently novel, it is the second real
   contribution, and it is untouched by the defect because it is a data-space analysis.
6. **GradCos.** Demote heavily or cut. As a proposed defense it is not competitive. As
   "what a corrected pipeline lets you measure" it can survive as a subsection.

## What this needs before it is submittable

1. **Survey real implementations.** The claim's strength is proportional to how many
   published pipelines are affected. Check the reference implementations of Krum, FLAME,
   FoolsGold, FLTrust and the Flower examples for `state_dict()` transmission. This is
   reading, not compute, and it is the highest-value remaining work.
2. **The corrected campaign.** Everything in the consequences table is currently 5-round
   smoke evidence. It needs the full run.
3. **A second architecture.** ResNet-18/CIFAR-10 numbers here are from an untrained
   forward/backward pass, not a real FL run. One real CIFAR-10 federated experiment would
   make the generality claim airtight rather than suggestive.
4. **Do not overclaim.** "Every FL paper is wrong" is false and will be caught. "Pipelines
   with this shape have this defect, here is the condition, here is who satisfies it, here
   is what changes" is defensible and still a strong result.
