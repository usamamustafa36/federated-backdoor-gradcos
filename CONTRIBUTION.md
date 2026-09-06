# The contribution, stated at the precision the evidence supports

This is the claim to build the paper on. Every number is measured; every hedge is
load-bearing. `SURVEY.md` has the implementation audit, `QA_FINDINGS.md` the defect
catalogue, `PUBLISHABILITY.md` the remaining risks.

## Claim

> In federated pipelines that transmit `state_dict()` -- the convention Flower's own
> PyTorch example uses -- BatchNorm's `num_batches_tracked` enters the update vector that
> Byzantine-robust aggregation rules decide on. The coordinate is inert under PyTorch's
> default `momentum`, yet it carries most of the vector's norm. Cosine-based rules are
> affected unconditionally; distance-based rules are affected as soon as clients hold
> different amounts of data. The result is that robustness rules are frequently ranking
> clients by how many batches they ran rather than by what they computed.

## The four facts it rests on

**1. It dominates.** One coordinate in 108,617 carries **98.1%** of the squared norm of a
real CICIoT2023 update (measured, real loader, real config). On ResNet-18/CIFAR-10, **20
coordinates in 11,183,582** carry 68.6% at 500 samples/client and **99.4%** at 5,000.

**2. It is inert.** Under PyTorch's default `momentum=0.1`, corrupting
`num_batches_tracked` by +100,000 leaves `running_mean`, `running_var` and eval-mode output
bit-identical. It is read only under `momentum=None`.

**3. It scales the wrong way.** Share = `L*B^2 / (L*B^2 + T^2)` for `L` BatchNorm layers,
`B` batches per local round, `T` the real update norm. For ResNet-18 it is 99.3% at eight
batches. **The more data a client holds -- the closer to deployment -- the worse it gets.**

**4. It hides in exactly the setting people debug in.**

| | counter share of Krum's pairwise distances | cosine floor |
|---|---|---|
| IID, equal shards | **0.00%** (cancels in `v_i - v_j`) | 0.998 |
| shards +/-20% | **81.6%** median | 0.998 |
| Dirichlet non-IID | **99.8%** median | 0.998 |

Distance rules are protected only under exactly-equal batch counts. Cosine rules are never
protected. Measured on this project's own partitioner: IID 0.00%, Dirichlet alpha=0.5
52.9% median / 88.2% max, alpha=0.1 up to 98.1%.

## What it explains that was previously unexplained

| observation | attributed to | mechanism |
|---|---|---|
| FLAME's 0.20 clean-accuracy deficit ("no free lunch") | clustering discarding 40% of honest clients | **mostly the class weighting, not the counter.** A controlled A/B isolating the counter fix gives FLAME only **+0.012**; the 0.499 -> 0.72 recovery is almost all the weighting change. The `sigma = lambda*S` inflation is real but its effect at 16 batches/round is small -- it should grow with B, which is what the scaling experiment tests |
| FLTrust's clean-accuracy deficit | attenuating honest updates that disagree with the root | `\|\|g0\|\|/\|\|gi\|\|` is a ratio of batch counts (server 2, clients 79): every update shrunk ~40x. Corrected: 0.556 -> 0.679 |
| FoolsGold's seed bimodality (s.d. 0.489) | "locks on early or never does" | history cosine >= 0.9998 for every pair; weighting decided by 4th-decimal residue |
| "honest clients are mutually well-aligned", cos ~0.99 | shared objective | 0.998 over the full vector vs **0.831** over parameters -- real agreement, compressed ~96x |
| **"heterogeneity flips Krum from robust to backdoored"** | non-IID changing update geometry | shard sizes differ, so 53-99% of Krum's distance matrix is batch-count clustering. Krum ranks clients by how much data they hold |
| Krum *repaired* by a decorrelation attack (BSR 0.948 -> 0.001) | -- | distances cancel the shared constant; the attack's noise is the first thing Krum can actually see |

The last two rows are the paper's own previously-hedged results. They now have mechanisms.

## RETRACTION: the scaling prediction failed, and the FoolsGold outcome is unestablished

Recorded before anything downstream of it is written.

**The scaling law does not translate into outcomes.** The prediction was that the defect's
effect grows with batches per local round, because the counter's share of the norm does
(80% -> 96% -> 99% at B = 16, 40, 79). Measured, non-IID, 15 rounds, identical config:

| defense | attacked | B=16 | B=40 | B=79 |
|---|---|---|---|---|
| FoolsGold | yes | **+0.460** | +0.085 | **-0.189** |
| FLAME | yes | +0.015 | +0.017 | +0.077 |
| GradCos | yes | -0.017 | -0.004 | -0.003 |

FoolsGold's effect shrinks and then **reverses sign**. Only FLAME trends the predicted way,
weakly. The counter's share of the norm is arithmetically certain; its effect on what a
defense *decides* is not a monotone function of it, and the paper must not imply otherwise.

**The FoolsGold outcome numbers are single runs of a bimodal defense.** This project's own
Sec. 7.11 reports FoolsGold at s.d. 0.489 across seeds, BSR spanning 0.003 to 0.926. Every
cell above is one draw. The +0.460 and the -0.189 may both be samples from that bimodality.
I described this result as "airtight" earlier; it is not, and the evidence that it is not
was already in the manuscript I had read.

**What survives the retraction.** The mechanism probe fed *identical* client histories
through both code paths -- no training stochasticity involved -- and produced weights
`[0,1,0,1,0,0,0,0,0,0]` against `[.19,1,.74,1,0,1,0,.19,1,.77]`: 8 clients zeroed versus 2.
That was then reproduced in closed form from the similarity distribution alone. **The
mechanism is real and demonstrable. The magnitude of its effect on trained outcomes is
not yet established**, and a five-seed A/B is running to settle it.

## The one large effect, with its mechanism verified

FoolsGold is the defense the defect hurts most, and the mechanism is now measured rather
than hypothesised. Real pipeline, non-IID, ten clients, `signal_subspace` toggled:

| | pairwise history cosine | FoolsGold weights | clients zeroed | clean acc under attack |
|---|---|---|---|---|
| defect present | 0.820 .. 0.990 | `[0,1,0,1,0,0,0,0,0,0]` | **8 of 10** | **0.110** |
| corrected | -0.027 .. 0.795 | `[.19,1,.74,1,0,1,0,.19,1,.77]` | 2 of 10 | **0.701** |

FoolsGold's whole function is to down-weight clients whose update histories are *too
similar to each other*. The counter compresses every pairwise similarity into the
0.82-0.99 band, so it reads the entire cohort as a sybil swarm and discards eight of ten
clients. The global model then trains on two clients and falls to 0.110 -- below the 0.125
chance line for eight classes.

The surviving pair is diagnostic: client 1 holds 399 rows and runs **2 batches** where
everyone else runs 8. Under the defect it is the client whose counter differs most, so it
looks least like a sybil and is kept. FoolsGold is selecting on shard size.

### The mechanism, step by step

FoolsGold's weighting is *relative*, and that is what turns compression into collapse.
Reproduced exactly in closed form -- the synthetic chain below returns the same weight
vector the real run produced, `[0,1,0,1,0,0,0,0,0,0]`:

| step | defect present | corrected |
|---|---|---|
| max pairwise similarity per client | 0.99 for the majority; **0.82-0.86** for clients with unusual batch counts | genuinely spread, 0.55-0.80 |
| `1 - max_sim` | 0.010 for the majority, **0.18** for the odd ones | 0.20-0.45, all comparable |
| divide by the maximum | majority crushed to **0.05**; the outlier sets the scale at 1.0 | 0.44-1.00 |
| logit sharpening, clip to [0,1] | majority -> **0** | 0.28-1.00 |
| clients retained | **2 of 10** | 10 of 10 |

The counter compresses the cohort into a narrow high-similarity band. Whichever clients
happen to run an unusual number of batches then sit outside that band, become the reference
point for the max-normalisation, and every other client is divided down and logit-crushed
to zero.

**FoolsGold ends up training exclusively on the clients holding the most unusual amount of
data** -- the opposite of what a sybil defense is supposed to do, and arrived at without any
adversary being involved. In the measured run the survivor was the client with 399 rows and
2 batches against everyone else's 8.

**A caveat on how this was established.** A first synthetic probe -- random Gaussian
histories with the counter appended -- showed *no* effect: weights stayed at 1.0 for every
client. That probe was wrong, because random histories sit at cosine ~0 and the counter
cannot compress them into FoolsGold's decision band. Real histories sit at ~0.8 before the
counter, which is precisely the regime where pushing them to 0.99 flips the outcome. The
synthetic test was too easy, and it would have produced a false negative had it been
trusted.

## What must not be claimed

FoolsGold's and FLDetector's official implementations work from **gradients** and are
immune. RFCL uses `model.parameters()` and is immune. **"Byzantine-robust FL is evaluated
on a bookkeeping counter" is false** and two open repositories disprove it in ten minutes.

The defect is a property of the transmission convention, not of any defense, and both
conventions are in active use. That is the sentence to write.

## A correction I had to make to my own analysis

I initially attributed FLAME's clean-accuracy recovery (0.499 -> 0.725) to the counter fix.
A controlled A/B -- same config, one flag -- shows the counter fix alone is worth **+0.012**
to FLAME. The recovery was almost entirely the class-weighting change, which had been
applied at the same time.

The lesson generalises and belongs in the paper's methodology: **the two fixes were changed
together and I read the joint effect as the effect of one of them.** That is exactly the
error the `signal_subspace` toggle now exists to prevent, and every consequence claimed in
the table above must be established with it rather than by comparing across code versions.

The `sigma = lambda*S` mechanism is still real -- `S` is counter-dominated, so the DP noise
is inflated. But at the smoke configuration's 16 batches/round the inflation is only ~2.2x,
not the ~10x of the full 79-batch configuration. **The smoke test is the weakest possible
case for the claim**, which is why the scaling experiment matters.

## Still required

1. **The corrected campaign.** Everything in the consequences table above is 5-to-10-round
   smoke evidence. It is directionally consistent and mechanistically predicted, but it is
   not results.
2. **External demonstration.** `yjlee22/byzantineFL` is affected, uses ResNet-18, and
   implements Krum/trimmed-mean/Fang. Showing its published setup change under the fix
   turns "could" into "does". CIFAR-10 is downloading for this.
3. **A wider survey.** Six implementations establishes that both conventions exist. Twenty
   would let the paper say which dominates.
4. **Restraint.** The temptation is to write the strong version. The strong version is
   false and the narrow version is still a good paper.
