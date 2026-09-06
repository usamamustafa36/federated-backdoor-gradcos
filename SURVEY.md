# Which implementations actually have the defect?

Survey of 5 September 2026. The question: how many published federated-learning
robustness pipelines flatten `state_dict()` (and so put BatchNorm's
`num_batches_tracked` into the vector their aggregation rule decides on)?

**The honest answer is: a minority of reference implementations, but the default path of
the most widely used framework.** That is a narrower claim than "the field is measuring the
wrong thing", and it is the one the evidence supports.

## Verified, by reading the code

| implementation | how per-client updates are vectorised | affected |
|---|---|---|
| **FLDetector** (official, KDD 2022) | MXNet `collect_params()`, filtered `grad_req != 'null'` | **No** — buffers excluded by construction |
| **FoolsGold** (official, RAID 2020) | raw gradient vectors, `np.reshape(this_delta, (n, d))` | **No** — gradients only |
| **RFCL** (`EbtisaamCS/RFCL`) | `model.parameters()` / `named_parameters()` | **No** — `parameters()` excludes buffers |
| **byzantineFL** (`yjlee22/byzantineFL`, Krum / trimmed-mean / Fang) | `for name in v: v[name].reshape([-1])` then `torch.cat(list(v.values()))` over a **state_dict**, on **ResNet-18** | **Yes** |
| **Flower `quickstart-pytorch`** (official example) | `ArrayRecord(model.state_dict())` sent; `to_torch_state_dict()` received | **Yes** |
| **This paper** | `[v for v in model.state_dict().values()]` | **Yes** |
| **OOD_Federated_Learning** (Wang et al., *Attack of the Tails*, NeurIPS 2020 -- cited by this paper) | `torch.cat([p.view(-1) for p in net.parameters()])` | **No** |
| **DBA** (Xie et al., ICLR 2020 -- cited by this paper) | `model.named_parameters()` | **No** |
| **iba** (`sail-research/iba`) | `net.parameters()` | **No** |

### Running tally: 6 immune, 3 affected

The `parameters()` convention **dominates published research implementations.** Of nine
checked, six never place a buffer in the vector. Two of the immune ones -- *Attack of the
Tails* and *DBA* -- are cited in this very manuscript.

The three affected are: this project, one GitHub reimplementation of Krum/trimmed-mean/Fang,
and **Flower's own documented PyTorch example**.

That is the shape of the finding, and it is narrower than it first looked. It is not that
the literature measured the wrong thing. It is that **the most widely adopted FL
framework's canonical pattern silently does**, which matters going forward -- for work
built on Flower -- rather than backwards.

Flower's example is the important row. It is the official, documented PyTorch entry point
for the most widely adopted FL framework, and the modern `ArrayRecord` API takes a
`state_dict` directly -- the docstring's own PyTorch example is
`record = ArrayRecord(model.state_dict())`. Verified on flwr 1.30.0 that the round trip
carries `num_batches_tracked` as an int64 on the wire.

## The refinement that makes this sharp: why nobody noticed

`torch.cat(list(state_dict.values()))` silently promotes the int64 counter to float32 and
includes it -- verified. But whether that *matters* depends on what the rule computes, and
the split is clean:

**Distance rules (Krum, Bulyan, and `byzantineFL`'s `euclid`)** compute `v_i - v_j` first.
If every client ran the same number of batches, the counter is identical across clients and
**cancels exactly**. They are fully protected -- but only then.

**Cosine rules (FLAME, FoolsGold, FLTrust, GradCos)** normalise by `||v||`, which the
counter inflates. Nothing cancels. They are affected always.

Quantified, L=20 (ResNet-18), T=3.0 (measured trainable norm):

| setting | counter share of pairwise sq. distance | cosine floor |
|---|---|---|
| IID, every client 16 batches | **0.00%** | 0.998 |
| mild heterogeneity, shards +/-20% | **81.6%** median, 96.5% max | 0.998 |
| Dirichlet non-IID, realistic spread | **99.8%** median | 0.998 |

**This is why the defect has gone unnoticed.** It is invisible for distance rules in
exactly the configuration people debug and sanity-check in -- IID with equal shards -- and
dominant in the configuration that motivates the whole field. A 20% shard imbalance, which
nobody would even call heterogeneous, already hands 82% of Krum's distance matrix to a
batch counter.

It also retro-explains this paper's own unexplained result. Sec. 9 reports that
heterogeneity "flips Krum from robust to backdoored" and reads it as evidence that non-IID
data changes the geometry defenses rely on. It does -- but not for the reason given: under
Dirichlet partitioning, shard sizes differ, and Krum's distance matrix becomes ~99.8%
batch-count clustering. Krum stops ranking clients by their updates and starts ranking them
by how much data they hold.

That finding was already in the manuscript, unexplained, marked single-seed and hedged.
The mechanism is now measurable.

## What this means for the claim

**Do not write:** "Byzantine-robust FL is evaluated on a bookkeeping counter."
The original FoolsGold and FLDetector implementations are immune. So is any
gradient-based or `parameters()`-based pipeline. That sentence would be caught in review
and would sink the paper.

**Write instead:** the defect is a property of the *transmission convention*, not of any
defense. Two conventions coexist in the literature:

- **gradient / `parameters()`**: buffers never enter the vector. Immune. BN statistics are
  then never synchronised, which is a separate and known issue (and the motivation for
  FedBN).
- **`state_dict()`**: buffers enter the vector. Affected. This is the convention Flower's
  own PyTorch example uses, so it is the default for anyone building on it.

The contribution is then: *a silent measurement hazard in the canonical PyTorch FL path*,
with three properties that make it worth a paper --

1. **Severity.** 68-99.99% of the squared norm, depending on batches per round (`L*B^2 /
   (L*B^2 + T^2)`). On ResNet-18 it is 99.3% at only 8 batches.
2. **Invisibility.** Mild in small sanity checks, total at realistic client dataset sizes.
   It passes every scale of test one would think to run before scaling up.
3. **Consequence.** Measured, on the corrected pipeline: FLAME's clean-accuracy deficit
   disappears, FLTrust's shrinks, FoolsGold's seed bimodality is explained, and Krum's
   response to a decorrelation attack inverts.

That is defensible, novel, and still strong. It is *not* a claim that prior published
numbers are wrong, and it must not be written as one.

## What would strengthen it further

- Widen the sample. Six implementations is enough to show both conventions exist; twenty
  would let the paper say something quantitative about which dominates.
- Check whether any affected implementation's *published* numbers change under the fix.
  Right now the only pipeline where that has been demonstrated is this paper's own.
- `yjlee22/byzantineFL` is the best external candidate: it is affected, it uses ResNet-18
  where the counter share is ~99%, and it implements Krum, trimmed-mean and Fang. Re-running
  one of its experiments with buffers excluded would turn "this could change results" into
  "here is a published setup where it does."
