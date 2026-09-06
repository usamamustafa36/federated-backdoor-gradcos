# Paper 8, submission status

> **Venue: Elsevier JISA, not IEEE TIFS.** Retargeted 5 September 2026; see the
> update immediately below. Sections dated before then describe the TIFS plan.

**Direction Is Not Enough: Trigger Salience and Adaptive Collusion against Byzantine-Robust
Federated Intrusion Detection**
U. Mustafa, I. Rashid. CV entry 8, listed as *submitted*.

Everything below was checked by rebuilding inside this folder on 28 August 2026.

## Update, 5 September 2026 — retargeted to Elsevier JISA

**The venue changed.** This paper is no longer going to IEEE TIFS. The target is the
**Journal of Information Security and Applications** (Elsevier, ISSN 2214-2126 / 2214-2134),
submitted through Editorial Manager on the **subscription track** — the open-access route
carries a ~$2,860 APC and is to be declined. There are no page charges either way. The title
of this file and the CV line both still say TIFS; treat that as stale.

**The manuscript is now an Elsevier package.** `paper/main.tex` was converted from
`\documentclass[journal]{IEEEtran}` to `\documentclass[3p]{elsarticle}` — single column at
journal density, matching the group's Computers & Security submission. The pre-conversion
source is kept at `paper/main.tex.pre-jisa.bak`. What changed:

- elsarticle `frontmatter` block: `\author`/`\ead`/`\affiliation`/`\cortext`, `keyword`
  environment, `\journal{...}`. The old `\thanks` code-availability note became a proper
  *Data availability* declaration, which is where JISA wants it.
- **`\usepackage{cite}` removed.** elsarticle loads `natbib` itself and the two clash
  silently. This is the one conversion step that can renumber or drop citations without
  erroring; all 30 citations were verified to still resolve.
- The 30 `\bibitem` entries became `paper/refs.bib` with `elsarticle-num`. Keys are
  unchanged, so no `\cite` in the body moved. `et al.` was expanded to the full author list
  for FLAME, Wang et al. and Flower; Kairouz keeps `and others`.
- `tab:main` stopped needing a `table*` wide float: at nine columns it fits the single column
  comfortably. Verified visually.
- `\usepackage[T1]{fontenc}` + `lmodern`, so the build has no font-shape substitutions.

**New files in `paper/`:** `refs.bib`, `declarations.tex` (CRediT, competing interest, data
availability, funding), `highlights.tex` (5 bullets, all under Elsevier's 85-character cap),
`Makefile`, `README.txt` (submission-facing), `cover_letter.md` (draft, with suggested-reviewer
notes to confirm), and `tools/check_manuscript.py`. `paper/README.md` was rewritten — it still
described an "IEEEtran, conference mode" paper under the old title.

**A real defect found and fixed: the residual results existed but were never being read.**
`paper/aggregate_multiseed.py` globbed `results/*_s*.json` at the top level only, so the
completed five-seed residual campaign in `results/residual/` (20 files, tag `msresid`) was
invisible to the generator. The `res` macros were therefore `\PENDING` and `tab:residual` had
been filled in **by hand** — while the paper claimed in Sec. 5.5 that nothing is hand-entered.
The glob now walks live subdirectories and deliberately skips any beginning `_`, which are the
archived and superseded runs (`_flame_buggy_backup`, `_pre_trigger_redesign_backup`, the dated
reboot backups); pulling those in would have quietly averaged buggy cells into a reported mean.
Every generated value matched the hand-typed one exactly, including the standard deviations
(0.131 statistical, 0.170 temporal), so the table was right — it just was not generated. It is
now, along with the surrounding prose. `res` PENDING fell from 24 to 12.

**The gate is now counted from source, and it names the lane.** The old count was taken by
searching the PDF text, which undercounts: a `[PENDING RUN]` marker that wraps inside a narrow
table cell reaches `pdftotext` as two lines. `make check` now counts references in `main.tex`
to macros that `numbers.tex` leaves unresolved, plus literal `\PENDING` hedges, and groups the
total by the lane of `run_remediation.sh` that retires it. Each of the 13 literal hedges now
carries a `% RETIRES WITH:` annotation naming that lane. **True count: 46, not the 26 previously
reported.**

**Other fixes.** Three floats (`fig:drfpr`, `fig:tradeoff`, `tab:noniid`) were never
cross-referenced in the text — a copy-editor would return that; references added and a check
added so it cannot regress. Abstract trimmed 269 → 250 words for JISA's cap. British/American
spelling was mixed (`behaviour`, `organised`, `maximise`, `labelled`, `dialling`, `sceptical`,
`mean-centring` against 56 uses of `defense`); normalised to American throughout. Two em-dash
spacing typos fixed (`FoolsGold ---built`, `only--- see`). Figure widths in `make_figs.py` are
now derived from the 6.5 in single-column `\textwidth` and matched to the `\includegraphics`
fractions, so no figure is rescaled on the page.

A prose audit for AI-writing tells found none: zero AI-vocabulary words, zero filler phrases,
zero hedge stacking, zero copula avoidance. The 72 em-dashes are appositives doing real work,
not padding, and were left alone.

**Two-column check.** `[final,5p,times,twocolumn]` compiles at 12 pages, but `tab:main`,
`tab:adaptive` and `tab:magnitude` overflow the column by 158, 153 and 75 pt and would need
promoting to `table*`. Recorded in `paper/README.txt`. Single column stays the default.

### Open risk found while the campaign ran: the abstract's headline number

The abstract and the introduction both state that the evasion collapses the colluders' mean
pairwise similarity "from 0.99 to **below 0.35**". That figure comes from the reduced-scale
validation run (6 clients, 3 rounds, 8k rows). Sec. 7.4 says so and marks the paragraph
`\PENDING`; the abstract and the introduction state it flat, with no hedge, and they are not
macros, so the generator could not catch them.

The first full-scale cell disagrees. `rem_..._fedavg_..._vdecorrelated_e1.0` gives a malicious
pairwise cosine of **0.428** against an honest cohort at 0.999 — the mechanism works, but the
number is above the claimed bound. One cell, and the undefended baseline at that, so this is not
yet a refutation. It is a warning that the headline figure may not survive full scale.

`tools/check_manuscript.py` now compares the claim against every `adMalCos*Decorrelated` and
`adMalCos*Adaptive` macro as lane 1a lands, and fails loudly while the worst measured value
exceeds the stated bound. It currently fails at 0.428. Both literal sites in `main.tex` carry a
`% FULL-SCALE CHECK` comment.

**When lane 1a completes, the abstract sentence must be rewritten against the measured range**
— not left as a literal. The honest options are to quote the real range, to restrict the claim
to the defended runs if that is where it holds, or to state the worst case.

### Current state



| Check | Result |
|---|---|
| `latexmk -pdf main.tex` | exit 0, 17 pages |
| Undefined citations / references / control sequences | 0 / 0 / 0 |
| Font-shape substitutions | 0 |
| Overfull hboxes | 1, caused by `\PENDING` filling `tab:adaptive`; self-resolves |
| Abstract | 250 words (JISA cap: 250) |
| Highlights | 5 bullets, longest 84 of 85 chars |
| References | 30, all cited, `elsarticle-num` |
| Orphaned floats | 0 |
| **Submission gate** | **FAILS — 46 unresolved results** |

### What is still blocking

The gate, and nothing else. The campaign was relaunched 5 September 00:32 under
`systemd-inhibit` on mains and is running lane 1a. Lane 1a (16 markers) and lane 3 (17) clear
33 of the 46 between them.

Everything else on the pre-submission list is a decision, not work: push the code (the public
repo still predates the remediation pass, and `declarations.tex` now points at it), confirm the
CRediT split, decline open access in Editorial Manager, and upload the competing-interest
declaration as a .docx. All four are listed in `paper/README.txt`.

## Update, 3 September 2026

Two of the four non-compute blockers are closed. The manuscript still cannot be submitted, and
the reason is still the same one: the experiments.

**Numbers are now generated, not transcribed (issue 6, closed).** `paper/make_numbers.py` reads
`results/summary_multiseed.csv` and `results/summary.csv` and writes `paper/numbers.tex`, which
`main.tex` inputs. Every table and every quoted figure in the prose is now a macro. A cell that has
not been run expands to `\PENDING` instead of a number, and `make_numbers.py --strict` exits 1 while
any macro is unresolved -- that is the submission gate. Currently 329 of 677 macros resolve; the
348 that do not map exactly onto the unrun lanes.

Building it surfaced three real defects, all fixed:

- `results/summary.csv` mixed the single-seed breadth grid with the multi-seed campaign's seed-42
  replicate of the same configuration, so any grid mean silently averaged the replicate in as an
  extra cell. `summarize_history` now records `seed`, and `load_results` records `run_tag` and
  `source_file`; the generator deduplicates on the configuration key, preferring the grid run. Grid
  means are now over exactly 9 cells per trigger, as the paper claims. This changed the fixed-trigger
  grid means: GradCos 0.154 (was reported 0.154 in PROGRESS.md, so that one was right), Krum 0.559
  (PROGRESS.md says 0.595), FedAvg 0.958 (says 0.945). **PROGRESS.md's fixed-trigger column is a
  stale July snapshot; the generated numbers supersede it.**
- `experiments/make_tables.py` crashed on `results/realizability_ciciot2023.json`, which is a JSON
  list rather than a run payload. It skipped non-dict payloads nowhere; it does now.
- The paper claimed "every reported number is machine-generated ... nothing is hand-entered". That
  was not true when written. It is true now, and the sentence names the generator so a reviewer can
  check it.

Every generated number was checked against the hand-typed one it replaced. They agree, apart from
the grid means above and a few 0.01 rounding drifts in the ratio sweep -- which is exactly the class
of error the generator exists to stop.

**Bibliography: 21 -> 30 (issue 5, closed).** All four candidates from `REFS_TO_ADD.md` are in, plus
five more that close the 2024-25 and FL-IDS gaps. Every entry below was verified against a publisher
or arXiv page on 3 September 2026:

| Key | What it closes |
|---|---|
| `li20233dfed` | 3DFed, IEEE S&P 2023 -- the closest prior work to our evasion lane |
| `yang2024learning` | Yang et al., CIKM 2024 -- learning-based attack against SOTA poisoning defenses |
| `fang2025foundation` | Fang et al., NDSS 2025 -- "do we really need new Byzantine-robust rules?" |
| `zhang2022neurotoxin` | Neurotoxin, ICML 2022 -- backdoor durability, cited at the suppression gap |
| `zhang2022fldetector` | FLDetector, KDD 2022 -- a defense outside our two-family taxonomy |
| `xie2021crfl` | CRFL, ICML 2021 -- closes off "why not certify?" |
| `zhang2022secfednids` | SecFedNIDS, FGCS 2022 -- poisoning defense for FL-NIDS specifically |
| `merzouk2023param` | Merzouk et al., ARES 2023 -- poisoning attacks on FL-IDS |
| `sameera2025weidetect` | WeiDetect, 2025 -- FL-NIDS poisoning defense |

Related Work gained a paragraph separating our evasion from 3DFed and Yang et al. (ours is weaker
and cheaper, which makes the defenses failing against it a stronger result), a positioning sentence
against Fang et al., and three sentences on FL-IDS poisoning noting that none of that work reports
the false-positive cost of its exclusions. The scope block gained a taxonomy caveat citing
FLDetector and a certification paragraph citing CRFL.

**`\PENDING` markers in the built PDF: 41 -> 26.** The build is clean at 11 pages, 0 undefined
references, 0 undefined control sequences.

**Figures self-upgrade (no manual step left).** Two figures were placeholders showing the wrong
plot. `paper/make_figs.py` already had `fig_dose()` and `fig_evasion()`, but `fig_dose` selected the
whole breadth grid, which varies malicious ratio and poison rate as well as magnitude -- putting back
the exact confound the magnitude sweep exists to remove. It now pins the headline operating point and
seed, plots one curve per (defense, trigger) so magnitude is swept *within* a family, and refuses to
draw with fewer than three magnitudes on disk. `fig_evasion` likewise pins the operating point and
seed so the multi-seed replicates cannot leak in.

In `main.tex` both figures are now wrapped in `\IfFileExists`: the moment the generator writes
`figs/fig_dose.pdf` or `figs/fig_evasion.pdf`, the figure and its caption switch from placeholder to
final. Verified in both directions -- with both files present the PDF drops from 26 `\PENDING` to 24
and the real captions appear. There is no manual swap left to forget.

### Root cause of the recurring "zombie CUDA state": suspend, not ollama

Worth stating first, because the wrong diagnosis has now cost three runs and about a week of GPU
time. `README.md`, `PROGRESS.md` and `REMEDIATION.md` all attributed it to `ollama` holding
`nvidia_uvm`. That is wrong, and the 3 September run disproves it: `ollama` was stopped for the
whole run and it failed anyway.

What actually happens, from `journalctl` and `dmesg` on 4 September:

- 3 Sep 23:24:11 -- GPU healed, lane 1a starts.
- 3 Sep 23:26:31 -- `systemd-logind: Suspending...`, then `PM: suspend entry (s2idle)`. Two minutes
  into the cell. The box is a laptop and it was **on battery**.
- 4 Sep 07:25:05 -- resume. `dmesg` shows `NVRM: Xid (PCI:0000:01:00): 31 ... MMU Fault ...
  FAULT_PDE ACCESS_TYPE_VIRT_READ`, naming `pid=185731, name=python3` -- our own sweep.
- 4 Sep 07:25:36 -- the sweep dies with `unspecified launch failure` and the pipeline reports the
  familiar "zombie CUDA state".

Suspending powers the GPU down under a live CUDA context, which invalidates it. Reloading
`nvidia_uvm` fixes it because the reload rebuilds UVM state after the resume -- so stopping `ollama`
in the same command looked causal and was not. The 28 August failure has the same shape, and the
stall watchdog never fired because the whole machine was asleep, so its clock was frozen too.

Three things changed as a result:

- `run_remediation.sh` gained `wait_for_ac()`, called before every lane. It refuses to start a
  multi-hour lane while on battery rather than starting one that cannot finish.
- The documented launch recipe now wraps the pipeline in
  `systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block`, so the machine cannot suspend
  mid-cell. The campaign now running holds that inhibitor.
- `README.md` and `PROGRESS.md` are corrected. Recovery after a suspend still needs the module
  reload; the prevention is mains power plus the inhibitor.

**The GPU was healed and the campaign relaunched on 4 September at 15:55, on mains and under the
inhibitor.** The earlier 3 September start is described below and died to the suspend above. `ollama` was stopped and
`nvidia_uvm` reloaded; `cuda_healthy()` returns True. Lane 1a (adaptive vs direction-based rules, 24
cells) started at 23:24 and the GPU is at 96% utilisation. If the zombie state recurs -- it has twice
-- the heal is:

    sudo systemctl stop ollama && sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm

Note `ollama` is what holds `nvidia_uvm`; leave it stopped for the duration of the campaign.

At ~33 min/cell, lane 1a finishes in ~13 h and lanes 1a+1b+1c+3 (63 cells, ~36 h) are the point at
which every claim the abstract makes has evidence behind it. Those lanes resolve the `ad`, `ev`,
`res` and `mg` macro families, so Tables `tab:adaptive` and `tab:magnitude` and Fig. `fig:evasion`
fill themselves. Full 287 cells is about a week.

## Short answer

This one cannot go to TIFS yet, and the gap is large. The manuscript carries 41 `\PENDING` markers
on 25 lines, 22 of them in the Results section. One results table is entirely empty, two figures are
placeholders showing the wrong plot, and the whole adaptive-collusion result, which the abstract
leads with and which the CV describes as the paper's stronger finding, has no experiment behind it
yet.

The CV says "submitted". Nothing on this machine shows a submission, and the paper itself carries a
guard at line 20 saying nothing with a `\PENDING` may go to a venue. Treat the CV line as the plan,
not the record.

## What was verified today

| Check | Result |
|---|---|
| `pdflatex` build | works, exit 0 |
| Page count | 11 pages |
| Overfull hboxes | 2, both caused by `\PENDING` filling table cells and self-resolving |
| `\PENDING` markers | 41 occurrences on 25 lines, 22 lines in Results |
| Document class | `\documentclass[journal]{IEEEtran}`, fixed 28 Aug |
| Author block | fixed 28 Aug, was `Anonymous Author(s)` |
| Abstract length | 268 words, was 347 |
| References | 21, four verified candidates in `REFS_TO_ADD.md` |
| Code availability statement | added 28 Aug |
| Experiment cells needed by `run_remediation.sh` | 287 |
| Experiment cells done | 0 |

## What is missing, in the order it will sink the paper

### 1. The experiments, all 287 cells of them

`run_remediation.sh` was launched on 27 August at 15:33, waited 96 minutes for the GPU, started lane
1a at 22:15 and then died. The log had five lines and stopped mid-lane, with no result file carrying
a `rem` tag.

**It was restarted on 28 August at 14:21 and is running now.** Counting the sweep enumeration in
`experiments/run_sweep.py` against what was on disk at that point:

| Lane | Answers | Cells done |
|---|---|---|
| 1a adaptive vs direction-based rules | the headline evasion result | 0 / 24 |
| 1b evasion noise sweep | how much noise the attacker needs | 0 / 12 |
| 1c adaptive vs the residual variant | does our own fix survive | 0 / 7 |
| 2 trigger magnitude sweep | turns salience into a dose response | 0 / 44 |
| 3 non-cosine defences | the control the blind-spot claim needs | 0 / 20 |
| 4 donor triggers | realizable triggers | 0 / 20 |
| 5a, 5b, 5c seeds | the single-seed claims | 0 / 112 |
| 6 non-IID breadth, alpha 0.1 and 1.0 | heterogeneity | 0 / 48 |
| **Total** | | **0 / 287** |

At the roughly 25 to 30 minutes per cell the earlier multi-seed campaign averaged on this GPU, that
is about 120 GPU-hours. The first cell of the restarted run took 33.5 minutes, so treat 120 as the
optimistic end and budget closer to 160 hours, or about a week. That is one measurement and the
first cell carries the dataset load, so the estimate is worth revisiting once a lane finishes. The script is resumable, so it can be
done in chunks, and the lanes are already ordered so an interrupted run leaves the most important
evidence on disk.

If five days is not available, the honest reductions are to cut `--rounds` from 100, to drop lane 6,
or to drop the seed lanes and label those claims single-seed. Cutting lanes 1 and 3 is not an option
because the abstract already promises both.

### 2. Anonymised, wrong document class, over-long abstract. **All three fixed 28 August**

The author block read `Anonymous Author(s)`, the class was `\documentclass[conference]{IEEEtran}`
and the abstract ran to 347 words. All three are done:

- journal class, with `\IEEEoverridecommandlockouts` dropped since it is a conference-class override
- real author block for U. Mustafa and I. Rashid, NUST affiliation and both e-mails, in the journal
  `\thanks` style copied from paper 7
- a second `\thanks` carrying the code availability statement, which the paper had never had
- abstract down to 268 words, keeping all four numbered findings
- the hard `\\` line break in the title removed, since it was placed for the conference layout and
  left "Adaptive" stranded on its own line in the journal one

It still builds clean at 11 pages with 0 undefined references. The pre-change file is at
`paper/main.tex.pre-journal.bak`. The `\PENDING` guard was deliberately left in place.

### 3. The public repo is real but three days stale

Correcting an earlier reading of this. The repo does exist and is public at
`github.com/usamamustafa36/federated-backdoor-gradcos`, 554 files, last pushed 25 August. What it
does not have is the remediation pass. Checked against the published tree, all of
`src/attacks/evasion.py`, `src/attacks/realizability.py`, `src/defenses/robust_stats.py`,
`scripts/calibrate_defenses.py`, `run_remediation.sh` and `REMEDIATION.md` are missing from it.

So the code availability statement now in the paper points at a repo that does not contain the
adaptive attacker the paper is largely about. That has to be pushed before submission, and the local
copy has no remote configured, so it needs adding. Pushing is publishing, so it is left for you to
trigger.

### 4. A wrong citation on one of the two datasets. **Fixed 28 August**

The bibliography credited FLNET2023 to M. Sarhan, S. Layeghy and M. Portmann. That is the
University of Queensland group behind the NetFlow-based NIDS datasets, and they did not make this
one. FLNET2023 is by P. Kumar, J. Liu, A. S. M. Tayeen, S. Misra, H. Cao, J. Harikumar and
O. Perez, published at MILCOM 2023, and it comes out of Misra's lab at New Mexico State.

The giveaway was already in the repository. `scripts/fetch_flnet2023.py` pulls the data from
`github.com/nsol-nmsu/FML-Network`, which is the NMSU group, while its own docstring credited
Sarhan. The data source was right and only the attribution was wrong, so nothing about the
experiments is affected.

This matters more than a normal citation slip, because FLNET2023 carries roughly half the
experiments and a reviewer who works on it would spot the misattribution immediately. Both the
`\bibitem` and the loader docstring are corrected.

The other twenty entries were reviewed at the same time and look right: correct authors, venues and
years for McMahan, Bagdasaryan, DBA, Krum, Yin, Bulyan, RFA, FLTrust, FLAME, DeepSight, FoolsGold,
Shejwalkar, Fang, Baruch, Pierazzi, Sun, Wang, CICIoT2023, Flower and Kairouz. Only the FLNET2023
entry was checked against its publisher page, so the rest rest on inspection rather than a lookup.

### 5. Twenty-one references

Thin for a TIFS regular paper, and the specific hole is the adaptive-attacker literature the paper
is now positioned against. Four candidates were checked against their publisher pages and written up
with ready-to-paste `\bibitem` entries and a suggested citation site for each, in
`REFS_TO_ADD.md`. The important one is 3DFed (IEEE S&P 2023), which already evades DeepSight,
FoolsGold, FLAME and FLDetector, so it overlaps heavily with our defence set.

### 6. Numbers are typed into the LaTeX by hand

There is no generated numbers file. Every figure in the prose was transcribed. With 41 blanks about
to be filled in from fresh runs, this is where a wrong number gets in. Paper 7 solves this with
`make_numbers.py` writing macros from the result JSONs, and the same approach would work here from
`results/summary_multiseed.csv`.

## What is genuinely done

Worth saying, because the remaining work is all compute and none of it is design. From the 13-issue
hostile review in `REMEDIATION.md`, seven issues are closed in full, including the realizability
audit (issue 4), the FPR reporting that changes three readings of the results (issue 10), the
GradCos bimodality concession (issue 11), the temporal detection gap (issue 12) and the scope block
(issue 13). The code for every queued lane is written and validated end to end on the quick path.
The adaptive attacker is verified on the quick path already, dropping colluder pairwise cosine from
0.994 to 0.24 while the honest cohort stays at 0.993.

One loose end that is not compute. `scripts/calibrate_defenses.py` was running on CPU and did not
finish, so `results/calibration.json` does not exist and the hyperparameters in the paper are still
the pre-declared defaults. The log stops inside the FLAME noise grid.

## The run that is going now

The GPU was cleared on 28 August and the pipeline restarted at 14:21, working through lane 1a. To
watch it or restart it:

    cd paper08-tifs-direction-is-not-enough
    tail -f results/remediation.log
    setsid nohup env DEVICE=cuda bash run_remediation.sh >/dev/null 2>&1 & disown

It is resumable, so a restart picks up from whichever cells are already on disk. It polls for the
GPU on its own, waits up to 12 hours and retries a lane up to 8 times, so it survives another zombie
episode without supervision. The 27 August log was kept as `results/remediation.log.aug27.bak`.

Before the restart, the GPU path was smoke tested on the adaptive attack with `--quick`, which
confirmed the evasion runs and the geometry logging records `mal_norm_ratio` and the honest cohort
cosine. In quick mode `mal_pair_cos` comes out nan, because 6 clients at a 0.2 malicious ratio is a
single malicious client with no pairs to average over. At the real scale of 20 clients there are
four, so this does not appear in the actual runs.

**One thing that had to be fixed first.** The original copy into this folder excluded every directory
named `data`, which was meant to skip the 3.6 GB dataset directory but also dropped `src/data`. The
first restart died on `ModuleNotFoundError: No module named 'src.data'`. `src/data` has been restored
and the file list now matches `tasmania/fl-paper` exactly, apart from the runtime heartbeat file the
sweep recreates itself.

## A note on the data symlink

`data/` is a symlink to `../tasmania/fl-paper/data`, which holds 3.6 GB of CICIoT2023 and FLNET2023.
Copying it would have duplicated that for no benefit. If you ever move or delete the `tasmania`
copy, replace the symlink with the real directory first.

## Where this came from

Copied on 28 August 2026 from `tasmania/fl-paper`, which is the live working copy and the newer of
the two. The snapshot at `tasmania/papers/02-trigger-salience-backdoor-fl` is from the same
afternoon but already stale. The originals are untouched.
