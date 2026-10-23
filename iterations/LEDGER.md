# Iteration ledger

Each iteration is one agent. It reads this file first, appends exactly one entry at the
bottom when done, and leaves the repo in a state the next agent can build on.

Goal: a journal manuscript that a hostile expert reviewer would accept without major
revision. Minimum 50 iterations. Stop only when an iteration scores the paper
"Accept as is / minor" with no open blocker AND the two iterations before it agree.

## Entry format

    ## Iteration N - <date> - <one-line focus>
    - Reviewer score before (1-10) and verdict:
    - Blockers found (ranked):
    - What I changed (files, experiments launched, with log paths):
    - Evidence (numbers measured, with source file - never hand-typed into the paper):
    - Running jobs left for the next agent (PID, log, ETA):
    - Score after / verdict:
    - Top 3 priorities for the next iteration:

---

## Iteration 1 - 2026-10-21 - Baseline review, framing/venue decision, archive void results, launch CPU post-fix A/B (P1)

### Baseline review (hostile JISA reviewer)
- **Reviewer score before: 2/10, REJECT.** The manuscript (`paper/main.tex`) is still the
  pre-defect paper "Direction Is Not Enough". It does not mention `num_batches_tracked`
  anywhere, and every number it printed came from the 321 pre-fix result files, measured
  through the broken signal path. The scientific record (CONTRIBUTION.md, QA_FINDINGS.md)
  has moved on; the paper has not.

**What the paper currently claims vs. what the evidence supports**

| paper claims | status after the counter defect |
|---|---|
| Salience (rotation off consensus) decides robustness; dose-response | Void. Salience gap was 4.2e-5 through the broken path; re-measure. The claim is also close to tautological (REFRAME.md). |
| Zero-sum noise cuts colluder cosine "0.99 to below 0.35" (abstract, intro) | Void, and a hand-typed literal. The 0.99 floor *was* the counter. The pilot smoke shows 0.855 -> 0.236 post-fix, at another scale. |
| "Every direction-based rule" falls to the evasion | Contradicted already (Krum repaired, BSR 0.948 -> 0.001), and Krum is a distance rule. |
| FLAME 0.40 FPR / clean-accuracy deficit ("no free lunch") | Void. Pilot A/B: mostly class weighting, counter fix only +0.012. "0.40+/-0.04" is hand-typed in the intro bullet (rule violation). |
| GradCos ties FLTrust at +CA | Void; FLTrust's deficit was the counter ratio. GradCos is not competitive anyway. |
| FPR must accompany DR | Survives as good practice; not a contribution. |
| Realizability audit | **Survives** (data-space, no model updates). Its macros still resolve. |

**What the evidence does support** (pilot, GPU, Sep 5-6; now in `results/_pilot_postfix_sep5/`):
counter carries 98.1% of squared update norm (real config), is inert under default momentum,
compresses honest cosine 0.831 -> 0.998, supplies 53-99% of Krum distances when shard sizes
differ; FoolsGold mechanism (8/10 clients zeroed vs 2/10) reproduced in closed form. NOT
supported: any outcome effect at p<0.05 (FoolsGold attacked CA +0.209, p=0.07-0.10, n=5),
the scaling law (refuted), generality across defenses (4/5 <= 0.03), "the field is wrong"
(6 of 9 surveyed implementations immune).

**Blockers, ranked by rejection likelihood**
1. Manuscript framing and every result are void/obsolete; no post-fix campaign at scale.
2. No controlled, multi-seed, significance-tested estimate of the defect's *outcome* effect
   per defense (the only outcome effect is p~0.07, n=5).
3. Hand-typed literals in abstract/intro ("0.99 to below 0.35", "0.40+/-0.04").
4. External validity: one tabular CNN+LSTM, 1 BN layer. Needs a second architecture
   (ResNet-18/CIFAR-10 or an MLP+BN) and an external pipeline (yjlee22/byzantineFL, Flower
   example) -- now CPU-bound, so must be small.
5. No 2023-26 defense evaluated (FLDetector 2022 implemented, not yet in paper).
6. The analytic part is thin: the share formula exists but nothing proves *why* cosine
   rules are always hit and distance rules only under unequal batch counts.
7. Detector weak (CA ~0.71 at the scaled config vs majority floor 0.652); must report floor + RF.

### Decision: framing and venue
- **Framing (binding for later iterations unless evidence overturns it):** rewrite the paper
  around the measurement hazard, per REFRAME.md: working title *"A Silent Measurement Hazard
  in PyTorch Federated Learning: When Byzantine-Robust Aggregators Decide on a BatchNorm
  Counter"*, with federated intrusion detection (CICIoT2023) as the application. Structure:
  (1) the defect + exact analytic decomposition, (2) implementation survey (scope, honestly
  narrow), (3) controlled A/B consequences per defense family (P1), (4) mechanism case studies
  (FoolsGold collapse, FLTrust rescaling, Krum under unequal shards), (5) realizability audit
  as the second contribution, (6) GradCos demoted to a short subsection or cut; salience and
  evasion re-measured only as "what a corrected pipeline lets you see".
- **Venue: stay with Elsevier JISA.** The evidence does not yet support TIFS/TDSC/USENIX:
  scope is 3 of 9 implementations, and no outcome effect is significant yet. Upgrade
  condition (re-assess when P1 lands): >= 2 defenses with Holm-significant outcome effects
  under realistic (non-IID) data AND a second-architecture/external-pipeline replication.
  If both hold, Computers & Security or IEEE TIFS become arguable.
- **Analytic result to write next (exact, cheap, reviewer-proof):** for client deltas
  d_i = (u_i, b_i) split into trainable/buffer parts with buffer norm share s_i,
  cos(d_i,d_j) = sqrt((1-s_i)(1-s_j)) cos(u_i,u_j) + sqrt(s_i s_j) cos(b_i,b_j); and
  ||d_i-d_j||^2 = ||u_i-u_j||^2 + ||b_i-b_j||^2 with the counter term L(B_i-B_j)^2.
  Hence cosine rules see the trainable signal shrunk by (1-s) (s=0.97 -> ~33x) whatever the
  batch counts, while distance rules are untouched iff B_i = B_j. First P1 run confirms the
  shape: Dirichlet, buffer_norm_share 0.97, buffer_dist_share 0.96, pair cosine 0.94 full
  vs 0.12-0.48 trainable.

### What I changed
- `results/`: ran `scripts/archive_pre_counterfix.sh` -> 321 pre-fix files + residual/ +
  summary CSVs to `results/_pre_counterfix/`. Moved the 164 Sep-5 post-fix pilot files
  (ab*, sd*, scb*, integ*) to `results/_pilot_postfix_sep5/` with a README (valid, but
  mixed scales; excluded from the generator). Nothing deleted.
- `paper/numbers.tex` regenerated: 43/784 macros resolve (realizability etc.); main.tex now
  shows 187 `[PENDING RUN]` markers. Honest state; the submission gate fails as it should.
- `src/fl/engine.py`: new `_defect_diagnostics`, logged every round in both modes
  (`buffer_norm_share`, `buffer_dist_share`, `pair_cos_full`, `pair_cos_sig`). Logging only;
  no decision reads it. Smoke-tested on CPU.
- `paper/aggregate_multiseed.py`: skips `results/postfix_*` (signal_subspace is not in its
  group key, so it would have averaged the defect arm with the fixed arm).
- `paper/analyse_postfix.py` (new): pairs full/trainable by seed; arm means/SDs, paired diff,
  95% t-CI, paired t and Wilcoxon p, Holm across defenses; writes
  `results/postfix_p1/summary_pairs.{csv,md}` and `paper/numbers_postfix.tex` (\pf... macros,
  \PENDING when < 3 paired seeds). Validated on the Sep-5 sd* pilot: reproduces FoolsGold
  attacked CA +0.209 (p=0.099 with the last-5-round metric).
- `configs/p1_{full,trainable}.yaml` (copies of _ab_*, out_dir results/postfix_p1, Krum/Bulyan
  f=2 = true malicious count; Bulyan clamps f at n=10 -- must be stated in the paper).
- `experiments/postfix/run_p1.sh` (new): resumable xargs queue, 6 lanes x 2 threads, CPU.
- RESUME_HERE.md: dated current-state header.

### Running jobs left for the next agent
- **P1 campaign**: launcher PID 448482 (`bash experiments/postfix/run_p1.sh`, setsid/nohup),
  log `results/postfix_p1/campaign.log`, per-job logs `results/postfix_p1/log_*.log`,
  results `results/postfix_p1/p1{full,trainable}_{dirichlet,iid}_*.json`.
  960 cells (96 jobs). Measured under current machine load: ~18 min/cell/lane (first cell
  03:43 -> 04:01), so ~48 h total; seeds 42-46 (both partitions, all defenses) finish first,
  ~24 h. If it dies, re-run the same command: completed cells are skipped.
  Check: `ls results/postfix_p1/*.json | wc -l` (target 960); analyse:
  `python3 paper/analyse_postfix.py`.
- GPU: down (CUDA unknown error). CPU-only per user decision.

- **Score after: 2/10, REJECT** (unchanged by design: the paper is now honestly empty rather
  than wrong; the infrastructure to fill it is running).

### Top 3 priorities for the next iteration
1. **Start the rewrite** (keep `main.tex.pre-reframe.bak`): new title/abstract/intro and a
   "The defect" section with the exact cosine/distance decomposition above as a proposition
   with proof, measured shares from `\pfDiag...` macros. Remove the hand-typed literals
   ("0.99 to below 0.35", "0.40+/-0.04"). Wire `\input{numbers_postfix}` into main.tex.
2. **Harvest P1 partially** (seed block 42-46 lands first): build the consequences table
   (defense x family x partition: defect vs fixed CA/BSR/DR/FPR with CI and Holm p) from
   `numbers_postfix.tex`. Report null results as nulls.
3. **CPU-sized external validity** (can run alongside P1 only if cores allow; P1 already uses
   12): plan a small second-architecture run (e.g. MLP-with-BN or ResNet-8 on a CIFAR-10
   subset; check whether the CIFAR download in data/ completed) and a Flower-example
   reproduction of the state_dict wire format; queue it after P1 rather than competing for cores.

## Iteration 2 - 2026-10-21 - Reframe the front matter around the counter; Proposition 1 with proof; generated defect probe; P1 table wired

- **Reviewer score before: 2/10, REJECT** (iteration 1's state: old "Direction Is Not Enough"
  paper, hand-typed headline literals, no mention of the defect).
- **Blockers found (ranked):**
  1. No outcome evidence yet: P1 is ~1% done (7/960 cells at 04:18). Every consequence claim is
     \PENDING. Still the decisive blocker.
  2. Body (Secs. 4-9) still follows the pre-reframe structure (salience, evasion, GradCos, FPR on
     the void grid; 125 `ms` + ~120 other old-lane \PENDING macros from run_remediation lanes that
     will never be re-run in that form). A reviewer would see two papers stitched together.
  3. External validity: one model with a single BN layer; no ResNet/CIFAR or real Flower run.
     Note: torchvision is broken on this box (`operator torchvision::nms does not exist`), so a
     ResNet probe needs a hand-written ResNet or a torchvision reinstall.
  4. Survey is 9 implementations read by hand (SURVEY.md); counts are now a table in the paper,
     but there is no artefact (commit hashes / file:line) a reviewer can check.
  5. No 2023-26 defense; detector strength vs majority floor (0.652) not reported.
- **What I changed:**
  - `paper/main.tex` (backup `paper/main.tex.pre-reframe.bak`): new title ("A Silent Measurement
    Hazard in PyTorch Federated Learning: When Byzantine-Robust Aggregators Decide on a BatchNorm
    Counter"), new abstract (247 words, only macros + config parameters), new introduction and
    contributions, new Related-Work paragraph (BN/FedBN/model state), new Sec. 3 "The Defect"
    with **Proposition 1** (exact norm/cosine/distance decomposition incl. counter term L B_i^2,
    L(B_i-B_j)^2, truncation caveat epsilon), **Corollary 1** (|cos d - cos b| <= 2(1-s); trainable
    cosine weight <= 1-s), **Corollary 2** (distance exposure iff batch counts differ), norm-based /
    coordinate-wise predictions (median/trimmed mean = negative controls), inertness paragraph,
    Table `tab:probe`, Sec. 3.1 scope + Table `tab:survey` (9 implementations from SURVEY.md),
    "the fix" paragraph; new Sec. 8.1 `sec:p1` (A/B design, CPU reductions stated) with Table
    `tab:p1` (12 rules x {Dir, IID}: CA clean, CA attacked, BSR attacked; Def/Fix/Delta/p_Holm),
    all cells \pf macros; new Conclusion. Old hand-typed "0.99 to below 0.35" and "0.40+/-0.04"
    are gone from abstract/intro (they survive in old body Sec. 8.x, allowlisted, to be cut when
    the body is rewritten). `\input{numbers_postfix}` and `\input{numbers_defect}` wired in.
  - `paper/highlights.tex`: rewritten, no numbers.
  - `paper/refs.bib`: + ioffe2015batchnorm (PMLR 37:448-456, verified), li2021fedbn (ICLR 2021,
    verified).
  - `experiments/counter_defect/probe_defect.py` (new, CPU, 26 s, deterministic) ->
    `results/defect_probe.json` + `paper/numbers_defect.tex` (\df macros).
  - `paper/analyse_postfix.py`: + `\pfDiagCosBand{Dir,Iid}` = 2(1 - median buffer share).
  - `paper/tools/check_manuscript.py`: pending-macro count now includes numbers_postfix.tex and
    numbers_defect.tex (\providecommand); `pf` lane label. `paper/Makefile`: new deps.
- **Evidence (all generated):** probe (`results/defect_probe.json`): 108,488 trainable / 129 buffer
  coords, 1 BN layer; counter +1e5 under momentum=0.1 -> running mean/var/logit max|diff| = 0
  exactly; under momentum=None -> 5.0e-3 / 1.3e-3; Prop. 1 holds on real local updates (B=16 vs 11)
  to 8.9e-16 (cos) and 1.2e-16 rel. (dist); full cos 0.989 vs trainable 0.154; counter 86.5% of
  ||d_i||^2, 84.6% of ||d_i-d_j||^2. P1 diagnostics (6 Dirichlet runs so far, will update
  automatically): buffer norm share 0.974, dist share 0.964, cos full 0.906 vs trainable 0.161,
  cosine band 0.053.
- **Build/check:** `latexmk` clean (rc 0, 21 pp); check_manuscript: all PASS except the gate
  (548 unresolved: 288 pf from P1, 244 old-lane macros, 16 literal) -- expected.
- **Running jobs left for the next agent:** P1 untouched. Launcher shell PID **448486**
  (`bash experiments/postfix/run_p1.sh`; iteration 1 recorded 448482/448483 for its parents),
  log `results/postfix_p1/campaign.log`, 7/960 cells at 04:18; ETA ~48 h (seeds 42-46 ~24 h).
  Harvest: `python3 paper/analyse_postfix.py && cd paper && make`.
- **Score after: 3/10, REJECT** (framing, title, abstract and analytic core are now right and
  reviewer-checkable; still no outcome evidence and the body is the old paper).
- **Top 3 priorities for the next iteration:**
  1. **Rewrite the body (Secs. 4-9)** around the new structure: move threat model/setup to the
     P1 scale as the main setup; cut or demote GradCos (Sec. 5.3), salience (8.4), evasion (8.5),
     residual (8.7), ratio/FLNET/non-IID subsections that depend on void run_remediation lanes
     (move superseded text to `paper/_superseded_body.tex`, keep the .bak); write mechanism case
     studies (FoolsGold collapse in closed form, FLTrust B_0/B_i rescaling, Krum under unequal
     shards) as analytic+probe subsections that need no long runs. Remove the old allowlisted
     literals (0.99, 0.35, 0.16, 0.33, ...) with the text that carries them.
  2. **Harvest P1** as it lands (seeds 42-46 first): fill the Results sentence of Sec. 8.1 and the
     abstract/conclusion \PENDING from `\pf` macros only; report nulls as nulls.
  3. **Second architecture on CPU** after or beside P1 if cores allow: extend probe_defect.py to a
     hand-written ResNet-18 (torchvision broken) for the L=20 share/Prop-1 check, and a small real
     FL run (MLP+BN or ResNet-8 on a CIFAR-10 subset; check data/ for CIFAR). Also put survey
     evidence (repo, commit, file:line) in the replication package.

## Iteration 3 - 2026-10-21 - Rewrite Secs. 4-9 around the counter hazard; mechanisms + retro section; ResNet-18 geometry probe; harvest P1 (70/960)

- **Reviewer score before: 3/10, REJECT** (iteration 2: right front matter, old body with
  244 void-lane macros, no outcome evidence).
- **Blockers found (ranked):**
  1. **The attack may not implant at P1 scale.** In every completed P1 rule (FLAME, FLTrust,
     FoolsGold, Dirichlet, seeds 42-46) attacked BSR ~= the rule's own clean-run BSR
     (0.02-0.03), in both arms. Sep-5 pilot FedAvg at the same scale (5 rounds) had BSR 0.04
     (`results/_pilot_postfix_sep5/integ_*fedavg*`). If P1's FedAvg confirms it, P1's BSR
     columns are uninformative by construction and the paper can make NO backdoor-robustness
     claim. P1 FedAvg Dirichlet is the last rule in the queue's Dirichlet block (~10 h after
     P1 start). The paper now says this explicitly (Sec. 6.2, Sec. 8 limitations).
  2. P1 still ~7% done; 9/12 rules and all of IID pending. Interim prose is marked
     `% RE-CHECK` in main.tex.
  3. Outcomes measured on one architecture (L=1). Geometry now verified on ResNet-18 (below),
     outcomes not.
  4. Survey artefact (commit hashes, file:line) still missing; FLAME hypothesis (ordering
     preserved by the affine map) unverified; donor clean-model BSR screen not generated.
- **What I changed:**
  - `paper/main.tex` (backup `paper/main.tex.pre-body-rewrite.bak`; old body moved verbatim to
    `paper/_superseded_body.tex`, not \input): new Sec. 4 Experimental Setup at the P1 scale
    (CPU reductions and their consequences stated), Sec. 5 "Aggregation rules and what the
    decomposition predicts" with Table `tab:rules` (12 rules x decision statistic x predicted
    exposure; FedAvg/median/trimmed mean = arms-identical negative controls, verified in code:
    they never call `self.sig`), Sec. 6 Results: 6.1 transmitted geometry + Fig.
    `fig:geometry`; 6.2 controlled A/B (Table `tab:p1` + new Table `tab:p1flag` for FPR/DR of
    the 7 excluding rules; interim results paragraph; explicit BSR-floor paragraph); 6.3
    Mechanisms: **Corollary 3** (FLTrust excludes no one under the defect, cos >= s*kappa-(1-s);
    rescaling -> B0/Bi) with proof, FoolsGold history-share bound and residue-amplification
    argument, FLAME null with a stated (unverified) ordering hypothesis, distance rules and
    negative controls PENDING; 6.4 "What the counter did to an earlier version of this study"
    (FLTrust never excludes / FLTrust CA cost / FoolsGold bimodality / colluder cosine ~1 and
    the evasion = counter artefacts, withdrawn; FLAME FPR survives). Sec. 7 realizability kept,
    salience/FLNET references removed, hand-typed donor-screen literals removed (\PENDING).
    Sec. 8 Discussion (why it survives review, recommendations, limitations incl. attack
    strength). Intro roadmap, a 5th contribution bullet, related-work "Evaluating robust
    aggregation" paragraph and conclusion rewritten. GradCos demoted to "one more cosine rule".
    All 244 old-lane macro refs and all old figures (fig_dr_fpr, fig_tradeoff, fig_dose,
    fig_evasion) are gone.
  - `paper/analyse_postfix.py`: + `\pfDiagNormInfl{Dir,Iid}` (=1/sqrt(1-s), norm inflation for
    NormClip/FLAME clip+noise), `\pfCellsDone`, `\pfCellsTarget`.
  - `paper/make_fig_p1.py` (new) -> `paper/figs/fig_p1_geometry.pdf` (per-round cosine full vs
    trainable, buffer norm/dist share; *.pdf is gitignored, regenerate with the script or
    `make numbers`). Makefile `numbers` target runs both scripts.
  - `experiments/counter_defect/probe_resnet.py` (new; hand-written CIFAR ResNet-18, CPU, 3 min,
    2 threads) -> `results/defect_probe_resnet.json`, `paper/numbers_defect_resnet.tex`
    (\dr macros); Table `tab:probe` now has a ResNet-18 column; new paragraph in Sec. 3.
  - `paper/tools/check_manuscript.py`: reads numbers_defect_resnet.tex; removed the obsolete
    allowlisted literals (0.99, 0.35, 0.16, 0.33, 0.85, donor screen, FLNET); added SGD 0.01/0.9.
- **Evidence (generated):** P1 (`results/postfix_p1`, 70 cells, Dirichlet s42-46): FoolsGold
  clean CA defect 0.584 vs fixed 0.712, diff +0.129 [0.031, 0.226], p_H 0.065 (n=5), clean FPR
  0.800 vs 0.436; FLTrust defect DR=FPR=0 exactly (Corollary 3), fixed clean FPR 0.592
  [CI 0.451, 0.733] p_H 0.001, attacked DR 0.46 / FPR 0.52; FLAME no change (clean FPR 0.396 both
  arms, CA diff -0.000). Diagnostics: buffer norm share 0.972, dist share 0.957, cos full 0.924 vs
  trainable 0.142, norm inflation 6.0. ResNet-18 probe: L=20, 11,173,962 trainable, buffer share
  99.9%, counter 68.5% of ||d_i||^2 and 85.7% of ||d_i-d_j||^2 (=500 = 20*(16-11)^2 exactly), cos
  full 0.993 vs trainable 0.0007, Prop. 1 error 3.4e-15, inert under default momentum.
- **Build/check:** latexmk rc 0, 16 pp; check_manuscript: all PASS except the gate (397 = 390 pf
  macro refs + 7 literal \PENDING, all P1 or the donor screen).
- **Running jobs left for the next agent:** P1 untouched, launcher PID **448486**, log
  `results/postfix_p1/campaign.log`, 70/960 cells at 06:55 (started ~03:43). ETA ~48 h total.
  Harvest: `python3 paper/analyse_postfix.py && python3 paper/make_fig_p1.py && cd paper && make`.
- **Score after: 4/10, REJECT** (one coherent paper now; analytic core extended with a
  mechanism corollary that the data confirm exactly; still no complete outcome evidence and a
  possibly null attack).
- **Top 3 priorities for the next iteration:**
  1. **Resolve the attack-strength question** as soon as P1's FedAvg cells land
     (`grep fedavg results/postfix_p1/campaign.log`). If FedAvg BSR ~ clean floor: design a
     CPU-sized P2 with an attack that implants under FedAvg (raise p to 0.3-0.5 and/or m to 0.3,
     or more rounds; calibrate on FedAvg alone with 1-2 seeds first), queue it to start when P1
     frees lanes, and cut BSR claims from P1. Do not exceed ~12 cores.
  2. **Harvest P1** and re-check every `% RE-CHECK` sentence (Sec. 4 statistics, Sec. 6.2
     results, Sec. 6.3 FoolsGold/FLTrust, conclusion); retire the \PENDING for Krum/Bulyan/RFA
     (Corollary 2 test: IID dist share should collapse) and negative controls; then the abstract.
  3. Cheap analytic/offline work while P1 runs: verify the FLAME ordering hypothesis offline
     (replay HDBSCAN on synthetic or saved updates under the affine map of Eq. 2, CPU seconds);
     survey artefact with repo URLs + commit hashes + file:line in the replication package;
     a small federated ResNet/CNN-with-BN outcome run only once cores free up.

## Iteration 4 - 2026-10-21 - Attack calibration: P1's backdoor does not implant; P1 stopped, replaced by P1-clean + P2 (calibrated attack)

- **Reviewer score before: 4/10, REJECT.** Top blocker (iteration 3's #1): P1's attacked BSR
  equalled the clean floor for every finished rule, so P1 could not support any backdoor claim.
- **Blockers found (ranked):**
  1. **Confirmed: the P1 attack does not implant under plain FedAvg** (pilot below). Every P1
     BSR column was uninformative by construction. Fixed in design this iteration (P2).
  2. All outcome evidence still pending (P1 clean arms 45/480 cells, P2 attacked 0/480).
  3. **New code defect found (not fixed, deliberately):** `FederatedEngine.__init__` stores
     `self.global_weights = tu.get_weights(self.model)`, and `get_weights` returns
     `.numpy()` views that alias the model's parameter memory. In ROUND 1 ONLY, local
     training mutates `global_weights` in place, so round-1 clients train sequentially (each
     starts from the previous client's weights) and round-1 defense deltas / logged
     geometry use the last client's weights as "global". From round 2 on, global_weights
     come from `parameters_to_ndarrays` (fresh arrays) and the bug is gone. Verified with a
     2-line test (aliased after in-place update: True). It affects both arms and every
     campaign identically (P1, P2, pilot), metrics are last-5-round means, so it is not a
     confound of the A/B, but it is a correctness bug a reviewer of the code would flag.
     NOT fixed now so that P1-clean, P2 and the pilot share one code path; fix
     (`[w.copy() for w in ...]`) only together with a re-run plan, or document it in the
     replication notes.
  4. The calibrated attack is norm-visible (malicious/honest trainable norm ~2x), calibrated
     on one seed; one architecture for outcomes; survey artefact still missing.
- **What I changed:**
  - `experiments/attack_pilot/pilot.py` (new): FedAvg-only pilot at the exact P1 scale
    (configs/p1_trainable.yaml, 40k/10k rows, 10 clients, 15 rounds, seed 42), with boost and
    malicious-local-epochs knobs (subclass; no change to the running code path at the time).
    Results: `results/pilot_attack_iter4/pilot_fedavg_{dirichlet,iid}_<cell>_s42.json`, lane
    logs `results/pilot_attack_iter4/lane{A..F}.log`. Scratch check that a poisoned client
    learns the backdoor locally (BSR 0.92 after 1 epoch from a pretrained model) but
    parameter interpolation at its FedAvg weight (0.26) leaves BSR 0.085: the backdoor is
    averaged away, not unlearnable.
  - `src/fl/engine.py`: default-off `attack.mal_local_epochs` (malicious clients train this
    many local epochs) and `attack.boost` (`_boost_malicious`, scales the trainable part of
    malicious deltas). Defaults reproduce the old behaviour exactly.
  - `experiments/run_sweep.py`: `--mal-local-epochs`, `--boost`, `--skip-clean`,
    `--skip-attacked`; filename suffixes `_me<k>` / `_b<x>` only when non-default (verified:
    P1 cell names unchanged, so resume works).
  - **P1 stopped** (process group 448486, SIGTERM; 3 lanes had been SIGSTOPped ~1 h for the
    pilot), 89 completed cells kept in `results/postfix_p1/` (45 clean, 44 attacked-1-epoch;
    the latter are kept but no longer used by the paper). Note appended to its campaign.log.
  - `experiments/postfix/run_p2.sh` + `configs/p2_{full,trainable}.yaml` (= p1 configs except
    out_dir): ONE resumable 6x2-thread queue that (a) finishes P1's CLEAN cells into
    results/postfix_p1/ with the unchanged P1 command + `--skip-attacked` (completed cells are
    skipped by filename), and (b) runs all ATTACKED cells with `--mal-local-epochs 5` into
    results/postfix_p2/. FedAvg first (calibration across seeds), seeds 42-46 Dirichlet, then
    IID, then seeds 47-51.
  - `paper/analyse_postfix.py`: `--atk-res DIR` takes attacked cells from DIR, clean from
    --res. Makefile `numbers` now runs `analyse_postfix.py --atk-res results/postfix_p2` and
    the new `paper/make_numbers_pilot.py` -> `paper/numbers_pilot.tex` (\ap... macros).
  - `paper/main.tex` (backup `paper/main.tex.pre-iter4.bak`): Adversary paragraph now
    states E_m=5 local epochs for malicious clients; new "Attack calibration" paragraph and
    Table `tab:calib` (14 pilot rows, all macros); Reductions paragraph, Sec. 6.2 design
    sentence and "What the BSR columns can and cannot say" rewritten (floor + FedAvg ceiling
    logic; the 1-epoch attacked cells are declared withdrawn); Limitations "Scale and attack
    strength" rewritten. check_manuscript reads numbers_pilot.tex.
- **Evidence (generated, `paper/numbers_pilot.tex`; CA/BSR = last-5-round means, seed 42):**
  Dirichlet FedAvg: clean BSR 0.052 (CA 0.724); P1 attack (m0.2 p0.1, 1 epoch) 0.045;
  p0.3 / p0.5 (4,842 poisoned rows) / m0.3p0.3 / trigger x2: all 0.04-0.05; boost x5:
  BSR oscillates (round max 0.99, last-5 mean low) and CA drops to ~0.6; E_m=2: 0.046;
  **E_m=3: 0.785, implants at round 10; E_m=5: 0.907, implants at round 5, CA 0.731**,
  norm ratio 2.02 (vs 1.31 for 1 epoch). IID: clean 0.012, P1 attack 0.038, E_m=3 0.744
  (round 11), **E_m=5 0.942 (round 5), CA 0.738**, norm ratio 2.19. Clean-model BSR is the
  same with the trigger at x1 and x2 (0.052): the clean model does not read the trigger as
  benign, i.e. no free OOD artefact; the realizability audit (joint Mahalanobis ~29-30,
  100th pctile vs benign) is unchanged since the trigger is P1's. Side finding: P1 Krum
  defect arm s42 reached BSR 0.70 with the 1-epoch attack where FedAvg cannot (Krum under
  the defect selected a poisoned update in late rounds) -- watch for this in P2 Krum.
- **Build/check:** latexmk rc 0, 17 pp; check_manuscript: only the gate fails (441 = 434 pf
  macro refs + 7 literal), all P1-clean / P2 pending as expected.
- **Running jobs left for the next agent:** **P1c+P2 queue**, launcher bash PID **497076**
  (process group 497076; `MAL_EPOCHS=5 nohup setsid bash experiments/postfix/run_p2.sh`),
  log `results/postfix_p2/campaign.log`, per-job logs `results/postfix_p2/log_p2*` and
  `results/postfix_p1/log_p1*`. Started 08:30. ~435 clean + 480 attacked cells left; at
  ~15-20 min/cell/lane, 6 lanes: ETA ~45 h (seeds 42-46 ~22 h). Resume: rerun the same
  command. Count: `ls results/postfix_p1/*atk0*.json | wc -l` (target 480) and
  `ls results/postfix_p2/*.json | wc -l` (target 480). Harvest:
  `cd paper && make numbers`. No other jobs of this chain are running (pilot finished).
- **P2 sanity check (08:52):** first P2 cell `results/postfix_p2/p2full_dirichlet_ciciot2023_fedavg_atk1_m0.2_p0.1_fixed_me5_s42.json` gives CA 0.730 / final-round BSR 0.934, identical to the pilot's E_m=5 cell, so the run_sweep path and the pilot subclass agree. 1260 s/cell/lane for attacked cells.
- **Score after: 4/10, REJECT** (the fatal design flaw is fixed and documented with a
  generated calibration table, but no outcome is measured yet under the working attack).
- **Top 3 priorities for the next iteration:**
  1. **Verify P2's FedAvg cells** as soon as they land (first jobs in the queue; ~30-40 min
     after 08:30): attacked BSR must be >> clean floor in both arms for seeds 42-46. If any
     seed fails to implant, report it; if most fail, raise MAL_EPOCHS and relaunch P2 only
     (clean P1 arm is unaffected). Then harvest P1-clean (FoolsGold/FLTrust/FLAME done) and
     fill Sec. 6.2/6.3 with the new attacked numbers; retire RE-CHECK comments.
  2. Decide on the round-1 aliasing bug (blocker 3): at least document it in the replication
     notes / threats to validity with its exact scope; optionally a 2-seed FedAvg+FoolsGold
     check with the copy fix to show it does not move last-5-round metrics.
  3. Cheap offline work while the queue runs: FLAME ordering hypothesis replay; survey
     artefact (repo, commit, file:line); multi-seed calibration robustness can be read from
     P2 FedAvg rather than re-run.

## Iteration 5 - 2026-10-21 - Round-1 aliasing defect measured: it decides FoolsGold's outcomes; P3 prepared; AlignIns (CVPR 2025) implemented; survey +1 exposed repo

- **Reviewer score before: 4/10, REJECT.** Blockers carried: no complete outcome evidence;
  round-1 aliasing defect (iteration 4, blocker 3) unquantified; newest rule from 2022 (B2).
- **Blockers found (ranked):**
  1. **The round-1 aliasing defect changes FoolsGold's outcomes, so it is not a nuisance.**
     Campaign-scale replay with the copy ON (Dirichlet s42, `configs/_r1fix_*.yaml`,
     `results/round1_alias/campaign_replay.json`, generated `\raRep...` macros):
     FedAvg clean CA 0.724->0.723, BSR 0.052->0.051 (no effect). FoolsGold clean CA
     0.608->0.288 (defect arm) and 0.709->0.332 (fixed arm); FPR 0.86->0.90 and 0.40->0.70.
     FoolsGold attacked (E_m=5): CA 0.660->0.278 / 0.735->0.620, BSR 0.017->0.021 /
     0.962->0.999. Mechanism: with the copy, round-1 updates all start from the same init,
     FoolsGold excludes most clients from round 1 (CA 0.10 after round 1) and never recovers;
     the defect's sequential round 1 had handed it a model trained by all 10 clients (round-1
     CA 0.71). **The P1 FoolsGold A/B headline (CA 0.584 vs 0.712) is a property of the
     defective engine.** Withdrawn in the paper (Sec. 4 "Round-one aliasing", Sec. 6.2, 6.3,
     conclusion). FLTrust's Corollary-3 result (DR=FPR=0 under the defect) is analytic and
     should survive, but must be re-measured.
  2. **E_m=5 is not a working attack on every seed.** P2 FedAvg Dirichlet s43: BSR 0.007
     (s42: 0.934). Cause (computed from the partition, `assign_malicious` + `partition_data`):
     malicious data share under example-weighted FedAvg is 26.1% at s42, 10.6% s43, 11.0% s44,
     23.5% s45, 9.7% s46. Prediction: s44 and s46 fail too, s45 implants. IID shares are
     20% on every seed. Iteration 4 calibrated on the most favourable seed.
  3. Campaign still running on the defective engine (see "Running jobs").
  4. B2 (recency): now partially addressed (below); no 2023-25 rule measured yet.
- **What I changed:**
  - `src/fl/engine.py`: default-OFF fix `federated.copy_initial_global` (copies the initial
    global weights) with a comment. Default path byte-identical, so the running queue is
    unaffected. Mechanism trace `experiments/round1_alias/check_alias.py trace` ->
    `results/round1_alias/trace.json`: under the defect the 10th round-1 client starts at
    trainable distance 4.26 from the round's init with counter 31; the defense's reference
    = last client's model (distance 0). With the copy: 0, 0, reference 0.997 from the last client.
    Tiny-config outcome runs (`outcome_clean_trainable.json`, 4 rows) were stopped as
    uninformative (CA ~0.35 at 8k rows) in favour of the campaign-scale replay
    (`results/round1_alias/run_replay.sh`, `collect_replay.py`).
  - Diagnostics now exclude round 1 (`paper/analyse_postfix.py` DIAG_FIRST_ROUND=2,
    `make_fig_p1.py` FIRST=2). Campaign round-1 full-vector cosine 0.382 vs 0.955 over rounds
    2-15 (`\raPone...`); tiny trace with the copy: round-1 cosine 0.95 (= normal). The paper's
    old sentence blaming round 1 on running statistics was wrong and is removed.
  - `paper/make_numbers_alias.py` -> `paper/numbers_alias.tex` (\ra macros); wired into the
    Makefile, main.tex, check_manuscript.
  - **P3 prepared, NOT launched:** `configs/p3_{full,trainable}.yaml` (= p1 + copy ON,
    out_dir results/postfix_p3), `experiments/postfix/run_p3.sh` (= run_p2.sh job list,
    clean + attacked into postfix_p3, needs MAL_EPOCHS).
  - **B2:** web-verified Multi-Metrics (Huang et al., ICCV 2023, doi
    10.1109/ICCV51070.2023.00429), FreqFed (Fereidooni et al., NDSS 2024, doi
    10.14722/ndss.2024.23620), AlignIns (Xu, Zhang, Hu, CVPR 2025, arXiv 2503.07978) -> refs.bib,
    related work. **AlignIns implemented** (`src/defenses/alignins.py`, registered as
    `alignins`; ported from JiiahaoXU/AlignIns@49b7d32 `agg_alignins`), synthetic self-test
    `python3 -m experiments.alignins.selftest` (mask removes buffers exactly; MPSA moves <= 1/k;
    under `full` TDA residue correlates 1.0 with b_i/||d_i||, kept set chosen by batch count),
    4-round engine smoke test OK. Prediction paragraph in Sec. 5 ("A 2025 rule, implemented
    but not yet run"): TDA exposed via shard size, MPSA not, clip exposed. New limitation
    "Recency of the rules".
  - **Survey:** AlignIns' official code flattens `state_dict()` for both the update and the
    global model used by TDA; CIFAR-10 ResNet-9 has `track_running_stats=False` (safe), but
    CIFAR-100 VGG-9 (`src/vgg.py:41`) and Tiny-ImageNet torchvision ResNet-18 carry
    `num_batches_tracked` -> exposed in 2 of 3 benchmarks. SURVEY.md row with file:line;
    Table tab:survey row; counts now "four of ten" (abstract, contributions, Sec. 3.3, limits).
- **Build/check:** latexmk rc 0, 18 pp; check_manuscript: all PASS except the gate
  (443 = 434 pf macro refs + 9 literal \PENDING). Abstract exactly 250 words.
- **Running jobs left:** the **P1c+P2 queue, PID 497076, is still running on the defective
  engine** (log results/postfix_p2/campaign.log). I tried to stop it (process-group SIGTERM)
  and the auto-mode permission classifier denied it. **Recommendation: stop it**
  (`kill -TERM -497076`). Its numbers for FoolsGold (and possibly FLDetector, the other
  stateful rule) are numbers of the defective engine. The cells it finishes for stateless
  rules are probably fine (FedAvg replay: no change), but this has not been shown rule by
  rule, so P3 should re-run everything on one code path. Restart cost now is small (~2 h of P2
  progress + P1's ~90 clean cells). My replay jobs have all finished; nothing else of mine
  is running.
- **Score after: 4/10, REJECT.** This iteration made the paper more honest, not more
  accepted. A headline result is withdrawn. Counting the defect arm, two of three
  "mechanism" findings (FoolsGold, and FLTrust pending re-measure) need P3.
- **Top 3 priorities for the next iteration:**
  1. **Stop P2 (if still running) and settle the attack before launching P3.** Calibrate on
     FedAvg with the copy ON (configs/p3_full.yaml), Dirichlet seeds 43/44/46 (the low-share
     seeds) at E_m in {5, 8, 10}, 1-2 seeds each, 6 lanes. Alternatives if E_m alone fails: fix
     the malicious data share, or move the attack claims to IID. Then
     `MAL_EPOCHS=<k> nohup setsid bash experiments/postfix/run_p3.sh > results/postfix_p3/campaign.log 2>&1 &`
     and add `alignins` to its DEFENSES list (cheap, implemented). Point the Makefile `numbers`
     target at postfix_p3.
  2. Re-derive the FoolsGold story from P3. Under the copy, both arms collapse at s42 (FedAvg-
     style FoolsGold excludes ~70-90% of honest non-IID clients). That collapse may itself be
     the result: FoolsGold is unusable on heterogeneous honest clients, counter or not.
  3. Harvest P3 FedAvg first (implant check on all seeds). Then FLTrust: does Corollary 3's
     "excludes no one" hold under the copy?

## Iteration 6 - 2026-10-21 - Seed-robust adversary (share-matched attackers) calibrated; FoolsGold collapse diagnosed; P3 auto-launcher armed

(Resumed: the first iteration-6 agent was killed by a laptop suspend ~14:2x before
recording. Its uncommitted work was reviewed, kept where sound, fixed where not, and
finished here.)

- **Reviewer score before: 4/10, REJECT.** Blockers: no outcome measured under a working
  attack on every seed; P1/P2 run on the round-1-defective engine; FoolsGold collapse under
  the copy unexplained.
- **Blockers found (ranked):**
  1. **The attack does not implant on every seed, even with the attacker data share fixed.**
     Share-matched attackers (combined share 19.1-21.0% on all 10 Dirichlet seeds, vs
     9.6-47.7% random), FedAvg, copy ON, P3 scale, last-5 BSR: E_m=5: s42 0.859, s43 0.535,
     s44 0.011, s46 0.010. E_m=10: 0.928 / 0.956 / 0.663 / 0.269. E_m=15: s44 0.872,
     **s46 0.164** (single rounds >0.5 undone next round). Clean floor 0.003-0.052.
     Implantability depends on the partition beyond share (s46 attackers [0,4] hold 46 of
     1295 benign rows; not yet explained). p=0.3 at E_m=5 does nothing on s44/s46.
  2. P3 not launched (no GPU: zombie CUDA "unknown error" at 14:27 and still at 14:50; CPU is
     at the 12-core budget with calibration).
  3. All \pf A/B macros still PENDING (434 refs): P1-clean was never finished and is on the
     defective engine anyway.
  4. One-architecture outcomes, norm-visible attack (malicious/honest full-vector norm ratio
     is large at E_m=15), CPU-scale reductions.
- **What I changed / kept:**
  - Kept from the dead agent (reviewed): `src/fl/build.py::assign_malicious_share_matched`
    (`attack.mal_selection: share_matched`, `share_tol` 0.01; random draw kept when it
    qualifies, so IID cells, where the share is exactly 20%, keep their attackers);
    `attack.mal_local_steps` (engine + `torch_utils.local_train(steps=)`, default off, unused);
    run_sweep `--mal-selection`, `--mal-local-steps`, suffixes `_sm`/`_ms<k>`, and
    `malicious_cids`/`malicious_data_share` in every result JSON; `configs/p3_*.yaml` now
    share-matched; `configs/calib6_full.yaml`; `experiments/calib_iter6/{run_calib.sh,shares.py}`;
    `experiments/foolsgold_diag/diag.py`; AlignIns added to P3 and analyse_postfix.
  - **Fixed:** `paper/make_numbers_calib6.py` let the p=0.3 side cells overwrite the p=0.1
    E_m=5 cells (same `_me5_sm` suffix; s44 printed 0.086 instead of 0.011) -> glob restricted
    to p0.1; E_m=15 stem added; table stems always defined. The dead agent had pointed the
    Makefile's \pf macros at the empty postfix_p3 and the paper's P1/P2 numbers at a new
    \pa file that main.tex never uses -> reverted (\pf stays P1/P2 until P3 lands; comment in
    Makefile; `analyse_postfix.py --target` keeps \pfCellsTarget=960 for P1, 1040 for P3).
    `run_p3.sh`: `DEVICE` env (cuda/cpu), `MAL_EPOCHS` now required (was a `__CALIB__`
    placeholder that would have crashed every attacked cell).
  - **Paper (backup main.tex.pre-iter6.bak):** new paragraph "A seed-robust adversary" +
    Table `tab:seedcal` (per seed: clean floor, random share + P2 E_m=5 BSR, matched share +
    E_m=5/10/15 BSR and implant round; all \cs macros), stating that P2's non-IID attacked
    BSR is uninformative on 3 of 5 seeds and that no E_m tried implants on every seed; the
    re-run reads attacked BSR only on seeds where FedAvg implants (pre-registered, PENDING).
    New FoolsGold diagnostic paragraph in Sec. Mechanisms: with the copy, 7/10 clients are
    DDoS-majority, median max history cosine 0.821, FoolsGold keeps median 3 clients (27.0% of
    rows, 1 of 7 DDoS-majority), CA 0.332; authors' weighted-SUM aggregation (verified in
    DistributedML/FoolsGold model_aggregator.py: `np.dot(delta.T, wv)`) gives 0.490; no
    history gives 0.671. So the collapse is FoolsGold's honest-dissimilarity assumption failing
    on label skew, not the port and not the counter.
- **Build/check:** latexmk OK, 19 pp; check_manuscript all PASS except the gate
  (454 = 444 macro refs {pf 434, cs 10} + 10 literal PENDING).
- **Running jobs (all CPU, 1 thread each, 12 lanes total):**
  - `run_calib.sh` drivers: E_m=15 s45,47-51 (6 lanes, log `results/calib_iter6/campaign_e.log`),
    E_m=15 s42,43 (`campaign_g.log`), E_m=5 then 10 at s45 (`campaign_f.log`). ETA ~17:30
    (E_m=15 cells take ~2.1 h at 1 thread). Per-cell logs `results/calib_iter6/log_*`.
  - **P3 auto-launcher** (`experiments/calib_iter6/launch_p3_when_calibrated.sh`, log
    `results/calib_iter6/launcher.log`): waits for all calib6 processes, then applies the rule
    fixed before seeing the results: >= 8/10 seeds with E_m=15 FedAvg BSR > 0.5 -> launches
    `MAL_EPOCHS=15 run_p3.sh` (cuda LANES=4 if a test allocation works, else cpu LANES=5) into
    `results/postfix_p3/campaign.log`; otherwise does nothing. CPU P3 at E_m=15 is many days;
    if the GPU comes back, kill the CPU P3 process group and relaunch with DEVICE=cuda
    (resumable by filename).
  - GPU: zombie ("CUDA unknown error") at 14:27 and 14:50; needs the user's sudo reload.
- **Score after: 4/10, REJECT.** The threat model is now sound and documented, and a
  FoolsGold result became a defensible finding, but no rule outcome exists yet under it.
- **Top 3 priorities for the next iteration:**
  1. Read `results/calib_iter6/launcher.log`. If P3 launched, verify the first FedAvg cells
     (both arms) implant; regenerate `paper/numbers_calib6.tex` and fill Table tab:seedcal
     (s45 E_m=5/10, s42/43 E_m=15). If the rule failed, redesign (e.g. pick attackers whose
     data also covers benign/attack classes, or report IID as the attacked setting).
  2. Explain s46 (attackers hold ~no genuine benign rows; check per-class BSR and which honest
     clients undo it). A mechanism here is a reviewer-proof calibration story.
  3. If the GPU is back, move P3 to CUDA; then harvest P3 FedAvg/FLTrust (Corollary 3 under
     the copy) and point `make numbers` at postfix_p3 (`--target 1040`).

## Iteration 7 - 2026-10-21 - Seed 46 explained as a late, unstable onset (censored at E_m=15), not resistance; composition ruled out; horizon probe armed

- **Reviewer score before: 4/10, REJECT.** Blockers unchanged from iteration 6: no rule
  outcome under a working attack; the calibration rule (>= 8/10 seeds implant) rests on an
  unexplained seed-46 failure; P3 not launched; all \pf A/B macros PENDING.
- **Environment:** GPU still zombie at 14:52 (nvidia-smi "Unknown Error", torch "CUDA unknown
  error"). CPU load ~12 from iteration 6's calibration; I added no training load while it runs.
- **Blockers found (ranked):** (1) as before, no outcome evidence; (2) "seed 46 resists" was
  an unexplained claim the whole calibration rule depends on; (3) the 15-round CPU horizon and
  the last-5-round criterion interact: a jump at round >= 14 cannot register as an implant.
- **What I did:**
  - `experiments/calib_iter6/s46_probe.py` -> `results/calib_iter6/s46_probe.json` (data
    only, no training): recomputes exactly what the share-matched attackers poison on seeds
    42-51. Poisoned rows 705-812 on every seed; poisoned source classes cover >= 96.8% of the
    BSR test set; DDoS is the majority poisoned class everywhere (s46 61.7%, implanting seeds
    >= 67.9%). **Composition does not single s46 out.** Trigger facts: 0 training rows within
    L_inf 0.5 sigma of the trigger; 3 of 5 stamped values lie outside the column's training range
    (Header_Length -1.5 < min -1.37; syn 2.0 > max 1.80; ack -1.0 < min -0.32), so honest
    clients never train against the trigger and the backdoor is an extrapolation. Only outlier:
    s46 attackers hold 46 genuine benign rows vs 260-501 on s42-44. **Pre-registered test:**
    s49 (81) and s51 (1) attackers are also benign-poor; if benign scarcity is causal, their
    E_m=15 cells (running) fail. If they implant, the explanation is refuted.
  - **Onset dynamics** (from existing calibration histories): implants are abrupt (floor ->
    >0.5 in one round), onset round 8-12 in the 6 implanting cells. s46: onset round 12
    (E_m=10, falls back to 0.0 next round, final round 0.504) and 14 (E_m=15, final 0.115).
    E_m=15 at s46 is right-censored by the 15-round horizon; E_m=10 is a genuine instability.
    More E_m does not bring the s46 onset forward -> near-threshold, noise-decided.
  - Paper (backup `paper/main.tex.pre-iter7.bak`): seed-46 paragraph in Sec. setup ("A
    seed-robust adversary") rewritten with all of the above as \cs macros (new block in
    `paper/make_numbers_calib6.py`: \csOnset*, \csSix*, \csTrig*, \csPois*, \csMalBenign*);
    two literal \PENDING for the s49/s51 test and the horizon probe.
  - **Horizon probe armed** (`experiments/calib_iter7/run_horizon.sh`,
    `configs/calib7_horizon.yaml` = calib6_full with out_dir results/calib_iter7, separate
    file name so the P3 launcher's `pgrep calib6_full.yaml` is not blocked). Waits for the
    calib6 processes to exit, then runs s46 E_m=15 and s44 E_m=5 for 40 rounds (2 lanes, 1
    thread; CUDA if available). **Pre-registered:** censoring holds for a cell if mean BSR over
    rounds 36-40 > 0.5. Sanity check on harvest: rounds 1-15 should reproduce the 15-round cells.
- **Build/check:** latexmk rc 0, 19 pp; check_manuscript all PASS except the gate
  (456 = 444 macro refs {pf 434, cs 10} + 12 literal PENDING; +2 literal from this iteration).
- **Running jobs:**
  - Iteration 6 calibration (unchanged, ~10 lanes, ETA ~17:30) and its P3 auto-launcher
    (`results/calib_iter6/launcher.log`).
  - **Horizon probe waiter PID 571764** (log `results/calib_iter7/horizon.log`, per-cell logs
    `results/calib_iter7/log_h_*`). Starts after the calibration; ETA ~5.5 h after start on CPU
    (s46 E_m=15 x 40 rounds), so ~23:00. Outputs
    `results/calib_iter7/calib7h_dirichlet_ciciot2023_fedavg_atk1_m0.2_p0.1_fixed_me{15,5}_sm_s{46,44}.json`.
    If P3 launches on CPU (5 lanes) the total is 7 lanes, within budget.
- **Score after: 4/10, REJECT.** The calibration story is now mechanistic and falsifiable
  instead of "s46 is unexplained", but no defended outcome exists yet.
- **Top 3 priorities for the next iteration:**
  1. Harvest calibration (launcher.log; regenerate numbers_calib6.tex). Check the s49/s51
     test above and replace its \PENDING with the verdict (add macros for s47-51 to the
     generator; SEEDS currently stops at 46). If < 8/10 implant and the failures are late
     onsets, the fix is more rounds (GPU) rather than more E_m: say so and redesign the rule
     (e.g. implant = BSR > 0.5 over the last 5 of R rounds with R chosen from the horizon probe).
  2. Harvest the horizon probe (~23:00) and settle the censoring \PENDING; wire its two cells
     into make_numbers_calib6.py.
  3. If the GPU is back: P3 on CUDA, ideally at more rounds if the horizon probe says onset is
     late; then FedAvg/FLTrust (Corollary 3 under the copy).

## Iteration 8 - 2026-10-21 - Hostile full read; story made coherent after the withdrawals; FLTrust corollary restated exactly in shares; history lemma; threat model; BN related work

- **Environment:** GPU still zombie (torch "CUDA unknown error" at 15:05). CPU at budget with
  iteration 6's calibration (9 run_sweep lanes) + iteration 7's horizon waiter; I launched no
  training. One few-second, 1-thread probe re-run (below).
- **Reviewer score before: 4/10, REJECT** (hostile top-venue read of the whole main.tex).
- **Blockers found (ranked):**
  1. No rule outcome under a working attack (unchanged; blocked on calibration/P3).
  2. **The story contradicted itself after iterations 5-7.** Discussion said the counter makes
     FoolsGold "exclude most of the cohort" (iteration 6 showed that is FoolsGold's own
     assumption failing, in both arms); the retro list kept "FoolsGold bimodality ... fixed-arm
     spread is a fraction" (withdrawn P1 data); FLTrust/FLAME interim cells were presented as
     settled although they ran on the round-1-defective engine; the FoolsGold mechanism
     paragraph called withdrawn numbers "consistent with this reading"; Setup/Limitations/
     calibration caption still called E_m=5 "the campaign's attack, calibrated on one seed".
  3. **Corollary 3 (FLTrust) was imprecise:** its hypothesis cos(b_i,b_0) >= kappa was never
     connected to anything measurable, and "threshold just over one half, far below the shares we
     measure" compared against the *clients'* shares although the server's root update has only
     B_0=2 batches. Contribution bullet misquoted Corollary 1 ("twice the trainable share").
     FoolsGold history bound was loose and unproved inline.
  4. Threat model scattered across a paragraph that mixed P1/P2 and the re-run; no mention that
     the counter is a value every (malicious) client sets for itself.
  5. Related work missed the BatchNorm-in-FL line (Hsieh 2020, FBN 2024, Hybrid BN ICML 2025)
     and the heterogeneity-robustness line (bucketing, ICLR 2022).
  6. Page count 19 -> 21 now (JISA has no hard cap; trimming is a later job once results land).
- **What I changed (backup `paper/main.tex.pre-iter8.bak`):**
  - **Corollary 3 rewritten:** with q = counter share of the squared norm (client q_i, server
    q_0), cos(d_i,g_0) >= sqrt(q_i q_0) - sqrt((1-q_i)(1-q_0)), positive **iff q_i+q_0 > 1**;
    exact rescaling identity ||g_0||/||d_i|| = (B_0/B_i) sqrt(q_i/q_0). Proof via the two-block
    split (counter vs rest). No data/partition/running-stat assumption.
  - `experiments/counter_defect/probe_defect.py` now also measures a B_0=2 server update
    (computed after the existing clients, so all earlier \df numbers are byte-identical):
    q_0 = 63.7%, q_i = 86.5%, bound 0.521, measured full cosine 0.947 vs trainable 0.127
    (`results/defect_probe.json` "fltrust"; macros \dfFlt*). Synthetic inputs, stated.
  - New Eq. (bufcos): buffer cosine >= sqrt(g_i g_j) - sqrt((1-g_i)(1-g_j)) with g = counter share
    of buffers; paragraph after Corollary 1 on when compression changes a decision (thresholds,
    varying shares) and when it need not (ordering preserved).
  - **Lemma 1 (Histories stay compressed):** 1 - s_i(t) <= eta^2/(eta^2 + L B_min^2) for all t,
    with proof (tighter than the old (eta+rho)^2 form, no running-stat assumption).
  - Coherence: Discussion, retro list (FoolsGold item replaced by an honest "two defects and one
    violated assumption" entry; FLTrust/FLAME items marked interim), "Results so far" provenance
    note, Conclusion, contributions bullets 3-4, Limitations (scale/attack), calibration caption
    and E_m=5 wording, FoolsGold mechanism paragraph now cites only the copy-ON replay
    (\raRep... FPR 0.900 defect vs 0.700 fixed) and defers to the diagnostic.
  - **Threat model** paragraph (goal / capabilities / knowledge / budget) + "The counter is
    attacker-controlled" (analytic consequences for Krum and FLTrust, explicitly not measured);
    limitation extended.
  - Related work: +4 refs, all web-verified today (hsieh2020quagmire PMLR 119; guerraoui2024fbn
    arXiv:2405.14670; chen2025hybridbn PMLR 267 pp. 9500-9515; karimireddy2022bucketing ICLR).
  - **Harvest prep:** `paper/make_numbers_calib6.py` now covers seeds 42-51; Table tab:seedcal has
    rows 47-51 (E_m=15 PENDING; columns never planned print "n/r", caption says why).
  - **New result picked up from a finished cell:** share-matched s45 at E_m=5 does NOT implant
    (BSR 0.012; random attackers with 23.5% share had 0.861). Text now says E_m=5 fails on
    44, 45 and 46.
- **Build/check:** latexmk rc 0, 21 pp; check_manuscript all PASS except the gate
  (465 = 452 macro refs {pf 434, cs 18} + 13 literal; +1 literal = FLTrust re-run test; cs rose
  because the table now shows the s45/s47-51 cells that are still running).
- **Running jobs (not mine, untouched):** iteration 6 calibration (9 lanes, ETA ~17:30) + P3
  auto-launcher (`results/calib_iter6/launcher.log`, still waiting at 15:07); iteration 7
  horizon waiter (`results/calib_iter7/horizon.log`, ETA ~23:00).
- **Score after: 4/10, REJECT.** The manuscript is now internally consistent, its analytic core
  (Prop. 1, Cor. 1-3, Lemma 1) is exact and stated in measurable quantities, and the threat model
  is explicit; but acceptance still hinges on outcome evidence that does not exist yet.
- **Top 3 priorities for the next iteration:**
  1. Harvest the calibration (~17:30): `python3 paper/make_numbers_calib6.py` fills tab:seedcal
     directly; settle the s49/s51 benign-scarcity test and the "reads attacked BSR only on implanting
     seeds" PENDING; check launcher.log for the >=8/10 rule outcome.
  2. If P3 launches, verify its first FedAvg/FLTrust cells (Corollary 3 again: DR=FPR=0 in the
     defect arm; also log the server's q_0 on real data — add it to fltrust.py's metrics, cheap).
  3. Harvest the horizon probe (~23:00); then, once results land, trim to ~18 pp (candidates:
     merge tab:calib into an appendix, shorten Sec. 4 "Round-one aliasing").

## Iteration 9 - 2026-10-21 - Calibration harvested (benign-scarcity explanation refuted); P3 rescued from silent CUDA OOM; FLTrust counter shares now logged on real data

- **State on arrival (coordinator, 18:05):** machine rebooted 17:45 and killed every job.
  The calibration had finished before that: launcher.log 15:51 "E_m=15 seeds implanting: 9 of
  10" -> P3 launched (CPU, 5 lanes), then relaunched after the reboot on CUDA, 4 lanes, under
  systemd-inhibit (PID 5899/5901, log results/postfix_p3/campaign.log). Horizon probe
  relaunched on CPU (PIDs 6099-6109, results/calib_iter7/horizon.log, ETA ~23:30-midnight).
- **Reviewer score before: 4/10, REJECT** (unchanged blockers: no rule outcome under a
  working attack; all \pf A/B macros PENDING).
- **Blockers found (ranked):**
  1. **P3 was failing silently.** 4 CUDA lanes do not fit: every attacked cell's BSR eval
     ran a 4096-row chunk through the LSTM (1.66 GiB cuDNN allocation) and OOMed. run_sweep
     isolates cell errors, so the driver logged "done(rc=0)" for jobs whose cells all failed
     (attacked FedAvg full s43-46, FoolsGold both arms, FLAME full: 20 ERROR lines by 18:05).
     Without a fix P3 would have "completed" with most attacked cells missing.
  2. **The reboot left two 0-byte result files** (p3full fedavg attacked s42, p3trainable fedavg
     clean s44: atomic rename without fsync), which the resume logic treated as done forever.
  3. Calibration not harvested; s49/s51 pre-registered test unsettled; seedcal table PENDING.
  4. Corollary 3 still had no real-data measurement of the server share q_0.
- **What I changed:**
  - `src/attacks/__init__.py`: BSR eval chunk 4096 -> 1024 (eval mode, predictions per sample
    do not depend on chunk; same chunk as torch_utils.evaluate). `experiments/run_sweep.py`:
    `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` by default; result JSON fsynced before
    the atomic rename; a 0-byte JSON no longer counts as done. Live from 18:02: P3 jobs started
    after that (e.g. PID 7306, 436-636 MiB) use the new code; the three jobs started earlier
    (5921, 6606, 6648, ~2.1-2.6 GiB each) still run the old code and may lose more cells.
  - The two 0-byte files moved to `results/postfix_p3/_zero_byte_after_reboot/`.
  - **Gap-filler** `experiments/postfix/fill_p3_gaps.sh` (PID 7091 under systemd-inhibit, log
    results/postfix_p3/gapfill.log + campaign.log): waits for run_p3.sh to exit, then re-runs the
    resumable driver (MAL_EPOCHS=15, cuda, 4 lanes) up to 3 passes until no new cells appear.
  - **FLTrust logs Corollary 3's quantities** (`src/defenses/fltrust.py` `_counter_diag`,
    `src/fl/engine.py` History.fltrust_counter): per round q_0 (server counter share), min q_i,
    min q_i+q_0, min bound sqrt(q_i q_0)-sqrt((1-q_i)(1-q_0)), min measured full-vector cosine.
    Pure logging. CPU smoke (2 rounds, E_m=1, scratchpad only, NOT a result): q_0 0.65-0.67,
    q_i >= 0.71, bound 0.36-0.39 <= measured cosine 0.73-0.79, DR=FPR=0 - consistent with the
    corollary. P3's FLTrust jobs start after the fix, so they carry it.
  - **Harvest** (`paper/make_numbers_calib6.py` regenerated): E_m=15 implants on 9/10 seeds
    (new macros \csSmEfifteenNimpl, \csSmEfifteenBSRMinImpl); s45 only just (0.519, onset round 13);
    s46 fails (0.164). **Benign-scarcity explanation REFUTED:** s49 (81 benign rows) BSR 0.929,
    s51 (1 benign row) BSR 0.953; paper says so and drops it. Clean column for seeds 47-51 now
    reads P3's clean FedAvg cells (PENDING until they run; caption says so).
  - **P3 reproduces the calibration** on the one finished matched pair: s43 trainable FedAvg
    attacked, CUDA, same attackers [3,8]: last-5 BSR 0.955, onset round 10 vs calibration 0.964,
    round 8 (\csRep*). The P3 FedAvg clean cells agree across arms exactly (FedAvg reads no
    decision statistic): s42 CA 0.726/BSR 0.043 in both.
  - Paper (backup `paper/main.tex.pre-iter9.bak`): s49/s51 verdict; the pre-fixed >=8/10 rule
    and its outcome (seed 46 excluded, seed 45 marginal); CPU-vs-GPU reproduction stated;
    AlignIns is in the re-run (1,040 cells), no longer "not part of the campaign"; FLTrust
    paragraph wired to \csFlt* macros (PENDING until P3 FLTrust cells exist).
  - AGENT_BRIEF.md: corrected the "4 lanes fit" note.
- **Build/check:** latexmk rc 0, 21 pp; check_manuscript all PASS except the gate
  (457 = 446 macro refs {pf 434, cs 12} + 11 literal; was 465).
- **Running jobs (none killed):** P3 driver PID 5901 (CUDA 4 lanes, ETA ~15-20 h, more with
  failed cells refilled); gap-filler PID 7091 (after P3); horizon probe PIDs 6099-6109 (CPU,
  ETA ~23:30-00:00, outputs results/calib_iter7/calib7h_*).
- **Score after: 4/10, REJECT.** Infrastructure saved and calibration closed honestly, but
  the outcome evidence still does not exist.
- **Top 3 priorities for the next iteration:**
  1. `grep -c ERROR results/postfix_p3/log_*` — confirm cells started after 18:02 no longer OOM.
     If they still do, the gap-filler's LANES should drop to 3 (edit fill_p3_gaps.sh before it
     starts). Then harvest FLTrust cells: rerun make_numbers_calib6.py (fills \csFlt*), check
     DR=FPR=0 in the full arm and bound <= cosine every round.
  2. Harvest the horizon probe (~midnight); settle the censoring PENDING.
  3. Once P3 FedAvg attacked cells exist for all seeds (gap-fill), define the implant set
     from P3's own FedAvg and point analyse_postfix/make numbers at postfix_p3.

## Iteration 10 - 2026-10-21 - P3 made the campaign of record in the paper (implant rule coded, AlignIns rows); Corollary 4: a falsified counter buys FLTrust admission; Corollary 3 checked on real data (sufficient, not necessary)

- **Coordinator notes recorded.** (18:08) The coordinator killed P3 PIDs 6606 and 6648
  (FoolsGold attacked, started before iteration 9's 18:02 OOM fix, so every seed failed).
  Every P3 process now running started after the fix, except 5921 (FedAvg trainable
  attacked, had no OOM; it has since finished). The gap-filler will rerun the failed cells.
  (later) **Venue changed to IEEE TIFS** (zero cost: final main text <= 10 IEEEtran pages incl.
  references, supplement <= 6 pp; see AGENT_BRIEF). I did no JISA formatting and cut nothing.
- **OOM check (done):** every ERROR line in results/postfix_p3/log_* names the pre-fix
  processes (5919/5920/6606/6648); jobs started after 18:02 have ERR=0, including attacked cells
  (FLAME trainable s42/s43, FLTrust full s42, FedAvg trainable s45/s46). GPU at ~2.5-4 GB of 8
  with 4 lanes. No load reduction needed. 34 of 1,040 cells present at 18:32.
- **Reviewer score before: 4/10, REJECT** (hostile TIFS read). Blockers, ranked:
  1. No rule outcome under a working attack yet (P3 needs ~20 h more).
  2. The results section still read the *first* campaign (defective round-one engine) through
     the \pf macros, the tables were labelled P1, AlignIns was missing from them, and the
     pre-registered implant rule ("attacked BSR only on seeds where FedAvg implants") was
     stated in the paper but **not implemented** in analyse_postfix.py.
  3. "The counter is attacker-controlled" was qualitative; for a security venue, an exact
     statement of what a falsified counter buys is the natural security result.
  4. Corollary 3 had no real-data check; once FLTrust cells landed, the real data showed its
     condition q_i+q_0>1 FAILS in some rounds (text said "predicts no exclusion" unconditionally).
  5. Length: 22 pp elsarticle; TIFS needs <= 10 IEEEtran pp (not touched: wait for P3).
- **What I changed (backup paper/main.tex.pre-iter10.bak):**
  - `paper/analyse_postfix.py`: pre-registered implant rule `--implant-bsr 0.5` (attacked BSR
    averaged over seeds where every FedAvg attacked cell has last-5 BSR > 0.5; CA/DR/FPR over all
    paired seeds); macros \pfImplantN/Decided/Excl{Dir,Iid}, \pfBSRFedavgAllSeeds{Dir,Iid}.
    `paper/Makefile`: \pf now from results/postfix_p3 (target 1040); the first campaign is
    regenerated as \pa (numbers_postfix_p1.tex, now \input; values byte-identical to before).
    `make_fig_p1.py --res` (figure now from P3). check_manuscript lane renamed to P3.
  - Paper: Sec. 6.2 rewritten (design of record = re-run; "Results so far" from P3 cells: FedAvg
    negative control identical across arms over 4 seeds; FoolsGold clean CA 0.408 defect vs 0.571
    fixed, CI [-0.286, 0.611], n=3, FPR 0.667 vs 0.567 - both arms exclude most honest clients;
    first-campaign FLTrust/FLAME quoted as \pa and labelled; implant-set paragraph). AlignIns rows
    in both A/B tables and in tab:rules; "twelve" -> "thirteen"; stale "CPU", "P1", "interim",
    "newest rules are from 2022" fixed.
  - **Corollary 4 (new, exact):** under the defect FLTrust gives client j a non-counter step
    M_j/||g0|| = rho_j(1-q_j)sqrt(1-q0) + sqrt(q0 q_j(1-q_j)); a client choosing its counter
    achieves M*/||g0|| = (rho sqrt(1-q0) + sqrt(rho^2(1-q0)+q0))/2 > 0 for every direction
    (admitted even at rho=-1), independent of its norm, optimum q=1/2 at rho=0. Proof in text.
    Verified on the implementation (`experiments/counter_defect/fltrust_falsify.py` ->
    results/fltrust_falsify.json, paper/numbers_falsify.tex \ff*): rel. error 2.1e-8, grid of 99
    shares never exceeds the closed form, rho=-1 attacker excluded with its true counter (signed
    step -0.139) but admitted when falsified (0.199 ||g0||); fixed arm excludes all rho<=0.
    **Honest caveat in text:** on the probe's synthetic updates honest rho_j = 0.91-0.92, so the
    falsifier gets only 0.5x (rho=-1) / 1.1x (rho=0) the median honest step; real-data ratio not
    measured (P3 logs q, not rho); no training with a falsifying attacker.
  - **Corollary 3 on real data** (make_numbers_calib6.py, new macros \csFltNroundsQsumLeOne,
    \csFltNroundsCosNonpos, \csFltNdefectRuns, \csFltDefectMaxExcl): over 60 logged rounds of 4
    defect-arm FLTrust runs, q0 ranges 5.8-91.4%; the condition fails in 7 rounds (bound down to
    -0.267), yet the measured cosine is never <= 0 (min 0.015) and no client is ever excluded.
    Text now says the condition is sufficient, not necessary.
- **Build/check:** latexmk rc 0, 22 pp (elsarticle; IEEEtran not yet converted, so no IEEEtran
  page count / supplement 0). check_manuscript all PASS except the gate (521 = 510 macro refs
  {pf 505, cs 5} + 11 literal; pf rose because AlignIns rows and P3 FLTrust/FLAME cells are
  pending, cs fell from 12 to 5).
- **Running jobs (none started by me remain):** P3 driver PID 5901 (CUDA, 4 lanes; ETA roughly
  20 h, i.e. ~Oct 22 afternoon/evening, plus gap-fill); gap-filler PID 7091; horizon probe PIDs
  6099-6109 (CPU, ETA ~midnight).
- **Score after: 4/10, REJECT** (TIFS). The paper now updates itself from P3 and has a genuine
  security result (Corollary 4), but outcomes are still missing and the length is ~2x the cap.
- **Top 3 priorities for the next iteration:**
  1. Convert to `\documentclass[journal]{IEEEtran}` (keep .bak, macros, IEEE citation style) to get
     a real page count; do not cut yet.
  2. Run `make numbers` (or the two analyse_postfix lines + make_numbers_calib6.py) as P3 lands;
     re-check every RE-CHECK comment (FedAvg identical arms, FoolsGold paragraph, FLTrust counts).
  3. Consider a small end-to-end test of Corollary 4 (FLTrust defect arm, attacker sets counter to
     q=1/2, CPU or after P3) and log rho_j in fltrust.py so the real-data ratio can be computed.

## Iteration 11 - 2026-10-21 - Converted to IEEEtran (real page count: 16 pp incl. references); P3 harvest (FLAME clean cells n=5; FLTrust Corollary 3 counts on 8 runs)

- **State at start (18:43):** P3 41/1,040 result files (driver PID 5901, 4 CUDA lanes, ERR-free
  since the 18:02 fix); gap-filler PID 7091 waiting; horizon probe (PIDs 6108/6109, CPU, s44 E_m=5
  and s46 E_m=15, 40 rounds) still running, no output yet -> not harvested.
- **Reviewer score before: 4/10, REJECT** (hostile TIFS). Blockers, ranked:
  1. No rule outcome under a working attack (P3 needs ~20 h).
  2. Length unknown in the venue's format (elsarticle 22 pp); every planning decision about cuts
     needed a real IEEEtran count.
  3. Two-column layout problems would surface only after conversion (wide tables, a 7.2-in figure).
- **What I changed (backup paper/main.tex.pre-iter11-ieeetran.bak = the elsarticle source):**
  - `\documentclass[journal]{IEEEtran}`, `cite` package, IEEEtran.bst, IEEE title/author block
    (affiliation, e-mails and funding statement in \thanks), IEEEkeywords. lmodern dropped (Times).
    Every \input{numbers*} unchanged; build and all generators work as before.
  - Back matter: `paper/declarations_ieee.tex` (Data Availability only; CRediT/competing-interest
    text kept in declarations.tex for the record, funding moved to the title footnote).
  - Two-column fixes: Tables survey, calib (attack calibration), seedcal, rules, p1, p1flag -> table*;
    probe table at column width with a wrapping first column; Eqs. (cos) and (bufcos) split over two
    lines; a long \texttt path -> \path. Overfull boxes 17 -> 2 (both < 1 pt).
  - `paper/make_fig_p1.py`: figure resized for one column (3.5 x 2.3 in, 6-7 pt fonts, short legend
    labels, right legend moved off the curves).
  - `paper/analyse_postfix.py`: a difference that rounds to zero prints "0.000" (was "-0.000" /
    "+0.000"). Only sign-of-zero strings changed in numbers_postfix*.tex; no value changed.
  - **Harvest (P3):** FLAME clean non-IID cells now n=5: FPR 0.384 in both arms (diff 0.000,
    CI [-0.050, 0.050]); CA 0.712 vs 0.705, diff -0.006, CI [-0.033, 0.020]. Added as the third
    "Results so far" item and in the FLAME mechanism paragraph ("so far in the re-run too; attacked
    cells pending"), with a RE-CHECK at n=10. FLTrust Corollary 3 counts regenerated: 8 defect-arm
    runs, 165 logged rounds, q_0 5.1-91.4%, condition q_i+q_0>1 fails in 21 rounds (bound down to
    -0.427), measured cosine never <= 0 (min 0.015), no client ever excluded: the "sufficient, not
    necessary" text still holds unchanged. Implant set so far: Dirichlet in {43,44,45}, out {46}.
- **Build/check:** latexmk rc 0. **IEEEtran page count: 16 pp total (main text ends on p.15,
  references p.15-16, about 15.6 pages used) / supplement 0 pp.** The cap is 10 incl. references
  (aim 9.5): about 6 pages (~40%) must move to a supplement (<= 6 pp) or be cut, and the final P3
  tables will fill PENDING cells (slightly longer, not shorter). check_manuscript: all PASS except
  the gate (512 = 501 macro refs {pf 496, cs 5} + 11 literal; was 521). Abstract is exactly 250
  words (TIFS limit 250).
- **Running jobs (none started by me):** P3 driver PID 5901 (CUDA 4 lanes, ETA ~Oct 22 afternoon/
  evening) + gap-filler PID 7091; horizon probe PIDs 6108/6109 (CPU; started 17:52, 40 rounds,
  outputs results/calib_iter7/calib7h_*; slower than the earlier "midnight" ETA guess is possible).
- **Score after: 4/10, REJECT.** Venue format now real; science unchanged until P3 lands.
- **Top 3 priorities for the next iteration:**
  1. Harvest: `python3 paper/analyse_postfix.py --res results/postfix_p3 --atk-res results/postfix_p3
     --target 1040` + `make_numbers_calib6.py`; re-check every RE-CHECK comment (FedAvg identical,
     FoolsGold, FLAME n=10, FLTrust counts). Harvest the horizon probe when calib7h_* JSONs appear.
  2. Plan the cut without executing it yet: write a section-by-section page budget (target 9.5 pp)
     and a supplement.tex skeleton (round-one aliasing, calibration/seedcal tables, trigger
     realizability, withdrawal history, per-defense extras); the six table* floats are the cheapest
     first moves.
  3. Corollary 4 end-to-end test (FLTrust defect arm, counter-falsifying attacker) on CPU or after P3;
     log rho_j in fltrust.py.

## Iteration 12 - 2026-10-21 - Page budget measured block by block (15.8 -> 9.5 pp plan); supplement skeleton with two-way cross-references; P3 harvest (FLTrust re-run: fixing the counter turns on exclusion of honest clients)

- **Coordinator note recorded.** At 18:51 the coordinator added `experiments/postfix/run_p3_reverse.sh`
  (PID 15185 under systemd-inhibit 15184): 2 extra CUDA lanes walking results/postfix_p3/jobs.txt in
  reverse (log results/postfix_p3/campaign_reverse.log), so P3 runs 6 lanes at ~0.65 GB each (GPU 3.8 GB
  used at 18:54). Committed with this iteration. I added no GPU job.
- **State at start (18:54):** P3 50/1,040 JSONs (59 at 19:06). The only ERROR lines in P3 logs are the
  three known pre-fix OOMs (foolsgold full/trainable s46, flame full s46, all before 18:20, written by
  pre-fix processes; the gap-filler reruns them). Horizon probe (PIDs 6108/6109, CPU, 40 rounds)
  still running, no calib7h JSON yet: not harvested.
- **Reviewer score before: 4/10, REJECT** (hostile TIFS). Blockers, ranked:
  1. No rule outcome under a working attack for most rules (P3 ~6% done).
  2. 15.8 IEEEtran pages against a hard 10 (aim 9.5); no plan for what goes where, no supplement.
  3. (new, found this iteration) The paired t-intervals on bounded rates leave [0,1]: FLTrust
     FPR CI [0.383, 1.049], DR CI [-0.047, 1.097] at n=4-5. A TIFS statistician will flag it.
- **What I changed:**
  - **Harvest (P3, 59 cells).** New: FLTrust non-IID clean n=5, attacked n=4. Defect arm excludes no one
    (FPR 0.000 clean and attacked, DR 0.000); fixed arm excludes honest clients at FPR 0.716 (clean,
    CI [0.383, 1.049]) and 0.631 (attacked), malicious at DR 0.525; clean CA 0.643 vs 0.573 (diff -0.070,
    CI [-0.275, 0.135]; the fixed arm's s45 collapses to CA 0.298 with FPR 0.96). This is Corollary 3's
    prediction (the counter makes FLTrust admit everyone) now on the corrected engine. Added as the
    fourth "Results so far" item (macros only, RE-CHECK at n=10) and replaced the conditional "If that
    holds in the re-run" in the FLTrust mechanism paragraph by "The re-run's clean cells so far agree".
    Corollary 3 real-data counts regenerated: 10 defect-arm runs, 285 rounds, q_0 up to 94.0%,
    condition fails in 24 rounds, measured cosine never <= 0, max exclusion 0.000: text unchanged, holds.
    Implant set unchanged (Dirichlet in {43,44,45}, out {46}).
  - **Supplement skeleton.** `paper/preamble.tex` (new): the shared preamble (packages, theorems,
    macros, every \input{numbers*}), plus `xr-hyper`. `paper/main.tex` now `\input{preamble}` and
    `\externaldocument{supplement}`; `paper/supplement.tex` (new, IEEEtran journal, S-numbered sections/
    tables/figures/equations) does `\externaldocument{main}`. No prefixes, so a label keeps working in
    both files after its text moves (labels must stay unique across the two). Seven sections, each a
    `\TOMOVE{...}` placeholder naming the main-text block that will move into it; **nothing was moved
    or deleted**. One sentence added to the intro roadmap pointing at Sec. S-I (both directions of
    cross-reference verified in the PDFs: main shows "Sec. S-I", supplement shows "Sec. III", "Table V").
  - `paper/Makefile`: `make` builds main -> supplement -> main again (xr needs both .aux files);
    `make numbers` does the same. `paper/tools/make_package.sh`: copies preamble, supplement, all
    numbers*.tex and declarations_ieee.tex (it still copied the Elsevier set).
  - `paper/tools/check_manuscript.py`: new checks main.pdf <= 10 pp, supplement.pdf <= 6 pp, no
    \TOMOVE left in the supplement, no undefined refs/cites in supplement.log.
  - **`paper/tools/page_budget.py` (new):** measures the IEEEtran page use of every section, bold
    paragraph head, theorem block and float by inserting \pdfsavepos whatsits (zero layout effect;
    the script verifies pdftotext output equals an unmarked build: "identical: yes"). ~45 s. Rerun it
    after every cut. Accidentally ran a `cat >> /dev/null` that hung on stdin; I killed it with
    `pkill -f -u ubuntu 'cat$'` (my own process; noting it because the pattern was broad).
- **Page budget (measured 19:05 on the 59-cell build; pages incl. floats; target 9.5 incl. refs).**

  | block (current) | now | target main | goes to supplement |
  |---|---|---|---|
  | Title, abstract, keywords | 0.34 | 0.32 | abstract to ~220 words |
  | I Introduction (0.56) + contributions list (0.67) | 1.23 | 0.85 | - (trim list to 4 short items) |
  | II Related work (5 paragraphs) | 0.77 | 0.60 | - (fold Federated IDS into one sentence) |
  | III Defect: setting, Prop. 1, Cor. 1, Cor. 2, norm/coord, inertness | 1.13 | 0.95 | - |
  | III verification on real updates + second architecture + Table I | 0.41 | 0.06 | S-II (0.38) |
  | III-A Which pipelines are exposed + Table II + the fix | 0.50 | 0.42 | - (Table II stays: survey is a contribution) |
  | IV Setup: task, model, federation, threat model, counter attacker-set | 0.64 | 0.55 | - |
  | IV Attack calibration + Table III, seed-robust adversary + Table IV, reductions | 1.61 | 0.12 | S-IV (1.50) |
  | IV Server, metrics, statistics | 0.31 | 0.28 | - |
  | IV Round-one aliasing | 0.43 | 0.06 | S-V (0.37) |
  | V Rules: Table V + per-family descriptions + 2025 rule + hyperparameters | 1.11 | 0.50 | S-VI (0.55) |
  | VI-A Transmitted geometry + Fig. 1 | 0.42 | 0.42 | - |
  | VI-B Design, results so far, BSR rule + Tables VI, VII | 1.20 | 1.40 | - (+0.2 reserved: final P3 text) |
  | VI-B first campaign, for reference | 0.11 | 0 | S-VII |
  | VI-C Cor. 3 + proof + real-data check | 0.67 | 0.30 | S-III (0.40) |
  | VI-C Cor. 4 + proof + probe | 0.59 | 0.25 | S-III (0.35) |
  | VI-C FoolsGold + Lemma 1 + proof | 0.53 | 0.20 | S-III (0.33) |
  | VI-C FLAME, distance, controls | 0.28 | 0.25 | - |
  | VI-D What the counter did to an earlier version | 0.38 | 0.06 | S-VII (0.32) |
  | VII Trigger design and realizability + Tables VIII, IX | 0.99 | 0.10 | S-VIII (0.90), main keeps one paragraph in VIII |
  | VIII Discussion (why it survives review, recommendations, limitations) | 0.71 | 0.55 | - |
  | IX Conclusion | 0.44 | 0.20 | - |
  | Data availability + references (37) | 0.92 | 0.92 | - |
  | **Total** | **15.80** | **~9.50** | **~5.1 + overview/refs ~0.5 = ~5.6 of 6** |

  Arithmetic: moving blocks saves ~5.3 pp (15.8 -> ~10.5); prose trimming of intro/related/
  setup/discussion/conclusion/abstract saves ~1.2 pp; +0.2 is reserved for the final P3 results text.
  **Both budgets are tight** (main ~9.5, supplement ~5.6/6). Fallbacks, in order: merge Tables VI and
  VII (A/B outcomes + flags) into one table* (~0.15), move Fig. 1 to the supplement (0.18, but the
  supplement is near its cap), cut the realizability audit to a separate paper instead of the
  supplement (frees 0.9 of supplement; it is independent of the counter story).
- **Build/check:** latexmk rc 0 for both. **IEEEtran pages: main 16 (ends at 15.80) / supplement 1
  (skeleton).** check_manuscript: FAIL main > 10 pp (expected), FAIL 7 \TOMOVE placeholders (expected),
  FAIL gate 481 (= 470 macro refs {pf 465, cs 5} + 11 literal; was 512); everything else PASS.
- **Running jobs (none started by me):** P3 driver PID 5901 (4 lanes) + coordinator reverse runner PID
  15185 (2 lanes), CUDA; at ~59 cells/75 min of 6-lane operation the ETA is still ~Oct 22 evening; gap-filler
  PID 7091 waits. Horizon probe PIDs 6108/6109 (CPU, since 17:52), outputs results/calib_iter7/calib7h_*.
- **Score after: 4/10, REJECT.** FLTrust's re-run result now supports Corollary 3 on the corrected engine
  (n=5), and the cut is planned and measurable, but outcomes for most rules are missing and the paper is
  still 16 pp.
- **Top 3 priorities for the next iteration:**
  1. Fix the interval method for bounded rates (FPR/DR/BSR CIs leave [0,1]): use a paired bootstrap or
     clip-and-say in analyse_postfix.py, regenerate, and state the method in Sec. IV "Statistics".
  2. Harvest P3 (`make numbers` or the analyse_postfix + make_numbers_calib6 lines) and the horizon probe
     when calib7h_* lands; re-check every RE-CHECK comment (FLTrust fourth item, FLAME, FoolsGold, FedAvg).
  3. Start executing the budget with blocks whose content is final and independent of P3 (allowed once
     P3 lands per the brief; if the coordinator agrees earlier, the safest first moves are S-V round-one
     aliasing, S-VIII realizability, S-II probe details): move text unchanged, replace with the kept
     summary sentences, rerun `python3 paper/tools/page_budget.py`, record the new page counts.

## Iteration 13 - 2026-10-21 - Statistics rebuilt for bounded rates at small n: exact paired sign-flip test, interval by test inversion, Holm (family + global), sign counts; the t-based "significance" of the first campaign does not survive

- **State at start (19:08):** P3 61/1,040 JSONs (6 lanes: PIDs 5901 + 15185, gap-filler 7091). Horizon probe
  (PIDs 6108/6109, CPU) still running, no calib7h JSON: not harvested. I started no job.
- **Reviewer score before: 4/10, REJECT** (hostile TIFS). Blockers, ranked: (1) no rule outcome under a working
  attack for most rules (P3 ~6%); (2) 16 pp against a hard 10; (3) statistics: t-intervals on bounded rates left
  [0,1] (FLTrust FPR [0.383, 1.049]), and, found this iteration, the t-test also *overstated evidence*: the first
  campaign's FLTrust FPR difference printed p_H = 0.001 at n = 5, which no distribution-free paired test can give.
- **What I changed:**
  - `paper/analyse_postfix.py`: primary test is now the **exact two-sided paired sign-flip permutation test** of
    the mean difference (all 2^n sign vectors; verified equal to `scipy.stats.permutation_test` at n = 4, 5, 6, 8,
    10). The **95% interval inverts the same test** over shifts in [-1, 1] on a 0.001 grid, so it never leaves the
    feasible range and excludes 0 iff p <= 0.05 (consistent by construction; percentile bootstrap was rejected
    because at n = 5 it would exclude 0 while p = 0.0625). Holm across the 13 rules within (partition, attack,
    metric) now on the exact p; new **global Holm** over all reported-metric tests; new macros per cell `Pos`/`Neg`
    (sign consistency, the effect-consistency measure) and `Pmin` (= 2^(1-n_nonzero), the test's floor); global
    `\pfTestsRun`, `\pfSigFamily`, `\pfSigGlobal`, `\pfSigRaw`, `\pfTestableTen` (0.0020). CSV keeps p_t, p_w,
    d_z for reference only. Regenerated numbers_postfix.tex (P3) and numbers_postfix_p1.tex (first campaign).
  - `paper/main.tex` (backup main.tex.pre-iter13.bak): Sec. IV "Statistics" rewritten (method, assumption =
    symmetry of per-seed differences under no effect, inverted interval, Holm family + global counts, the 2^(1-n)
    floor and "read for significance only at n >= 6"); "Results so far" now says up front that n <= 5 cannot reach
    p < 0.05 and reports direction + sign counts + exact p instead of CIs (FLTrust FPR: fixed > defect on 5/5 seeds,
    p = 0.062 = the floor); first-campaign paragraph no longer prints p_H = 0.001 (now: 5/5 seeds, exact p at the
    floor); Table VI caption and intro sentence name the test. refs.bib: holm1979, ernst2004permutation (both
    verified by web search: Scand. J. Stat. 6(2):65-70; Stat. Sci. 19(4):676-685, doi 10.1214/088342304000000396).
- **Evidence (generated):** 23 tests run on P3 so far; 0 survive Holm (family or global), 0 even raw p <= 0.05,
  as they must at n <= 5. First campaign: 41 tests, 0 survive (was: FLTrust FPR p_H 0.001, CA p_H 0.235 under t).
  At n = 10 the floor is 0.0020 < 0.05/13 = 0.0038, so a perfectly consistent 10/10 effect survives Holm; a 9/1
  split generally will not. This is the honest power of a 10-seed design and should be stated in the limitations
  when P3 lands (or the next agent can argue for 12+ seeds on the cells that matter, e.g. FLTrust/FLAME/FoolsGold).
- **Build/check:** latexmk rc 0; **IEEEtran pages: main 16 (ends at 15.99, was 15.80: +0.19 from the statistics
  paragraph and 2 refs) / supplement 1 (skeleton)**. check_manuscript: same 3 expected FAILs (pages, 7 \TOMOVE,
  gate 481); everything else PASS (abstract 250 words).
- **Running jobs (none started by me):** P3 driver PID 5901 + reverse runner PID 15185 (CUDA, 6 lanes), gap-filler
  PID 7091; horizon probe PIDs 6108/6109 (CPU), outputs results/calib_iter7/calib7h_*.
- **Score after: 4/10, REJECT.** The statistics are now defensible to a TIFS statistician and no longer overstate
  n = 5 evidence, but outcomes are still missing and the paper is 16 pp.
- **Top 3 priorities for the next iteration:**
  1. Harvest P3 (`cd paper && make numbers`) and the horizon probe when calib7h_* lands; at n >= 6 per cell, put
     the inverted CIs back into "Results so far" (macros `...Lo/Hi` exist) and check every RE-CHECK comment.
  2. Power/design note for TIFS: with 10 seeds only 10/10-consistent effects survive Holm over 13 rules; decide
     (pre-register in the ledger before looking) whether the primary hypotheses are restricted to the rules with a
     predicted exposure (Table V: FLTrust, FLAME, FoolsGold, Krum/Bulyan/RFA...), which shrinks the Holm family
     legitimately, and say so in Sec. IV; the "arms identical" rules are then negative controls, not tests.
  3. Start the cut (budget in iteration 12): the Statistics paragraph itself grew to ~0.45 pp; compress it to the
     method sentence + floor sentence when the cut starts, moving the t-interval remark to the supplement.

## Iteration 14 - 2026-10-21 - Confirmatory hypotheses pre-registered (iterations/PREREG_P3.md) and wired into the analysis; correction: attacked IID runs are NOT the distance rules' null (E_m=15 attackers carry a 15x counter)

- **State at start (19:15):** P3 65/1,040 JSONs (6 CUDA lanes: PIDs 5901 + 15185, gap-filler 7091). The
  only ERROR lines are the three known pre-fix OOM logs (18:05-18:19). Horizon probe PIDs 6108/6109 (CPU)
  still running, no calib7h JSON: not harvested. I started no job.
- **Reviewer score before: 4/10, REJECT.** Blockers: (1) outcomes missing for most rules (P3 ~7%); (2) 16 pp vs
  hard 10; (3) new, found this iteration: with 13-rule Holm families at n=10 nearly nothing can survive and
  nothing was registered in advance, so any positive finding would read as a forking-paths result; (4) new:
  a theory error. Sec. V and VI-C said Krum/Bulyan/RFA are untouched by the counter in IID runs because batch
  counts are equal. In attacked runs they are not: malicious clients train E_m=15 epochs, the engine counts
  every forward pass (src/fl/engine.py::_client_fit), so their counter is ~15x an honest client's in every
  partition (Cor. 2 applies).
- **What I changed:**
  - `iterations/PREREG_P3.md` (new): dated pre-registration. Primary family (Cor. 3): FLTrust FPR clean and DR
    attacked, Dirichlet and IID, fixed > defect. Secondary family (Eq. norm: NormClip/FLAME noise sigma = lambda*S
    with S the full-vector norm in the defect arm, ~8x inflated): NormClip and FLAME clean CA, both partitions,
    fixed > defect; registered as weaker (defect arm also clips less; FLAME Dir clean already looked null).
    One-sided exact sign-flip in the registered direction, Holm within family over the REGISTERED size (untested
    hypothesis enters at p=1), blind-only Holm as sensitivity, final only at n=10, no re-runs to rescue.
    Explicitly exploratory and why: Krum/Bulyan/RFA (both arms see the attackers as outliers: their trainable
    norm is 16-50x honest in calibration), FLAME clustering, FoolsGold, GradCos, AlignIns, FLDetector, every BSR;
    negative controls are descriptive. Non-blind disclosure: P1, P3 (FLTrust Dir s42-46) and S3 (FLAME Dir clean
    s42-46) were partly read; P2, P4, S1, S2, S4 blind (no such cell on disk). `iterations/PREREG_P3_manifest.txt`:
    sha256 of the 70 P3 JSONs on disk at registration (all treated as seen).
  - `paper/analyse_postfix.py`: `--prereg` parses the ```prereg block, `signflip_p_one` (verified equal to
    scipy permutation_test alternative='greater' at n=4,6,10), macros \pfPre<Id><N|Pos|Neg|Diff|P|Ph|Verdict>,
    family counts (Total/Tested/Supported/Blind*), \pfPreFinal (interim/final), \pfPrePartialN, \pfPreBlindN,
    \pfPreManifestN; writes results/postfix_p3/prereg_results.md. Makefile passes `--prereg`.
  - `paper/make_numbers_calib6.py`: \csMalNormRatioMin/Max/N (attackers' trainable norm over honest, E_m=15 calib).
  - `paper/main.tex` (backup main.tex.pre-iter14.bak): Statistics paragraph rewritten (confirmatory vs exploratory,
    t-interval aside removed); Sec. V distance rules and VI-C "Distance rules" corrected (clean IID is the null;
    attacked runs expose the counter in both partitions; no sign predicted).
- **Evidence (generated, INTERIM):** P1 FLTrust Dir clean FPR +0.716, 5/0, one-sided p 0.031, Holm 0.125; P3 FLTrust
  Dir attacked DR +0.580, 5/0, p 0.031, Holm 0.125; S3 FLAME Dir clean CA -0.006, 3/2, p 0.69. 0/4 primary, 0/4
  secondary supported so far (cannot be otherwise at n=5 with family size 4).
- **Note:** `make numbers` fails at make_figs.py (results/summary.csv missing; legacy, pre-existing); I ran the P3
  lines (analyse_postfix, make_numbers_calib6, fltrust_falsify, make_fig_p1) directly and reverted the
  legacy numbers.tex side effect.
- **Build/check:** latexmk rc 0. **IEEEtran pages: main 17 (ends at 16.15, was 15.99) / supplement 1.** check:
  same 3 expected FAILs (pages, 7 \TOMOVE, gate 465); rest PASS.
- **Running jobs (none mine):** P3 PIDs 5901, 15185, gap-filler 7091 (83/1,040 at 19:37); horizon PIDs 6108/6109.
- **Score after: 4/10, REJECT** (outcomes and length unchanged; inference plan now defensible and a wrong
  null claim removed).
- **Top 3 priorities:**
  1. Harvest P3 + horizon; do NOT edit PREREG_P3.md except dated amendments. When P2/P4/S1/S2/S4 cells land,
     report them through the \pfPre macros (add one sentence/row in Sec. VI-B; consider a 8-row confirmatory
     table in place of prose).
  2. Fix `make numbers` (make_figs.py needs results/summary.csv) or drop legacy steps from the target.
  3. Start the page cut with P3-independent blocks (S-V aliasing, S-VIII realizability, S-II probe), per the
     iteration-12 budget; main is now 16.15 pp.

## Iteration 15 - 2026-10-21 - `make numbers` fixed (legacy steps split off); first cut: five P3-independent blocks moved to the supplement (main 16.15 -> 12.75 pp); horizon probe s44 harvested

- **State at start (~19:40):** P3 85/1,040 JSONs (6 CUDA lanes: PIDs 5901 + 15185, gap-filler 7091);
  95 at the end. Horizon probe (PIDs 6108/6109, CPU): s44 E_m=5 done, s46 E_m=15 still running. I started no job.
- **Reviewer score before: 4/10, REJECT.** Blockers: (1) outcomes missing for most rules (P3 ~8%); (2) 17 pp
  (16.15) vs hard 10; (3) `make numbers` broken, so the paper had no one-command rebuild.
- **What I changed:**
  - **`make numbers` (paper/Makefile).** Cause: make_figs.py needs results/summary.csv, which
    `experiments.make_tables` can no longer write because the pre-fix JSONs were archived to
    results/_pre_counterfix in iteration 1. None of the legacy outputs is used: the only figure in the paper
    is fig_p1_geometry.pdf, and the only numbers.tex macros used are the 42 `\rz*` realizability ones, which
    make_numbers.py reads from results/realizability_ciciot2023.json. Worse, aggregate_multiseed.py would pool
    the calibration campaigns (calib_iter*) into summary_multiseed.csv as if they were a headline campaign
    (it set \numSeeds=10, \numCellsMulti=4; unused, but wrong). The `numbers` target now runs make_numbers.py
    without those steps (numbers.tex is byte-identical to the committed one); the three legacy steps live in a
    separate `make legacy` target with a comment saying why. **`make numbers` now runs end to end, rc 0,
    5 min 22 s** (fltrust_falsify.py is most of it). It rewrites results/fltrust_falsify.json with
    last-digit float noise (1e-15); numbers_falsify.tex unchanged; I reverted the JSON.
  - **Cut (backups main.tex.pre-iter15.bak, supplement.tex.pre-iter15.bak).** Moved unchanged, labels and all,
    into paper/supplement.tex: S-II probe paragraphs + Table probe; S-IV "Attack calibration", "A seed-robust
    adversary" (+ Tables calib, seedcal) and "Reductions, stated"; S-V "Round-one aliasing"; S-VII "The first
    campaign, for reference" + the subsection "What the counter did to an earlier version" (label sec:retro
    now in S-VII); S-VIII the whole realizability section (Tables trig, realize). Main keeps: a 6-line
    "Verification" summary; a new 17-line "Attack calibration" paragraph (E_m threshold, share-matched budget,
    the pre-registered E_m=15 rule, 9/10 implant, seed 46, BSR read on implanting seeds only, attackers'
    norm 16-50x honest); a 9-line aliasing summary; one sentence on the first campaign; a short paragraph
    naming the four withdrawn findings; a new "Feature-space trigger" limitation with the d_M numbers.
    "Reductions" is covered by the existing "Scale and attack strength" limitation. Intro roadmap and two
    section-range references fixed. The supplement has no bibliography of its own: \cite resolves through
    xr-hyper to the paper's reference numbers (a second bibliography redefined bagdasaryan2020/pierazzi2020
    labels; now 0 multiply-defined).
  - **Horizon probe (partial harvest).** make_numbers_calib6.py: `\csHz{BSR,Implant,Rounds,LastLow}` for
    the two 40-round cells. s44 at E_m=5 (never implants in 15 rounds): implants at round 22 of 40, last
    round with BSR <= 0.5 is 27, last-five BSR 0.919. Sentence added in S-IV ("on that one cell the 15-round
    failure was a matter of time"); s46 E_m=15 still \PENDING. n=1, stated as such.
  - **P3 harvest** (`make numbers`): 86 runs at analysis time. New: Krum Dirichlet clean n=5, attacked n=3;
    DR 1.000 in both arms, CA diff +0.018 clean (3/2), no sign either way, consistent with iteration 14's
    "both arms see the attackers as outliers" (exploratory). PREREG: no new confirmatory cell (P1, P3 n=5;
    S3 n=5; P2/P4/S1/S2/S4 still 0); no amendment needed.
- **Build/check:** latexmk rc 0, 0 undefined refs/cites, 0 "??" in either PDF. **IEEEtran pages: main 13
  (ends at 12.75, was 16.15) / supplement 5 (about 4.7 incl. two placeholders).** check_manuscript: FAIL
  main > 10 pp, FAIL 2 \TOMOVE (S-III proofs, S-VI rule details), FAIL gate 445; rest PASS.
- **Page arithmetic for the next agent (page_budget.py, this build):** still 3.25 pp to cut for 9.5. Left in
  the budget: proofs of Cor. 3/4 + Lemma 1 (1.64 pp now; plan keeps ~0.75 -> -0.9), rule descriptions
  (0.87 -> ~0.4, -0.45), Limitations 0.51 and Conclusion 0.44 (-0.4), intro/contributions (-0.4), Statistics
  0.30 (-0.1), merge Tables VI/VII (-0.15). That reaches ~10.0, not 9.5, so further prose trimming is needed.
  **Supplement is the binding constraint:** 4.7 pp now + proofs (~0.9) + rules (~0.45) = ~6.05 > 6. Options:
  compress Table seedcal (10 rows x 8 cols, ~0.35 pp) or drop the realizability audit to a separate paper
  (frees ~0.9 pp of supplement; independent of the counter story).
- **Running jobs (none mine):** P3 PIDs 5901, 15185, gap-filler 7091; horizon PIDs 6108/6109 (s46 E_m=15).
- **Score after: 4/10, REJECT.** Rebuild is reproducible and the paper is 3.4 pp shorter, but outcomes are
  still missing and the main text is 12.75 pp.
- **Top 3 priorities:**
  1. Harvest P3 (`cd paper && make numbers`) and the s46 horizon cell (`\csHz...FortySixEfifteen`; then
     replace the \PENDING sentence in S-IV and revisit "Our reading is that the attack sits near a threshold").
  2. Continue the cut: S-III proofs (keep statements + one-sentence sketches) and S-VI rule details, then
     prose trimming; decide the supplement overflow (seedcal table compression vs. realizability out).
  3. When primary cells P2/P4 (FLTrust IID) land, add the 8-row confirmatory table in place of prose.

## Iteration 16 - 2026-10-21 - Second cut: proofs, rule details, falsify check and FoolsGold diagnostic to the supplement; prose tightened throughout (main 12.75 -> 9.88 pp, 10 pages); realizability per-row table replaced by a generated artifact file to keep the supplement under 6 pp

- **State at start (~19:58):** P3 96/1,040 JSONs (PIDs 5901, 15185, gap-filler 7091); 111 at the end. Horizon
  probe PID 6108 (CPU): s46 E_m=15 still running, no new JSON. The only ERROR lines in P3 logs are the three
  known pre-fix OOM logs. I started no job.
- **Reviewer score before: 4/10, REJECT.** Blockers: (1) outcomes missing for most rules (P3 ~9%); (2) main text
  12.75 pp vs hard 10; (3) supplement could not absorb the remaining moves (4.7 + ~1.4 > 6).
  Found this iteration: (4) Sec. VI-C said "the only FoolsGold cells run with the copy are one clean and one
  attacked replay" although P3 (which runs with the copy) already has FoolsGold Dir clean cells; rewritten.
- **What I changed** (backups main.tex.pre-iter16.bak, supplement.tex.pre-iter16.bak):
  - **Moved verbatim to the supplement** (new S-III "Proofs and checks of the mechanism results"): proofs of
    Prop. 1, Cor. 1, Cor. 3, Cor. 4, Lemma 1 (main keeps statements + one-sentence `proof[Proof sketch]`), the
    probe numbers for Cor. 3, the falsified-counter check (S-III-A, label sup:falsify; main keeps a 5-line
    summary with \ffMaxRelErr and \ffAmpNeg) and the FoolsGold diagnostic (S-III-B, sup:fgdiag; main keeps the
    label-skew conclusion with \csFgBaseNMajorDDoS, \csFgBaseCA). S-VI: the six rule-family paragraphs +
    hyperparameters (sentences duplicated in main removed); main keeps Table II + a new "Implementation"
    paragraph (negative controls, distance-rule exposure in attacked runs, NormClip/FLAME inflation
    \pfDiagNormInflDir, FLAME trainable-only noise, exclusion thresholds, GradCos status, AlignIns split
    prediction, Bulyan f clamp, untuned hyperparameters). Both \TOMOVE placeholders are gone.
  - **Supplement overflow:** the 12-row realizability table (tab:realize) is replaced by
    `results/artifact/realizability_ciciot2023.md`, all 21 rows x 13 statistics, written by make_numbers.py
    from results/realizability_ciciot2023.json (new macro \rzNrowsArtifact; numbers.tex otherwise unchanged);
    the supplement defines the columns in prose and cites the file; README lists results/artifact/. The
    seed-46 investigation prose in S-IV was condensed (same claims, same macros).
  - **Main-text tightening (no claim removed):** contributions list and roadmap (0.69 -> ~0.4 pp), threat model,
    "counter is attacker-controlled", Statistics method sentence, Cor. 1 discussion + Eq. bufcos (now the
    inequality only), Cor. 2 discussion, norm/coordinate-wise rules, inertness + verification merged, scope
    subsection, geometry subsection, A/B Design (absorbs the "first campaign" paragraph), Results-so-far
    (i)-(iv), FLTrust real-data paragraph, FoolsGold/FLAME mechanism paragraphs, distance rules + negative
    controls merged, retro paragraph, "Why the hazard survives review", Limitations (run-in list), Conclusion
    (half; the trigger-premise sentence now only in contributions/abstract), Related Work (minor).
  - **P3 harvest** (`make numbers`, rc 0, 3 min): 107 cells at analysis. New: Krum Dir attacked n=5 (DR 1.000
    both arms; CA fixed-defect -0.002, 0/5 seeds positive, two-sided p 0.062, exploratory, not significant);
    FLTrust Cor. 3 log unchanged (300 rounds, 24 with q_i+q_0<=1, 0 non-positive cosines, 10 defect runs, max
    exclusion 0.000). PREREG: no new confirmatory cell (P1/P3/S3 n=5; P2/P4/S1/S2/S4 n=0); 0/4 primary,
    0/4 secondary supported (interim). Exploratory: 38 tests, 0 survive family or global Holm.
    results/fltrust_falsify.json float-noise rewrite reverted again.
- **Build/check:** latexmk rc 0, 0 undefined refs/cites, 0 "??". **IEEEtran pages: main 10 (ends at 9.88) /
  supplement 6 (ends at ~5.91).** check_manuscript: all PASS except the gate (439 unresolved P3 results).
- **Page arithmetic for the next agent:** P3 needs ~1-1.5 pp (outcome table + confirmatory result), so main must
  reach ~8.5-9 before they land: ~1 pp more. Largest remaining blocks (page_budget.py): bibliography 0.95,
  Tables III/IV 0.59 (merge/compact into one outcome table when P3 lands), Cor. 3 block ~0.4, Cor. 4 + "three
  consequences" ~0.35, Lemma + FoolsGold ~0.4, Related Work ~0.7, intro ~0.55. The supplement is full (5.91):
  anything more moved there must displace something; candidates for generated artifact files are the seedcal
  table (Table S-III, 0.22 pp) and the first-campaign retro section (0.5 pp).
- **Running jobs (none mine):** P3 PIDs 5901, 15185, gap-filler 7091 (111/1,040 at 20:19); horizon PID 6108
  (s46 E_m=15).
- **Score after: 4/10, REJECT.** Length is now inside the cap with no claim dropped, but outcomes are still
  missing and the P3 table will push the main text back over 10 unless ~1 pp more is cut.
- **Top 3 priorities:**
  1. Harvest P3 + s46 horizon (`cd paper && make numbers`; replace the \PENDING sentence in S-IV and revisit
     "near a threshold" if s46 implants).
  2. Cut ~1 pp more from main (FLTrust/falsify block: move "three consequences" and the real-data q-log details
     to S-III; compress Related Work and intro; consider merging Tables III/IV into one compact outcome table).
  3. Draft (commented out) the 8-row confirmatory table from the \pfPre macros so it can be switched on when
     P2/P4/S1/S2/S4 land, and budget its space now.

## Iteration 17 - 2026-10-21 - Novelty check (closest prior: a Flower DP-clipping issue, Oct 2026, and BNGuard); confirmatory-hypothesis table wired to the \pfPre macros; third cut (main 9.88 -> 9.28 pp incl. the new table); horizon s46 harvested

- **State at start (~20:20, resumed ~22:20 after a usage-limit pause):** P3 111 -> 192/1,040 JSONs (PIDs 5901,
  15185, gap-filler 7091; 3 logs with ERROR = the known pre-fix OOM ones). Horizon probe finished 21:19
  (s46 E_m=15 done, HORIZON COMPLETE). I started no job; the coordinator's edit to AGENT_BRIEF.md is not mine
  and is left uncommitted.
- **Reviewer score before: 4/10, REJECT.** Blockers: (1) P3 outcomes missing for most rules (18%; no new
  confirmatory cell); (2) no positioning against prior work on BatchNorm buffers / the counter in FL
  aggregation, which a hostile reviewer will search; (3) main at 9.88 pp leaves no room for the P3 outcome
  text; (4) confirmatory result only in prose.
- **Novelty search (WebSearch, 2026-10-21).** Queries: "num_batches_tracked federated learning aggregation
  robust"; "BatchNorm buffers Byzantine-robust aggregation federated learning state_dict cosine similarity
  defense"; "\"non-trainable parameters\" federated learning poisoning defense batch normalization statistics
  attack"; "\"num_batches_tracked\" FedAvg averaging bug flower OR fedml OR github issue"; "backdoor attack
  federated learning manipulating BatchNorm running statistics malicious client"; "Krum FLTrust robust
  aggregation should exclude batch normalization layers flattened model update evaluation pitfall";
  "federated learning integer buffer counter dominates update norm clipping cosine similarity BatchNorm
  state_dict pitfall paper"; "Byzantine attack batch normalization statistics federated learning vulnerability
  robust aggregation ignores running mean variance"; "\"num_batches_tracked\" arxiv federated learning paper";
  "BNGuard ... MobiHoc 2025". Findings (each verified by fetching the page):
  - **Closest: Flower issue flwrlabs/flower #8298** (opened 6 Oct 2026 by a third party, open; fix PR #8381,
    17 Oct 2026, open): Flower's DP clipping helpers include the 0-d int `num_batches_tracked` in get_norm but
    cannot rescale it, so the clip factor ~C/B shrinks every real update. This is exactly the norm term of our
    Eq. (norm) for one clipping routine (cf. our NormClip/FLAME). It postdates our survey (Sep 2026) and covers
    neither cosine/distance rules, nor trust scores/histories, nor an exact decomposition, nor outcomes. Cited
    as concurrent (`flower2026issue8298`, @misc).
  - **BNGuard** (Xu, Zhang, Hu, arXiv:2509.13219, "to appear in MobiHoc 2025" per arXiv; same authors as
    AlignIns): reads BN *running statistics* deliberately as a detection signal for OOD backdoors. Opposite
    use; does not concern the counter. Cited (`xu2025oba`).
  - FBN (Guerraoui et al., already cited) makes the statistics' aggregation Byzantine-robust; now said so.
  - No paper found that analyses `num_batches_tracked` (or any non-trainable buffer) as a coordinate of the
    vector Byzantine-robust rules decide on, nor a decomposition of cosine/distance into trainable + buffer
    parts. A third-party GitHub PR (SathishKumarAI/federated-yolov8..., #64) mentions the counter differing by
    the epoch's batch count in a personal project; not citable, not about robust rules.
  - Related Work "Model state" paragraph rewritten accordingly: the claim is now "we found no work on what
    the counter does to the client-level decisions of Byzantine-robust rules"; the counter-in-norm effect for
    one DP clipping routine is credited to the Flower issue.
- **Confirmatory table (Table III, tab:prereg)**, live, single column: P1-P4, S1-S4 with n, sign counts, diff,
  one-sided p, Holm p, supported (yes/no). New macro `\pfPre<Id>Sup` in analyse_postfix.py (yes/no/\PENDING);
  inside the table \PENDING renders as a red dash (gate still counts it). Fills automatically on `make numbers`.
  Text notes that Holm over four can reach 0.05 only from n=7. Statistics paragraph shortened (points to it).
- **Third cut (backups main.tex.pre-iter17.bak, supplement.tex.pre-iter17.bak), no claim removed:** intro
  first paragraphs, contributions + roadmap, Related Work (backdoors, robust aggregation, evaluation, FL-IDS),
  Cor. 1 discussion, Statistics, Design, BSR paragraph, "counter is attacker-controlled", FLTrust real-data
  paragraph (first-campaign numbers now parenthetical), the "three consequences" + falsify check merged into
  one paragraph, Lemma 1 discussion, "earlier version" paragraph, recommendations, two limitations,
  Conclusion; "Results so far" became "Exploratory cells so far" (FLTrust (iv) points to P1).
- **Horizon probe (harvested, n=1 per cell):** s46 E_m=15 over 40 rounds: BSR first > 0.5 at round 14, falls
  back, stays > 0.5 after round 17, last-five 0.989. Supplement S-IV PENDING sentence replaced
  (`\csHz...FortySixEfifteen`); main mentions it in Attack calibration. Both horizon cells support the
  "near a threshold / censored at 15 rounds" reading; the campaign's implant set is unchanged (P3 FedAvg
  excludes seed 46: \pfImplantExclDir=46).
- **P3 harvest** (`make numbers`; 192 cells at analysis): 73 exploratory tests, 0 survive family or global
  Holm. PREREG unchanged: P1/P3/S3 n=5, P2/P4/S1/S2/S4 n=0; 0/4 primary, 0/4 secondary supported (interim).
  results/fltrust_falsify.json float-noise rewrite reverted again. `make numbers` stopped at LaTeX once
  (\path in a caption; fixed), the generators all ran.
- **Build/check:** latexmk rc 0, 0 undefined refs/cites, 0 "??". **IEEEtran pages: main 10 (ends at 9.28,
  was 9.88; includes the new table) / supplement 6 (~5.95).** check_manuscript: all PASS except the gate
  (386 unresolved, all P3).
- **Running jobs (none mine):** P3 PIDs 5901, 15185, gap-filler 7091 (192/1,040 at 22:30).
- **Score after: 4/10, REJECT.** Positioning is now defensible and verified; length has ~0.7 pp headroom for
  P3 text; outcomes still missing.
- **Top 3 priorities:**
  1. Harvest P3 (`cd paper && make numbers`). When FLTrust IID / NormClip cells land, Table III fills itself;
     then write the one-paragraph confirmatory result and retire the PENDING sentence in the abstract.
  2. Supplement is at ~5.95/6 pp: anything added there must displace something (seedcal table -> artifact).
  3. Consider a short "Concurrent report" sentence in Sec. V (scope) if the Flower PR #8381 merges, and
     re-check Flower's quickstart (survey row) against the current release before submission.

## Iteration 18 - 2026-10-21 - Explanatory schematic (Fig. 1) drawn from the generated macros; Flower overclaim fixed with a verified check of Flower's built-in Krum/Bulyan; abstract/intro tightened; P3 harvest (200 cells, no new confirmatory cell)

- **State at start:** P3 199 JSONs (PIDs 5901, 15185, gap-filler 7091 running; none mine). I started no job.
- **Reviewer score before: 4/10, REJECT.** Hostile first read, ranked: (1) outcomes missing (P3 ~19%; P2/P4/S1/S2/S4
  still n=0); (2) no explanatory figure: the only figure was a per-round diagnostic plot, so the central mechanism
  (counter dominates norm, compresses cosines) had to be reconstructed from equations; (3) **overclaim:** Flower's
  quick-start was called "exposed" under a caption defining exposure as "enters the vector the rule decides on", yet
  the quick-start uses FedAvg, which decides nothing (a reviewer reading our own Table II would catch this);
  (4) abstract diluted by the trigger-audit sentence and over 250 words once edited; (5) notation is consistent
  (d=(u,b), b=(r,c), s_i, q_i, B_i, L) -- no change needed.
- **Fixes:**
  - **Fig. 1 (fig:schematic, TikZ, one column)**: (a) bars of coordinates vs squared norm of one transmitted
    update (bottom bar width computed by pgfmath from \pfDiagBufNormShareDir; counts \dfNTrain, \dfNBuf); (b) client
    angle fans drawn at acos(\pfDiagCosSigDir) and acos(\pfDiagCosFullDir). No hand-typed number; caption says
    lengths are schematic and the buffer sliver is widened. tikz added to preamble.tex.
  - **Flower scope, verified:** new `experiments/counter_defect/flower_builtin_check.py` -> results/flower_builtin_check.json
    (flwr 1.30.0): Flower's built-in Krum/MultiKrum/Bulyan (`multikrum.py::compute_distances`) concatenate every
    array of the ArrayRecord; squared distance between two quick-start-style records exceeds the counter-free value by
    exactly (B_i-B_j)^2 (1369 for B=3 vs 40); DP `get_norm` also includes the counter. Sec. III-A, abstract,
    contributions and Table I (dagger footnote) now say the quick-start itself uses FedAvg and that Flower's own
    distance strategies read the counter. SURVEY.md updated.
  - Abstract rewritten to 248 words (check passes; dropped the distance-share number, kept in Sec. VI-A); intro
    numbers paragraph merged and points to Fig. 1; geometry subsection, conclusion, "Why the hazard survives review",
    "earlier version" paragraph and the evaluation related-work paragraph compressed (no claim removed).
- **P3 harvest** (`make numbers`, rc 0): 200 cells. PREREG unchanged: P1/P3/S3 n=5, P2/P4/S1/S2/S4 n=0; 0/4 primary,
  0/4 secondary supported (interim); no confirmatory paragraph written (no FLTrust IID or NormClip cell yet).
  Exploratory: 76 tests, 0 survive family or global Holm. results/fltrust_falsify.json float-noise rewrite reverted.
- **Build/check:** make rc 0, 0 undefined refs, 0 "??". **IEEEtran pages: main 10 (ends at 9.35, was 9.28; includes
  the new figure) / supplement 6 (unchanged).** check_manuscript: all PASS except the gate (386 unresolved, all P3).
  Backups main.tex.pre-iter18.bak, supplement.tex.pre-iter18.bak.
- **Running jobs (none mine):** P3 PIDs 5901, 15185, gap-filler 7091.
- **Score after: 4/10, REJECT.** Presentation and scope claims are now defensible; outcomes still missing.
- **Top 3 priorities:**
  1. Harvest P3; when FLTrust IID / NormClip cells land write the confirmatory paragraph and retire the abstract PENDING.
  2. Budget: ~0.65 pp headroom for P3 text; the two big outcome tables (0.59 pp) may need merging into one.
  3. Consider whether Fig. 2 (per-round diagnostics) can move to the supplement now that Fig. 1 carries the story
     (saves ~0.18 pp) -- supplement is full, so only if something there moves to an artifact file.

## Iteration 19 - 2026-10-21 - Generality probe on a standard BatchNorm image model (ResNet-20 / CIFAR-10, real federated rounds, CPU); P3 harvest (S1 now n=5); supplement trimmed to make room

- **State at start (22:49):** P3 219 JSONs; coordinator had started experiments/postfix/run_p3_prereg.sh at 22:46
  (2 more GPU lanes, 36 FLTrust/NormClip/FLAME jobs of the registered families; log results/postfix_p3/campaign_prereg.log;
  committed here with results/postfix_p3/jobs_prereg.txt, as asked). GPU 8 lanes ~5.1/8 GB; I added no GPU job.
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) outcomes still missing (P2/P4/S2/S4 n=0); (2) **generality**:
  every outcome and every real-data diagnostic is one CNN+LSTM (L=1) on tabular IDS data; the only second
  architecture was a synthetic-input ResNet-18 geometry probe, so "does it reach decisions elsewhere?" was unanswered;
  (3) supplement full (5.95/6) so any new evidence had to displace text.
- **Generality experiment (new, CPU, mine):** `experiments/generality/cifar_resnet20.py` + `run_generality.sh`.
  ResNet-20 (option A, 19 BN layers, 269,722 trainable / 1,395 buffer coords, default momentum), CIFAR-10 (local copy
  in data/cifar10, sha256 recorded per run), 10,000 training images, 10 clients, 2 label flippers (y->y+1), 1 local
  epoch SGD lr 0.05 mom 0.9 wd 5e-4 batch 32, FLTrust root set 100 images (B_0=4), IID or label-Dirichlet(0.5),
  20 rounds, seeds 0-2. Every round the SAME client updates are scored by Krum, Multi-Krum, FLTrust on (full
  state_dict / state_dict without the counter / parameters()) -- a decision-level counterfactual; closed-loop arms
  (fltrust_full/trainable, mkrum_full/trainable, Dirichlet) are queued for outcomes. Resumable (per-round checkpoints
  in results/generality_cifar/_ckpt, not committed). Generator `paper/make_numbers_generality.py` ->
  `paper/numbers_generality.tex` (\gc... macros; unfinished FedAvg runs contribute their completed rounds to the
  decision statistics, closed-loop accuracy only from finished runs). Added to `make numbers` and preamble.
- **Evidence (interim, rounds 1-7 of 20, 3 seeds x 2 partitions; results/generality_cifar/_ckpt via the generator):**
  counter share of ||d_i||^2 median 98.0% (Dir) / ~99% (IID); FLTrust honest cosine to root 0.969 full vs 0.124
  trainable (Dir); label flippers get 20.0% of FLTrust trust (= head count, never zeroed) on the full vector vs 5.1%
  (zeroed 69% of attacker-rounds; honest zeroed 11.3%) on the trainable one; IID 20.0% vs 1.3%. Krum's pick differs
  full vs trainable in 100% of Dir rounds and in 100% full vs counter-free (counter alone); under IID (equal B_i)
  full vs counter-free differ in 0% of rounds, as Cor. 2 predicts, and the remaining full-vs-trainable differences
  (~62%) come from running statistics. Multi-Krum keeps 1.67 vs 1.29 attackers (Dir). Test accuracy at round 5:
  0.17-0.33 (early training; the decision statistics are early-round statistics -- say so if they shift by round 20).
- **Paper:** supplement S-II gains "Real images, real federated rounds" + Table S-I (tab:gen); main Limitations
  "One architecture for outcomes" now quotes the CIFAR result in one sentence (macros) and says accuracy outcomes
  there are not yet measured. To fit, supplement compressed without dropping claims: seed-46 poisoned-data
  enumeration, realizability intro/"pull against each other", withdrawn-findings preamble + FoolsGold/colluder
  items, round-one section, "Reductions, stated". Backups main.tex.pre-iter19.bak, supplement.tex.pre-iter19.bak.
- **P3 harvest (`make numbers`, rc 0):** 219 runs. PREREG: S1 (NormClip Dir CA) now n=5, 4+/1-, diff +0.008,
  p=0.0625, Holm 0.25, not supported (interim); P1/P3/S3 n=5 unchanged; P2/P4/S2/S4 n=0. 0/4 primary, 0/4 secondary
  supported. results/fltrust_falsify.json float-noise rewrite reverted again.
- **Build/check:** latexmk rc 0, 0 undefined refs/cites, no overfull in supplement. **IEEEtran pages: main 10 (ends at
  9.38, was 9.35) / supplement 6 (5.96).** check_manuscript: all PASS except the gate (368 unresolved, all P3).
- **Running jobs:** MINE: generality campaign, systemd-inhibit PID 54368 (bash 54370, xargs 54374; 6 lanes x 2
  threads), log results/generality_cifar/campaign.log, per-run logs results/generality_cifar/logs/. ~7 min/round
  under current load: wave 1 (6 FedAvg runs) ends ~01:30, wave 2 (FLTrust closed loop, Dir) ~04:00, wave 3
  (Multi-Krum closed loop) ~06:30 on 22 Oct. Resumable: re-run `experiments/generality/run_generality.sh` after any
  crash. NOT mine: P3 PIDs (run_p3, gap-filler, run_p3_prereg).
- **Score after: 4/10, REJECT.** Generality objection now has a real-data, real-federation answer at the decision
  level (interim); outcomes are still missing both here and in P3.
- **Top 3 priorities:**
  1. Harvest P3 (`cd paper && make numbers`); write the confirmatory paragraph when P2/P4/S2/S4 land.
  2. Harvest the generality campaign (make numbers runs the generator): replace "interim" in the supplement/main
     sentence once all 6 FedAvg runs reach round 20, check the statistics still say the same at rounds 8-20, and
     write the closed-loop FLTrust/Multi-Krum accuracy sentence (n=3, exploratory, no p-value claims).
  3. Keep main <= ~9.5 pp: the P3 confirmatory paragraph must be paid for by cuts.

## Iteration 20 - 2026-10-22 - Generality campaign harvested (final, closed loop included); P3 at 475 cells: all four primary hypotheses 5/5 in the predicted direction (not yet supportable), S2 final and not supported; fixed-arm FLTrust IID "shutdown" found and reported

- **State at start (06:06):** generality campaign finished 04:19 (18 runs, all rc=0, 20/20 rounds). P3 475/1040;
  run_p3_prereg.sh 13/36 jobs (NormClip IID s42-46 both arms, FLAME Dir s47-51 clean full). 8 GPU lanes; I added none.
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) confirmatory outcomes missing; (2) the generality evidence was
  interim and had no accuracy outcome; (3) **new, found this iteration:** the fixed-arm FLTrust IID cells show FPR
  0.996 / DR 1.000, which a reviewer would read either as a broken fix or as a meaningless "detection".
- **Fixes:**
  - **Generality harvest.** make_numbers_generality.py now also emits in-loop decision macros (\gcFtLoopFull/Tr,
    \gcMkLoopFull/Tr: what the driving rule did in its own loop) and \gc{Ft,Mk}AccMin/Max. Final (3 seeds x 2
    partitions, 20 rounds): counter share 99.0% (Dir)/99.5% (IID); FLTrust flipper trust 19.9% full vs 1.8% trainable
    (Dir), 19.6 vs 0.5 (IID); flippers zero-trusted 89.2% on trainable (honest 9.6%). Closed loop (Dir, n=3): FLTrust
    driven by full gives flippers 20.1% of trust vs 4.7%; Multi-Krum keeps 1.62 vs 1.15 flippers/round. **Accuracy does
    not separate the arms**: FLTrust 0.130 vs 0.147 (near chance in both, 100-image root barely trains in 20 rounds),
    Multi-Krum 0.398 vs 0.404 (2/3). Supplement paragraph rewritten (interim dropped, closed-loop result added with the
    weak-attack caveat); main Limitations sentence now says accuracy does not separate at n=3.
  - **Fixed-arm FLTrust shutdown (new diagnostic, make_numbers_calib6.py -> \csFltShut*):** in all 10/10 fixed-arm IID
    FLTrust runs (clean+attacked, s42-46) every client gets zero trust from round 6-15 on and the model freezes (CA
    0.549 vs 0.680 defect); Dir: 2/10 runs. Sec. VI-C now says the IID DR of 1.000 is a shutdown, not detection, and the
    old explanation ("disagrees with non-IID honest updates") was wrong (IID is worse) and is removed.
  - **Confirmatory paragraph (interim, honest):** P1-P4 each n=5, 5+/0-, one-sided p=0.031, Holm 0.125 -> not supported
    (n=5 cannot reach 0.05 under Holm-4); P2/P4 are blind and also 5/5 but their effect is the shutdown. S2 (NormClip IID
    CA) complete at n=10: 8/2, diff +0.001, p=0.072, Holm 0.25 -> **not supported** (final for S2). S1 n=5 4/1, S3/S4 3/2.
    0/4 primary, 0/4 secondary supported. RE-CHECK comment marks the representative-P1-macro sentence.
- **Build/check:** latexmk rc 0, 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.49, was 9.38) / supplement 6
  (5.96).** check_manuscript: all PASS except the gate (139 unresolved, all P3). Backups main.tex.pre-iter20.bak,
  supplement.tex.pre-iter20.bak. results/fltrust_falsify.json float-noise rewrite reverted again.
- **Running jobs (none mine):** P3 PIDs 5901, 15185, 52037 (prereg runner, 13/36 done at 06:05).
- **Score after: 4/10, REJECT.** Generality is now a clean decision-level result with an honest null on accuracy; the
  FLTrust story is sharper but less flattering (the counter masks a FLTrust that, read correctly, shuts down here).
- **Top 3 priorities:**
  1. Harvest P3 as seeds 47-51 land for FLTrust IID/Dir (P1-P4 reach n=10 -> first point where support is possible);
     then retire the abstract/intro/conclusion PENDING sentences with macro-driven text.
  2. The FLTrust shutdown needs a mechanism sentence or a quick CPU probe (why trainable cosines to a 300-row root go
     <=0 near convergence under IID: root update noise vs vanishing client updates?) -- a reviewer will ask.
  3. Main is at 9.49 pp: any new text must be paid for by cuts (aim <= 9.5).

## Iteration 21 - 2026-10-22 - Mechanism of the fixed-arm FLTrust IID shutdown found (class-balanced root, not a bug); PREREG Amendment 1 (interpretation only); P3 harvest 480 cells

- **State at start (06:10):** P3 475 -> 480/1040 after `make numbers` (Krum IID clean now paired); prereg macros
  unchanged (P1-P4 n=5, 5/0 each, Holm 0.125, 0/4 supported; S2 final, not supported). 8 GPU lanes (not mine).
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) confirmatory outcomes still interim (n=5); (2) fixed-arm FLTrust
  IID shutdown unexplained -- a reviewer reads it as a broken fix, and it is the effect behind blind P2/P4; (3) closed-loop
  generality has no accuracy separation; (4) main at 9.49 pp, no room.
- **Fix: shutdown mechanism (experiments/fltrust_shutdown/replay.py, CPU, 3x4 threads).** Replays clean P3 fixed-arm
  cells (exact P3 config from the result JSON) logging every trust cosine, ||g0||, client norms, per-tensor <g_i,g0>,
  test prediction histogram, and RNG-neutral counterfactual root updates from the same global model (balanced+class
  weights, natural root (same 296 rows, uniform over training rows), natural+weights, a second balanced draw).
  Results (results/fltrust_shutdown/replay_{iid_s42,iid_s43,dirichlet_s42}.json, 12 rounds each):
  - replay reproduces the P3 shutdown rounds exactly (s42: 6, s43: 7; round-1 CA identical to P3) and it persists to
    round 12 (absorbing; prediction histogram frozen).
  - **Not a code bug** (fltrust.py checked: cosine on the trainable mask, ReLU, rescale; correct). **Not a vanishing
    root update** (||g0|| 0.47-0.61 in shutdown rounds vs 0.51-0.60 before). **Not mini-batch noise** (a second balanced
    draw agrees, cos >= 0.91, and also gives all clients <= -0.04).
  - **Cause: the class-balanced root** (37 rows/class; paper discloses it, Cao et al. assume root ~ training dist.). In
    shutdown rounds every client's cosine to the balanced root is -0.38..-0.07; to a natural root of the same size
    +0.60..+0.81; natural vs balanced root updates point apart (cos -0.61..-0.43). Training the balanced root with the
    clients' class weights does not help (<= -0.18). >= 86% of the negative inner product sits in lstm.weight_hh_l0.
    Once the model fits the majority classes the balanced root pulls toward the minority classes against every IID
    client; with sum of trust = 0 the implementation keeps the global model (FLTrust's formula is undefined there), so
    the next round repeats the conflict. Dirichlet replay: max 8/10 excluded, 0 full shutdowns in 12 rounds.
  - New macros \fs* (paper/make_numbers_fltshut.py -> numbers_fltshut.tex; in Makefile `numbers` and preamble).
    \csFltShutDef{N,Runs} added to make_numbers_calib6.py: defect arm 0 of 20 runs shut down.
  - Paper: main Sec. VI-C now gives the cause in 3 sentences + Dir/defect shutdown counts; confirmatory paragraph says
    P2/P4 can confirm Cor. 3's prediction, not detection (amendment cited); Discussion lists the balanced-root shutdown
    among non-counter failures. Supplement: new subsection S-III-D (sup:fltshut). Supplement cuts to pay for it
    (overview sentence, seed-46 timing detail, first-campaign bullets, realizability sentences).
- **PREREG_P3.md Amendment 1 (dated, interpretation only).** Seen: all 480 cells incl. P1-P4 at n=5 and the shutdown.
  Tests, families, Holm, n=10 timing unchanged; P2/P4 NOT dropped or re-scored. Reporting rule: a supported P2/P4 is
  reported as confirming Cor. 3's literal prediction, never as detection; total-exclusion counts per arm/partition are
  reported beside P1-P4; natural-root runs are exploratory and cannot rescue any hypothesis. Honest note: the
  registration foresaw only the opposite degenerate case ("fixed arm excludes no one").
- **Code:** src/defenses/fltrust.py gains `defense.fltrust_root: balanced|natural` (default balanced = every campaign so
  far; P3 unaffected). configs/fltrust_natroot.yaml (P3 trainable config, fltrust, natural root, out results/fltrust_shutdown).
- **Build/check:** latexmk rc 0, 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.53, was 9.49) / supplement 6
  (5.98).** check_manuscript all PASS except the gate (131 unresolved, all P3). Supplement has 9 \fsNat* PENDING macros
  until the natural-root runs land.
- **Running jobs:** mine: natural-root closed loop, `experiments/fltrust_shutdown/run_natroot.sh` under systemd-inhibit,
  PID 101660 (bash 101661), 3 CPU lanes x 4 threads: clean IID s42-44, clean IID s45-46, attacked IID s42-43 (me15);
  logs results/fltrust_shutdown/log_natroot_*.log, campaign log natroot_campaign.log; resumable (run_sweep skips done
  cells). ETA clean ~2-3 h, attacked ~4-5 h from 06:50. Not mine: P3 PIDs 5901, 15185, 52037.
- **Score after: 4/10, REJECT** (unchanged: the shutdown is now explained and honestly scoped, but it also shows that
  this paper's FLTrust fixed arm is a weak, root-dependent baseline, and the confirmatory family is still n=5).
- **Top 3 priorities:**
  1. Harvest natroot (`python3 paper/make_numbers_fltshut.py`): if the natural-root fixed arm neither shuts down nor
     loses CA, consider (exploratory, labelled) reporting FLTrust's counter effect with a natural root too; do NOT swap
     it into P1-P4. If it also shuts down, the root-distribution explanation is incomplete -- say so.
  2. Harvest P3 as seeds 47-51 of FLTrust land (P1-P4 reach n=10); retire PENDING abstract/intro/conclusion sentences.
  3. Main is 9.53 pp; pay for any new text with cuts (aim <= 9.5).

## Iteration 22 - 2026-10-22 - Natural-root FLTrust harvested (shutdown gone, but no detection under IID); P1 and P3 supported at n=10 (interim family); Dirichlet natural-root runs launched

- **State at start (09:47):** natroot IID campaign finished 09:38 (0 ERROR lines). P3 605 -> 616/1040 after two
  `make numbers` runs (the first read s51 FLTrust-Dir-attacked mid-write and gave P3 n=9; the rerun gives n=10). 8 GPU
  lanes (not mine); I added none.
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) confirmatory family interim; (2) FLTrust's fixed arm looked like a
  root artefact, unresolved whether any root makes it a detector; (3) closed-loop generality has no accuracy separation;
  (4) main page budget.
- **Natural-root harvest (exploratory, `make_numbers_fltshut.py`):** IID fixed arm with a training-distribution root:
  clean 0/5 shutdowns, FPR 0.000, CA 0.704 (balanced fixed 0.549, defect 0.680); attacked n=2 DR 0.000, FPR 0.000, BSR
  0.066. **So the class-balanced root is confirmed as the cause of the shutdown, and with the natural root the IID fixed
  arm admits every flipper, exactly as the defect arm does.** Consequence written into main Sec. VI-C: under IID neither
  root makes FLTrust a detector; P2/P4 therefore measure the root (already the Amendment-1 reading). Supplement S-III-D
  gives BSR and the Dirichlet line (\fsNatDir*, n=1 clean so far: FPR 0.120 vs ~0.64 balanced-root fixed arm; attacked
  PENDING). Generator now also emits \fsNat{,Dir}{Clean,Atk}{N,Fpr,CA,Shut,Dr,Bsr}.
- **Confirmatory (make numbers, interim):** P1 (FLTrust Dir clean FPR) n=10, 10/0, diff +0.638, p=0.0010, p_H=0.0039;
  P3 (FLTrust Dir DR) n=10, 9/0 (+1 tie, s50 DR 0 vs 0), diff +0.510, p=0.0020, p_H=0.0059 -> **both supported; their
  cells are complete, and Holm's p_H <= 4p keeps them supported whatever P2/P4 give.** P2/P4 still n=5 (5/0, p_H 0.0625).
  Secondary: S2 final not supported; S1 n=5, S3 n=10 5/5, S4 n=5; 0/4 supported. Main confirmatory paragraph rewritten
  from macros (supported count, P1/P3 stats, honest reading: confirms Cor. 3, not useful detection since fixed-arm DR ~ FPR).
- **Cuts to pay:** confirmatory floor sentence, limitations calibration sentence, sign-flip definition, GradCos sentence,
  hyperparameter sentence (Implementation). Supplement natroot sentence tightened.
- **Build/check:** latexmk rc 0, 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.61, was 9.53) / supplement 6
  (~6.0, PDF 6 pp; page 6 is nearly full -- no room).** check_manuscript all PASS except the gate (51 unresolved, P3).
  Backups main.tex.pre-iter22.bak, supplement.tex.pre-iter22.bak. fltrust_falsify.json float noise reverted again.
- **Running jobs:** mine: Dirichlet natural-root FLTrust, `experiments/fltrust_shutdown/run_natroot_dir.sh` under
  systemd-inhibit, PID 186783 (bash 186785), 2 CPU lanes x 4 threads: clean Dir s42-44 (~25 min/seed; s42 done 10:10),
  attacked Dir s42-44 (me15, ~1-1.5 h/seed). Logs results/fltrust_shutdown/log_natroot_{clean,attacked}_dirichlet_s42.log,
  campaign log natroot_dir_campaign.log; ETA ~13:30. Not mine: P3 PIDs 5901, 15185, 52037.
- **Score after: 4/10, REJECT** (P1/P3 supported is real progress, but they confirm a mechanism prediction, not a defense
  benefit; FLTrust is now shown to be a weak baseline under both roots in IID; most of P3 still pending).
- **Top 3 priorities:**
  1. Harvest Dir natroot (`python3 paper/make_numbers_fltshut.py`): if the natural-root fixed arm separates DR from FPR
     under Dirichlet, that is the first sign the fix yields *useful* FLTrust detection (exploratory; report beside P1/P3,
     never swap into them). If DR ~ FPR or DR 0, say FLTrust is not a useful detector here under either root.
  2. Harvest P3 as P2/P4 (FLTrust IID s47-51) land; when every cell of the eight hypotheses reaches n=10 the family
     becomes final -- then retire the abstract/contribution PENDING sentences with macro-driven text.
  3. Main 9.61 pp, supplement full: any addition must be paid for by cuts (aim <= 9.5).

## Iteration 23 - 2026-10-22 - Dirichlet natural-root FLTrust harvested (no detection in either partition); abstract and contribution PENDING retired; framing re-read against the data

- **State at start (12:00):** natroot Dirichlet campaign finished 11:58 (0 ERROR lines; clean + attacked s42-44).
  P3 692/1040 after `make numbers`; prereg runner 24/36 jobs (remaining 12 = IID FLAME/FLTrust/NormClip s47-51, so
  P2/P4 still n=5, ETA a few hours). 8 GPU lanes (not mine); I added none and started no jobs.
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) family interim (P2/P4 n=5); (2) abstract/contribution still
  promised outcomes as PENDING while the decisive FLTrust result exists; (3) risk of overselling: the fix restores
  FLTrust's exclusions but not detection; (4) page budget.
- **Natural-root Dirichlet harvest (exploratory, `make_numbers_fltshut.py`):** clean n=3 FPR 0.120, CA 0.648, 0
  shutdowns; attacked n=3 **DR 0.000 in every round of every seed**, FPR 0.183, BSR 0.042. So with a
  training-distribution root FLTrust excludes no attacker in either partition (IID DR 0.000, n=2), and with the
  balanced root its Dirichlet "detection" (DR 0.510) comes with FPR 0.585. **Settled: FLTrust is not a useful detector
  in this setting under either root or partition.** Written into main Sec. VI-C (one sentence), supplement S-III-D
  (one clause), contribution 3 and the conclusion.
- **Confirmatory status:** P1 n=10 10/0 p_H 0.0039, P3 n=10 9/0 p_H 0.0059 (supported, final cells); P2/P4 n=5 5/0
  p_H 0.0625. Secondary: S1 (n=10, p 0.048), S2 (p 0.072), S3 (p 0.90) complete; since Holm's multiplier for the
  smallest of them is >=3, none can become supported whatever S4 gives -> main text now says "S1-S3 are complete and
  cannot be supported". S4 n=5.
- **Text:** abstract PENDING retired with a macro sentence (registered ten-seed tests confirm the FLTrust effect
  under non-IID, Holm p <= \pfPrePThreePh; honest clients excluded about as often as attackers; "the counter changes
  what the rule decides, not whether it detects"). Trigger-audit sentence dropped from the abstract to make room
  (still in contributions, Sec. realizable, limitations); abstract 250 words (checker). Contribution 3 PENDING retired
  (cells so far, P1/P3 supported, no accuracy effect detected, natural root detects nothing). "Exploratory cells"
  PENDING line replaced by the cell count. Conclusion: FLAME "non-IID" qualifier; one sentence separating "what a rule
  decides" from "whether it defends". Main replay explanation shortened (details stay in supplement).
- **Hostile re-read of abstract/intro/contributions:** claims now limited to (a) exact geometry, (b) measured
  dominance of the counter, (c) registered, supported decision change for FLTrust (non-IID), (d) no accuracy effect
  detected, (e) FLTrust not a useful detector here with either root. No accuracy/BSR benefit is claimed; CIFAR
  closed-loop null stays in Limitations (abstract/intro do not mention CIFAR outcomes).
- **Build/check:** latexmk rc 0, 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.63, was 9.61) /
  supplement 6.** check_manuscript all PASS except the gate (40 unresolved, all P3 lane). Backups
  main.tex.pre-iter23.bak, supplement.tex.pre-iter23.bak. fltrust_falsify.json float noise reverted.
- **Running jobs:** none of mine. Not mine: P3 PIDs 5901, 15185, 52037 (+ gap-filler 7093).
- **Score after: 4/10, REJECT** (cleaner and honest, but the central measured outcome is a decision change in one
  rule that does not translate into defense benefit; most of the A/B table, incl. BSR, still pending).
- **Top 3 priorities:**
  1. Harvest P3 as P2/P4 (FLTrust IID s47-51) land; at n=10 for all eight hypotheses mark the family final
     (\pfPreFinal) and re-check the abstract's Holm bound comment (line ~59) and contribution 3 comment.
  2. When the A/B table fills, decide what the paper's outcome headline is: if no rule's CA/BSR separates, say so in
     abstract (the paper becomes "evaluations silently test a different rule"), and consider strengthening with the
     falsified-counter attack measured closed-loop (Cor. falsify) -- the one place the defect could be an attack surface.
  3. Main 9.63 pp, abstract at exactly 250 words: any addition must be paid for (aim <= 9.5).

## Iteration 24 - 2026-10-23 - R1 (trained counter-falsifying attacker) re-implemented from its pre-registration, unit-tested and launched (CPU pilot + waiter); P3 prereg runner relaunched on CPU; repo paths removed from the main text

- **State at start (02:10):** every runner had died in the 2026-10-22 14:50 reboot (P3 prereg log stops 12:37,
  run_p3.sh 13:03, reverse 12:36); two more reboots since. P3 **728/1040** cells after `make numbers` (P1 n=10
  holm 0.0039, P3 n=10 holm 0.0059 supported; P2/P4 n=5 holm 0.0625; S1-S3 complete, not supportable; S4 n=5).
  Missing prereg cells: IID FLAME (attacked full, both trainable), FLTrust and NormClip (all four) s47-51.
  **CUDA is in the zombie state** (`torch.ones(1,device='cuda')` -> "CUDA unknown error", nvidia-smi shows 10 MiB
  and no process): only the user can clear it (sudo; gpu_unwedge_watcher.sh). Everything below runs on CPU.
- **R1 state found:** PREREG_R1.md, experiments/r1_falsify/{run_r1.sh,wait_and_run.sh,choose_b.py} and
  configs/r1_*.yaml existed uncommitted, but the code they need (src/attacks/counter.py, engine flag, run_sweep
  flags, krum1, tests) did not exist anywhere on disk (lost with the earlier agent's uncommitted work). No R1 cell
  had ever run (results/r1_falsify absent).
- **Reviewer score before: 4/10, REJECT.** Ranked: (1) no security-relevant outcome that the counter changes
  (the measured effect is a decision change in FLTrust that buys no CA/BSR difference); (2) family interim (P2/P4
  n=5) and 32 pf PENDING in the A/B table; (3) repo paths and internal history in the prose (blind review R4);
  (4) no tests for the engine.
- **Fix 1 (R1 code, from the prereg spec, no R1 outcome seen):** src/attacks/counter.py (norm bound on the
  trainable block, never enlarging; counter policies honest/share(q)/median, integer >= 1);
  FederatedEngine._r1_attack (after variant/boost; bound measured on trainables in both arms; counter written
  relative to the integer counter the client loaded; per-round `history.counter_attack` record, only present when
  R1 is active, so P3 JSON schema unchanged); FLTrust logs `mal_step_share`, attackers' trust and honest median
  trust (logging only; made robust to fltrust_falsify.py's `__new__` construction, which my first version broke);
  `krum1` = single-winner Krum in the registry; run_sweep `--norm-bound --counter-policy --counter-share`
  (suffixes `_cp<pol>`, `_nb<b>`; old filenames unchanged). **tests/test_counter_attack.py: 6 tests pass**
  (share hits q, floor 1, median policy, identity/invalid, norm bound, and Cor. 2 in miniature: a full-vector
  single Krum selects an off-direction attacker that reports the honest-median counter and rejects it once the
  counter is masked). 2-round `--quick` plumbing runs (scratch dir) behave as specified. PREREG_R1 **Amendment 1**
  records the re-implementation, the CPU fallback and the plumbing check.
- **Fix 2 (R1 analysis):** paper/analyse_r1.py applies the registered tests mechanically (one-sided sign-flip,
  Holm within primary and mechanism families, FedAvg-reference informativeness gate, A-vs-B exploratory), writes
  paper/numbers_r1.tex (`\rOne...`, all PENDING now) and results/r1_falsify/summary.json; checked on a synthetic
  result set in the scratch dir; added to `make numbers`. Not yet \input by main.tex.
- **Fix 3 (R4 presentation):** every repo path/config key removed from main-text prose (SURVEY.md,
  flower_builtin_check.py, mal_selection key, PREREG_P3.md x3, analyse_postfix.py, copy_initial_global,
  p1_full.yaml, make_fig_p1.py); release sentence now mentions unit tests. Supplement keeps its paths (it is the
  reproducibility appendix). Backups main.tex.pre-iter24.bak, supplement.tex.pre-iter24.bak.
- **Build/check:** latexmk rc 0, 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.61, was 9.63) /
  supplement 6.** check_manuscript all PASS except the gate (36 unresolved, was 40; all P3 lane).
  fltrust_falsify.json float noise from `make numbers` left unstaged.
- **Jobs left running (all mine, CPU, under systemd-inhibit):**
  - P3 prereg runner: systemd-inhibit PID 179336 / runner 179337 (3 lanes x 2 threads), log
    results/postfix_p3/campaign_prereg.log; 11 jobs x 5 cells, ~45-50 min/cell on CPU -> **ETA ~14 h (~16:00
    2026-10-23)**. Then P2/P4 reach n=10 and the family is final.
  - R1 pilot: systemd-inhibit PID 181310 / runner 181311 (3 lanes x 2 threads), log results/r1_falsify/pilot.log
    (+ per-job log_r1pilot*.log); 7 cells, **ETA ~04:30**.
  - R1 campaign waiter PID 181451 (log results/r1_falsify/campaign.log): waits for 181311, applies choose_b.py,
    then runs the 160-cell campaign (run_r1.sh campaign) on CUDA (4 lanes) if CUDA works then, else CPU 3 lanes x
    2 threads (~40 h on CPU). If the GPU is restored while it runs on CPU: kill the run_r1.sh/xargs PIDs it
    started (not P3's) and relaunch `DEVICE=cuda LANES=4 bash experiments/r1_falsify/run_r1.sh campaign` under
    systemd-inhibit (resumable).
  - Not running: the exploratory P3 runners (run_p3.sh / run_p3_reverse.sh, 312 cells missing). Relaunch on GPU
    after R1 or when CUDA returns: `MAL_EPOCHS=15 DEVICE=cuda LANES=2 bash experiments/postfix/run_p3.sh`.
- **Score after: 4/10, REJECT** (infrastructure for the one experiment that can change the verdict now exists,
  is tested and is running; no outcome yet).
- **Top 3 priorities:**
  1. Harvest the R1 pilot (choose_b.py output -> b*, record in ledger; pilot outcomes are "seen", not evidence)
     and check the first campaign cells (`grep -c ERROR results/r1_falsify/log_*.log`, counter_attack records:
     share policy q_a ~0.5, median policy = honest median, trainable norm ratio <= b*).
  2. Harvest P3 prereg (P2/P4 n=10) -> mark the family final, re-check abstract/contribution 3 comments.
  3. When R1 cells land, \input numbers_r1.tex and plan one main-text paragraph + table (pay for it: main is at
     9.61 pp); report the outcome whatever its sign (a null BSR with a supported mechanism is reported as such).

## Iteration 25 - 2026-10-23 - R2 designed, pre-registered and plumbed (byzantineFL, ISBI 2024, authors' code); trigger audit dropped; GlueFL/Flower forum credited; reviewer questions answered; 8 engine unit tests

- **State at start (02:35):** CUDA still zombie ("CUDA unknown error"); everything on CPU. Running (iteration 24,
  not touched): P3 prereg runner 179336/179337 (FLAME IID s47-51 cells in progress), R1 pilot 181310/181311 (3
  cells running, none finished), R1 waiter 181451. Machine heavily loaded by other users' jobs (atlas.eval x3,
  ollama; load 30-36 on 20 cores). P3 729/1040 after `make numbers` (P1/P3 supported, P2/P4 n=5); R1 0 cells.
  `make numbers` died with make's "wait: No child processes" after make_fig_p1 (system quirk under load); the
  remaining generators were run by hand (generality, fltshut, analyse_r1, analyse_r2) and the PDFs rebuilt.
- **Reviewer score before: 4/10, REJECT** (blind review 1's ranking unchanged: no security-relevant outcome the
  counter changes; P3 incomplete; "does any published number move under the mask?" unanswered; notebook-style
  history; trigger audit off-topic; practitioner prior art uncredited).
- **R2 (main work).** Read both exposed pipelines. Chose **yjlee22/byzantineFL @ c6d8de3** first: it is the
  *official code of an ISBI 2024 paper* (Lee, Park, Kang, arXiv 2210.16519; venue verified on KAIST's page; our
  survey row and Sec. III-C had called it "a public re-implementation ... Fang's attack" -- wrong, corrected: Fang
  is an aggregation baseline there). Its Krum / trimmed-mean / Fang compare **whole ResNet-18 state_dicts (L=20)**
  with **quantity skew** (500-1000 samples/client, B_i ~125-250 local batches), i.e. Cor. 2's unequal-B case, and
  run on BloodMNIST (28x28), so the authors' full Fig.-3 grid is GPU-cheap. Note for R2's predictions: MPAF
  (untargeted) writes 10x(count - noise) into the attacker's counter. AlignIns (VGG-9/CIFAR-100) stays second
  target (GPU only, later amendment).
  - `iterations/PREREG_R2.md` written and **committed (6d34f8e, 03:00, sha256 7e21c421...) before any R2 outcome
    was read**: arms full / nonbt (counter removed from the decision vector only) / trainable (secondary); authors'
    run1.sh grid (krum, trimmed_mean, fang x c_frac 0.1-0.3 x target/untarget, quantity skew, defaults), seeds 3-12;
    outcome = the paper's plotted quantity, minimum test error over rounds; H1 = Krum 6 two-sided paired sign-flip
    tests, Holm; H2 = TM+Fang 12; mechanism M1 (counter share of pairwise distances > 0.5), M2 (counterfactual
    decision change), M3 (no Y difference for MPAF).
  - `experiments/r2_exposed/run_byzfl.py`: runs the authors' unmodified main.py via runpy; changes only data root,
    a tensorboard stub (broken protobuf on this machine; --tsboard never passed), logging, and in masked arms the
    single function (`multi_vectorization`) all three rules read through. Logs per round: test acc, counter and
    trainable share of pairwise squared distances, the Krum and trimmed-mean choice under all three arms on the
    same received models, which received models are compromised, batch counts. Resumable `run_r2.sh`
    (DEVICE/LANES/THREADS; 490 runs, krum first). `paper/analyse_r2.py` implements the registered tests
    (sign-flip + Holm checked on toy inputs) -> paper/numbers_r2.tex (\rTwo..., all PENDING), in `make numbers`.
    Third-party clones in experiments/r2_exposed/_ext (gitignored; commit hashes pinned); torchvision 0.21 matching
    torch 2.6 installed privately to experiments/r2_exposed/.pylib (the user-site torchvision is broken; not
    touched). BloodMNIST from the HF mirror (zenodo stalled at ~1 kB/s), MD5 = medmnist's 7053d035....
  - **Plumbing only (excluded by the prereg):** one round, Krum, target, c 0.3, seed 3, nonbt arm, `--local_ep 1`
    (not the registered 5): JSON complete, compromised positions and batch counts logged, logged choice = the arm's
    counterfactual choice. A round takes ~11 min on 2 CPU threads under the current load, so the campaign
    (tens of rounds per run x 490) **needs the GPU**; no campaign run was started.
- **R4 presentation.** Trigger-realizability audit dropped (blind review item 6): contribution bullet, related-work
  sentence, threat-model pointer and limitation numbers removed from main; supplement section reduced to "The
  trigger" (table + one paragraph, citing Pierazzi for problem-space realizability); the cut text is kept verbatim
  in paper/_dropped/realizability_audit_iter25.tex (it held one PENDING, now gone from the supplement). Prior art
  credited after verification: **GlueFL** (arXiv 2212.01523, App. D averages running_mean/var/num_batches_tracked
  deltas apart from masked weights -- read in the HTML full text) and the **Flower forum thread 533** (matt08,
  1 Jan 2025, aggregation fails on num_batches_tracked); both in refs.bib. Reviewer questions answered in the text:
  other frameworks (Keras/Flax BatchNorm keep running statistics but no counter), Bulyan (kept as a clamped variant
  because Flower ships it), root choice (balanced so every class reaches the reference; Sec. VI-C measures it),
  momentum=None (existing). Round-one aliasing paragraph shortened; it now cites the unit test.
- **Engine unit tests:** tests/test_engine.py, 8 tests (counter delta = epochs*ceil(n/bs) or the step budget;
  counter inert under default momentum, read under momentum=None; trainable mask = parameters exactly, 2C+1
  buffer coordinates; get_weights aliasing (round-one defect) and copy fix; set/get round trip; distance
  decomposition with the counter term (B_i-B_j)^2; Krum arms agree iff counters equal). `pytest -q tests/`: 14 pass.
- **Build/check:** latexmk rc 0 (both), 0 undefined refs. **IEEEtran pages: main 10 (ends at 9.61, unchanged) /
  supplement 6 (page 6 now ~80% by text-line count, was full; float placement limits what the audit's removal freed).** check_manuscript all PASS except the
  gate (36 unresolved, all P3 lane). Backups main.tex.pre-iter25.bak, supplement.tex.pre-iter25.bak.
- **Jobs left running (iteration 24's, untouched):** P3 prereg 179336/179337 (results/postfix_p3/campaign_prereg.log,
  ETA ~16:00 but probably later given the load); R1 pilot 181310/181311 (results/r1_falsify/pilot.log; first cells
  not finished at 03:45, ETA ~05:00+); R1 waiter 181451 (results/r1_falsify/campaign.log). Mine: none.
- **Score after: 4/10, REJECT** (no new outcome; R2 is now one GPU command away and registered, and the paper
  reads less like a notebook).
- **Top 3 priorities:**
  1. As soon as CUDA works: decide GPU order between R1's campaign (waiter launches it on CUDA automatically if CUDA
     is up when the pilot ends; otherwise it runs on CPU and should be moved, see iteration 24) and R2
     (`systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block env DEVICE=cuda LANES=4 bash
     experiments/r2_exposed/run_r2.sh`, ~490 short runs; Krum first so H1 completes early). R2 runs are small
     (ResNet-18 at 28x28, bs 20): they can probably share the card with R1 at 2 lanes each -- check memory.
  2. Harvest the R1 pilot (choose_b.py -> b*) and P3 prereg (P2/P4 n=10 -> family final).
  3. When R2 Krum cells land: `python3 paper/analyse_r2.py`, \input numbers_r2.tex, one main paragraph + a small
     table (main is at 9.61: pay for it), reported whatever the sign; then AlignIns as PREREG_R2 Amendment 1.

## Iteration 26 - 2026-10-23 - R1 pilot harvested (b* = 2 by the registered rule), R1 campaign moved onto the GPU, R2 queued behind it; P3 harvested: all four primary hypotheses supported (P4 interim n=8)

- **State at start (14:01):** CUDA zombie. R1 pilot complete (09:45, 0 ERROR lines); the waiter (181451) had applied
  choose_b.py at 09:54 and started the 160-cell campaign on CPU (3 lanes x 2 threads, run_r1.sh 527497, xargs
  527516): 6 cells done in 4 h (~2 h/cell on CPU -> ~107 h). P3 prereg runner (179336) on its last two jobs (IID
  FLTrust attacked full s51, trainable s50-51). Load 31 on 20 cores (other users' jobs).
- **Reviewer score before: 4/10, REJECT** (ranking unchanged: no security outcome the counter changes; R1/R2 have no
  outcome; P2/P4 interim).
- **R1 pilot / b\*.** choose_b.py output (campaign.log): FedAvg final BSR b=1 0.026/0.059 (mean 0.042), b=2
  0.867/0.062 (mean 0.465); neither >= 0.5, so **b\* = 2** and, as registered, the stealthy attacker "does not implant
  reliably even without a defense" and the BSR hypotheses are uninformative (to be reported, not reinterpreted). The
  waiter did start the campaign with b*=2. First cells checked: share policy q_a 0.46-0.52, trainable norm ratio
  2.000 (<= b*), honest policy writes the trained counter (435/60 vs honest 13); 0 ERROR lines. Recorded as
  **PREREG_R1 Amendment 2** (b*, outcomes seen: 6 FLTrust cells s42-43, device change; no test changed).
- **R1 onto the GPU.** CUDA came back ~14:20 (coordinator). Killing iteration 24's CPU runner was refused by the
  permission classifier (not my processes), so instead: `experiments/r1_falsify/run_r1_reverse.sh` (new) walks the
  same jobs_campaign.txt from the end, one cell per run_sweep call (identical arguments, single seed), skipping
  finished cells and the cell the CPU runner is on (lowest unfinished seed of a job whose log exists); lock dirs
  stop self-duplication; CUDA, 3 lanes x 1 thread. A CPU variant of it ran 14:04-14:20 and was stopped by me (one
  partial cell lost). On GPU: ~32 min/cell at 3 lanes, peak ~0.65 GB/lane (Ollama, not ours, holds 4.7 GB of the
  card); 3 cells done by 14:55, 0 ERROR lines.
- **R2 cannot share the card with R1.** Launched run_r2.sh at 1 lane next to the 3 R1 lanes: the first byzantineFL
  run did not finish round 1 in 10+ min (GPU 100%, the process spins in CUDA sync; a faulthandler dump of a 1-round
  debug run sits in the authors' local training loop), and its first try died at 15:05 with no traceback because
  run_r2.sh overwrote the log on retry. Stopped (my PIDs). run_r2.sh now appends per-run logs. **Queued**
  `experiments/r2_exposed/wait_r1_then_r2.sh` (PID 734442, log results/r2_exposed/waiter.log): waits for the R1 GPU
  helper to exit, checks CUDA, then runs run_r2.sh on CUDA with 3 lanes. Note: PREREG_R2 says "120 trainable runs
  (krum only)", but its own grid gives 3 c x 2 p x 10 seeds = 60, so the campaign is 430 runs (run_r2.sh), not 490:
  arithmetic slip in the prereg, no design change; record as an amendment when R2 runs.
- **P3 harvest (`make numbers`, 749/1040 cells):** P1 n=10 10/0, P2 n=10 10/0, P3 n=10 9/0, all p_H 0.0039;
  **P4 n=8 8/0 p_H 0.0039 (interim; its last two seeds are running)**; so 4/4 primary supported (2/2 blind).
  S1-S4 all n=10, none supported (closest S1 7/3, p 0.048, p_H 0.19). Confirmatory paragraph rewritten from macros:
  P1/P3 confirm Cor. fltrust; the IID pair is supported but is FLTrust's shutdown (zero trust for every client), not
  detection; RE-CHECK comment notes that P4 at 8+/2- with ties |d|=1 would give p 0.055.
- **Build/check:** latexmk rc 0, 0 undefined. **IEEEtran pages: main 10 (ends at 9.63) / supplement 6.**
  check_manuscript all PASS except the gate (36 unresolved, all P3 lane). pytest tests/: 14 pass. Backup
  main.tex.pre-iter26.bak.
- **Jobs left running:**
  - R1 CPU forward runner (iteration 24's, not stoppable by me): waiter 181451 / run_r1.sh 527497 / xargs 527516,
    log results/r1_falsify/campaign.log, 3 lanes x 2 threads. **Whoever can: stop it** (`kill 527497 527516 527517
    527518 527519 527520 527521 527522`; 181451 and 527496 then exit) once the GPU lane is healthy; the GPU helper
    then takes every remaining cell on its next pass (it is resumable; re-launch it if it has exited).
  - R1 GPU helper (mine): systemd-inhibit 710677 / bash 710678, log results/r1_falsify/gpu.log (+ rlog_*.log),
    3 CUDA lanes. ~151 cells left at ~6/h GPU + ~1.5/h CPU -> **ETA ~2026-10-24 12:00-15:00**. It makes one pass; cells
    the CPU runner held at scan time stay with the CPU runner.
  - R2 waiter (mine): PID 734442, results/r2_exposed/waiter.log -> results/r2_exposed/campaign.log. Run time per
    run alone on the GPU not yet measured.
  - P3 prereg runner 179336/179337 (iteration 24's): last cells, **ETA ~15:00 (full s51) and ~18:00 (trainable s51)**.
- **Score after: 4/10, REJECT** (all four FLTrust predictions hold, but the security outcome R1/R2 is still
  unmeasured).
- **Top 3 priorities:**
  1. `make numbers` after ~18:00: P4 n=10 -> family final (\pfPreFinal); re-check the confirmatory paragraph's
     RE-CHECK comment and the abstract.
  2. Check R1 GPU progress (`grep -c ERROR results/r1_falsify/rlog_*.log`; nvidia-smi); when the FLTrust family
     (A/B/C x 10 seeds) completes, run analyse_r1.py, \input numbers_r1.tex, and draft the R1 paragraph+table (main
     at 9.63 pp: pay for it). Report b*=2's uninformative-BSR consequence as registered.
  3. When R2 starts, time one run alone; if 430 runs do not fit, prioritise Krum (H1) as run_r2.sh already does.

## Iteration 27 - 2026-10-23 - What R1 can still show: PREREG_R1 Amendment 3 (pilot rule governs, mechanism family is the security outcome), PREREG_R2 Amendment 1 (430 runs), R1 macros in the paper, R2 profiled and re-ordered H1-first

- **State at start (15:20):** CUDA fine. R1: 9/160 cells (GPU helper 710677/710678, 3 lanes; CPU runner 527497/527516);
  0 ERROR lines in any R1 log. R2 waiter 734442 waiting. P3 prereg runner 179336 on its last cell (trainable s51).
- **Reviewer score before: 4/10, REJECT.** Blockers: (1) no security outcome the counter changes is measured (R1
  running, R2 queued); (2) at b*=2 the stealthy attacker does not implant even under FedAvg, so R1's BSR family
  cannot carry a backdoor claim; the reader must be told what R1 *can* show, before it shows it; (3) P4 interim;
  (4) scale.
- **What the security-relevant outcome is (argued in the amendment, before the outcomes):** a robust rule's guarantee
  is a bound on adversarial influence on the aggregate (Krum: selection close to honest; FLTrust: weight set by
  direction vs root). That bound is a property of the defense and is measured without a payload: R1's registered
  mechanism family (FLTrust attackers' trust-weighted trainable step share; Krum/Multi-Krum admission rate, defect >
  fixed). BSR needs a payload that implants undefended, which b*=2 does not. R2 carries the "published number"
  outcome (min test error with the authors' attacks), which does not depend on our attacker.
- **PREREG_R1 Amendment 3 and PREREG_R2 Amendment 1, committed first (8657211, 15:40; sha256 844b8e77... /
  5c1a31af...):** (i) the pilot rule's b*=2 branch makes the primary BSR family uninformative whatever the campaign
  FedAvg gate says (if they disagree the report says so); BSR tests still printed, never called supported/refuted;
  (ii) the mechanism family is R1's confirmatory security outcome, with pre-committed wording for both outcomes;
  (iii) exploratory made explicit: A-defect vs B-defect on the mechanism quantities, variant C defect vs fixed (BSR,
  CA, mechanism), share vs head count 2/10; no tests. R2: 60 trainable runs, 430 total (the 120/490 was an
  arithmetic slip; run_r2.sh always generated 430); plumbing run outcome disclosed. Outcomes seen before the
  amendment: iteration 26's numbers_r1.tex (FLTrust s42-43) and choose_b output; listed in the amendment.
- **analyse_r1.py:** `primary_uninformative_pilot` from choose_b output (\rOnePrimUninf, \rOnePilotBSRbOne/bTwo),
  exploratory AvB/AvBMech/C/CMech/CCa macros (means, sign counts, n; no p). **Looks after the amendment (logged as
  Amendment 3 item 4 requires):** FedAvg ref n=3 (s49-51) median BSR 0.027 (gate also says uninformative; the two
  criteria agree so far); exploratory AvBMech FLTrust n=2: falsified counter 0.339 vs honest counter 0.052 step share
  under the defect, while A-fixed is 0.330. **Warning for whoever writes R1 up:** if this holds, the registered FLTrust
  mechanism test (defect > fixed) may well not be supported, because the fixed rule already gives this attacker about
  that share; the hazard is that under the defect the attacker's share is set by a scalar it chooses (x6.5 between
  honest and falsified counter). That contrast is exploratory by registration and must be reported as such, not
  promoted. n=2: no conclusion.
- **Paper:** numbers_r1.tex now \input (preamble, Makefile deps). Supplement: new Sec. S-III-B "A trained falsifier
  (registered, running)" (design, pilot rule, b*, BSR family labelled from the macro, confirmatory outcome = influence,
  cells done; no outcome reported). Main Limitations "Threat model" item rewritten to say this (macros only);
  recommendations sentence shortened to pay for it. Backups main/supplement .pre-iter27.bak.
- **R2 feasibility:** cProfile of one round (CPU, 2 threads, local_ep 1, krum c0.1 target s3; scratch, not a campaign
  cell) 416 s: conv backward 260 s, forward ~95 s, test 28 s, harness diagnostics + Krum ~23 s. So the run is
  compute-bound in the authors' ResNet-18 training, not in our harness; at local_ep 5 the grid is GPU-only and may
  take days. run_r2.sh re-ordered (order only, logged in the script): H1 krum full/nonbt (120 runs) first, then krum
  trainable (60), then H2 and fedavg. The waiter launches the edited script.
- **P3:** still on its last cell (trainable s51) at 16:00; not harvested this iteration. P4 stays interim n=8.
- **Build/check:** latexmk rc 0, 0 undefined. **IEEEtran pages: main 10 (ends at 9.63) / supplement 6 (ends at 5.66).**
  check_manuscript all PASS except the gate (36 unresolved, P3 lane). pytest tests/: 14 pass.
- **Jobs left running (none started by me remain):** R1 GPU helper 710677/710678 (results/r1_falsify/gpu.log; cells
  started 14:54 still running at 15:55, slower than the 32 min/cell of iteration 26 -> ETA likely later than
  2026-10-24 15:00); R1 CPU runner 527497/527516 (campaign.log); R2 waiter 734442 (waiter.log); P3 runner 179336
  (ETA ~18:00); coordinator lock 178623. My profile run (737598) finished.
- **Score after: 4/10, REJECT** (the paper now says honestly what R1 can and cannot show; nothing new measured).
- **Top 3 priorities:**
  1. After ~18:00: `make numbers`; if P4 has n=10, mark the P3 family final (\pfPreFinal), re-check the confirmatory
     paragraph's RE-CHECK comment, the conclusion's \PENDING sentence and the abstract.
  2. R1: when the FLTrust A/B/C families reach 10 seeds, run analyse_r1.py and write the result with Amendment 3's
     pre-committed wording (mechanism test as registered; AvBMech as exploratory). Consider stopping the CPU runner
     only if the user authorises it.
  3. R2: when it starts, time one run from results/r2_exposed/log_*.log; if H1's 120 runs exceed ~2 days, say so
     and decide (by amendment, before outcomes) whether to cut seeds or rounds — do not do it silently.
