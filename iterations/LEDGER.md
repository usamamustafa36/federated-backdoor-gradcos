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
