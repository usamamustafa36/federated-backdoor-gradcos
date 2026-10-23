# Pre-registration R1: a trained counter-falsifying attacker (Corollary 4 made real)

Written 2026-10-22, 12:20-13:10 PKT, by iteration 24 (started by one agent, finished
by a second one after the first ran out of room), before any R1 pilot or confirmatory
cell existed.
Committed together with the code that runs it (src/attacks/counter.py, the engine flag,
tests/test_counter_attack.py, experiments/r1_falsify/). Not to be edited after that
commit except by dated amendments appended at the bottom, each saying what changed and
which R1 outcomes the author had seen. The pilot (below) uses seeds 7 and 8 only, which
are not in the confirmatory set; its outcomes are reported as seen.

## Threat model

Static federated backdoor, as in P3 (CICIoT2023, CNN+LSTM with BatchNorm, 10 clients,
all participating, 15 rounds, malicious ratio 0.2 with share-matched selection, fixed
trigger, poison rate 0.1, E_m = 15 malicious local epochs, round-1 aliasing fix on).
Each malicious client additionally controls two things nobody checks:

1. **Norm bound (stealth).** It rescales the trainable block of its update to at most
   b times the median honest trainable norm of the round (`attack.norm_bound = b`;
   direction kept; BatchNorm buffers as trained). Knowledge: the median honest norm
   (the usual assumption of norm-matching attacks). b is fixed by the pilot rule
   below, before any confirmatory cell runs. This answers the review's point that the
   unbounded E_m = 15 attacker (15-19x the honest norm) is caught by its norm.
2. **The counter.** It reports a `num_batches_tracked` value of its choice
   (`attack.counter_policy`, src/attacks/counter.py; integer, at least 1):
   - against FLTrust, `share` with q = 1/2: the counter carries half the squared
     norm of its own update. Corollary 4: this maximises the attacker's non-counter
     step at rho = 0 whatever the server's share. Knowledge: none beyond its own update.
   - against Multi-Krum and Krum, `median`: the median honest counter increment of the
     round (knowledge of the honest counters only, a scalar per BatchNorm layer;
     full-knowledge setting of Fang et al.).
   Under the default momentum the counter is inert, so the falsified value has no
   effect on the model the attacker helps train.

The server runs the rule unchanged. **Defect arm**: decisions on the full state_dict
(`signal_subspace: full`). **Fixed arm**: decisions on the trainable parameters. The
attacker is identical in the two arms (the norm bound is measured on trainables in
both), so the arm is the only difference. Seeds are paired (same partition, same
attackers, same initialisation).

Rules: FLTrust (balanced root, as in P3), Multi-Krum (`krum`, keeps n - f = 8, f = 2),
Krum (`krum1`, single winner, f = 2). Bulyan is excluded: with n = 10 it needs
n >= 4f + 3, so f is clamped to 1 while two clients are malicious, and a result on it
would test the clamp, not the rule.


Partition: Dirichlet (alpha = 0.5) only, the partition in which P3's fixed-arm FLTrust
excludes anyone at all and in which batch counts differ between honest clients (so the
distance rules read the counter under the defect, Cor. 2). IID is not part of R1.

## Predictions (from the paper's theory) and why

- **FLTrust (Cor. 3, 4).** Under the defect, the attacker's trust score is at least
  sqrt(q_a q_0) - sqrt((1-q_a)(1-q_0)), which is > 0 whatever its trainable direction
  when q_a + q_0 > 1 (q_a = 1/2, q_0 about 0.7), so it is never excluded, and after
  FLTrust's rescaling to ||g_0|| on the full vector its trainable step is
  sqrt(1 - q_a) ||g_0|| = ||g_0||/sqrt(2) at q_a = 1/2, whereas an honest client whose
  counter carries q_h (about 0.7-0.98 in P3) gets only sqrt(1 - q_h) ||g_0||. Under the
  fix, the attacker gets weight max(0, cos) of its trainable update with the root update
  and the same rescaled norm as everyone else. Predicted sign: the attackers' share of
  the trainable aggregate is larger in the defect arm, and so is BSR. (P3 already shows
  that the *honest-counter* E_m = 15 attacker is never excluded under the defect either:
  its counter, 15x an honest one, gives it q_a near 1, so its trainable step is shrunk
  instead. The falsified counter is what turns non-exclusion into weight.)
- **Multi-Krum and Krum (Cor. 2).** Under the defect and Dirichlet shards, distances
  are dominated by differences in batch counts. An attacker that reports the honest
  median counter sits in the middle of the honest counters and so gets a small Krum
  score, whatever its trainable update; under the fix the counter is invisible and the
  attacker is kept only if its (norm-bounded) trainable update is close to the honest
  ones. Predicted sign: the attackers are admitted (Multi-Krum) or win (Krum) more often
  in the defect arm, and BSR is higher there. The honest-counter attacker reports 15x
  the honest count and is excluded in both arms (P3: DR 1.000 in both arms, s42-46);
  that is control (B) below.
- **No prediction** for clean accuracy, for the unbounded variant's BSR under FLTrust
  (its trainable update is already large; rescaling caps it in both arms), or for the
  size of any effect.

## Cells

Engine and data as P3 (configs/p3_full.yaml = defect arm, configs/p3_trainable.yaml =
fixed arm; 15 rounds; --mal-local-epochs 15; trigger fixed; m = 0.2; p = 0.1),
out_dir results/r1_falsify, seeds 42-51 (paired across arms and variants).
Per rule, with policy P = share(0.5) for FLTrust and median for krum/krum1:

| variant | norm bound | counter | arms | seeds |
|---|---|---|---|---|
| A stealthy falsifier (primary) | b* | P | defect, fixed | 42-51 |
| B honest-counter control | b* | honest | defect | 42-51 |
| C unbounded falsifier | none | P | defect, fixed | 42-51 |

plus a FedAvg reference (fixed arm, b*, honest counter, seeds 42-51) that measures the
BSR the bounded attacker reaches with no defense. 3 rules x 50 + 10 = 160 cells. In the
fixed arm the counter is invisible to the rule, so A-fixed doubles as B-fixed.

## Choice of the norm bound b* (fixed before any confirmatory cell runs)

Pilot: FedAvg, Dirichlet, fixed arm, honest counter, seeds 7 and 8, b in {1, 2}
(plus a timing/sanity pass of variant A at b = 1 on seed 7 for FLTrust both arms and
krum1 defect arm, whose outcomes are seen and are not evidence). **Rule:** b* = the
smallest b in {1, 2} whose mean final-round FedAvg BSR over seeds 7 and 8 is >= 0.5; if
neither reaches 0.5, b* = 2 and the report says the stealthy attacker does not implant
reliably even without a defense, which makes every BSR hypothesis below uninformative
(reported, not reinterpreted). The rule is applied mechanically by
experiments/r1_falsify/choose_b.py when the GPU campaign starts; its output is logged.

## Outcomes and tests

Per cell: final-round BSR (round 15) and CA; per round: attacker exclusion (DR), FPR,
and for FLTrust `attack_diag.mal_step_share` (attackers' share of the trust-weighted
trainable step mass) and the counter actually reported (`counter_attack`).
Admission rate = 1 - mean over rounds of DR.

Test: the exact ONE-sided paired sign-flip permutation test of the mean seed-paired
difference (defect minus fixed) in the predicted direction, all 2^10 sign patterns
(as `signflip_p_one` in paper/analyse_postfix.py), Holm within each family,
alpha = 0.05. n = 10 pairs; a pair with a missing or errored cell is dropped and the
report gives n.

- **Primary family (3 tests), variant A:** final BSR, defect > fixed, for FLTrust,
  Multi-Krum, Krum.
- **Mechanism family (3 tests), variant A:** FLTrust: mean mal_step_share defect >
  fixed; Multi-Krum and Krum: admission rate defect > fixed.
- **Exploratory (no test claims):** variant A-defect vs B-defect (does the falsified
  counter itself matter), variant C, CA, FPR, the FedAvg reference.

A hypothesis is "supported" only if its Holm-adjusted p < 0.05. If the FedAvg reference
BSR (campaign seeds) has median < 0.2, the primary family is reported as uninformative
whatever its p-values. A supported mechanism with an unsupported BSR is reported as
exactly that: the counter buys admission or weight but not a backdoor here.

## What was visible when this was written (non-blind)

- All P3 result files on disk (results/postfix_p3); in particular the Dirichlet attacked
  FedAvg (fixed arm, s43-46: BSR 0.73-0.99), FLTrust (s42-51 defect arm: DR 0, BSR
  0.00-0.11) and Krum (s42-46 both arms: DR 1.000, BSR <= 0.03) summaries were read by
  the second iteration-24 agent while writing the cells table. Calibration
  (results/calib_iter6): FedAvg Dirichlet E_m = 15, BSR 0.12-0.98 over s42-51.
- One 3-round smoke run per rule (FLTrust, Multi-Krum; seed 7; share policy; b = 1;
  dev copy, not under results/), CA 0.23, BSR 0: a plumbing check only.
- A 2-round byte-identity check (seed 42, 6,000 rows, R1 flags off) that compares the
  pre- and post-merge code; it contains no R1 cell.
No R1 cell (seeds 42-51, 15 rounds) had been run.

## Amendment 1 (2026-10-23 02:30 PKT, iteration 24, third agent). No R1 outcome seen.

- **Code re-implemented from this document.** The implementation the header refers to
  (src/attacks/counter.py, the engine flag, tests/test_counter_attack.py) was never
  committed and did not survive the 2026-10-22 reboots; only experiments/r1_falsify/ and
  configs/r1_*.yaml did. It was re-written from the specification above, without any R1
  cell on disk: src/attacks/counter.py (norm bound, `share`/`median`/`honest` counter
  policies), FederatedEngine._r1_attack (applied after the variant/boost transforms; norm
  bound on the trainable block in both arms, then the counter, written relative to the
  integer counter the client loaded), `krum1` (single-winner Krum) in the defense
  registry, FLTrust logging of `mal_step_share` (never feeds a decision), run_sweep
  flags `--norm-bound --counter-policy --counter-share` (filename suffixes `_cp<policy>`,
  `_nb<b>`), unit tests in tests/test_counter_attack.py (6 pass). With both flags off
  the code path is skipped, so P3 cells are unchanged. The per-round record is
  `history.counter_attack` (the outcome named `counter_attack` above) and contains
  `mal_step_share` for FLTrust (the outcome named `attack_diag.mal_step_share` above).
- **Device.** CUDA is in the zombie state ("unknown error") at 02:12; the pilot runs on
  CPU (3 lanes x 2 threads, seeds 7-8, launched 02:20) and the waiter
  (experiments/r1_falsify/wait_and_run.sh) runs the campaign on CPU (3 lanes x 2 threads,
  next to the P3 prereg runner) unless CUDA works when it starts. Device does not change
  any test.
- Plumbing check seen: 2-round `--quick` cells (seed 7, 6 clients, scratch directory, not
  under results/) for FLTrust/share and Krum1/share/median, b = 1: the counter and norm
  records are as specified (attacker trainable norm = 1.000 x honest median; share
  policy counter share 0.45-0.52). Not evidence.

## Amendment 2 (2026-10-23, iteration 26): b* and the device change. No test changes.

- **b\* = 2, by the registered rule, applied mechanically by choose_b.py at 09:54**
  (results/r1_falsify/campaign.log): FedAvg pilot final BSR b = 1: 0.026 / 0.059 (mean
  0.042); b = 2: 0.867 / 0.062 (mean 0.465). Neither reaches 0.5, so b\* = 2 and, as
  registered, the report must say that the stealthy attacker does not implant reliably
  even without a defense and that the BSR hypotheses are uninformative (reported, not
  reinterpreted). The FedAvg reference cells (seeds 42-51) still run and the analysis
  script's informativeness gate is applied to them as registered.
- Pilot outcomes seen (not evidence): the five pilot cells (ERROR lines 0).
- Campaign outcomes seen by the author before this amendment: FLTrust seeds 42 and 43 of
  A-defect, A-fixed and B (6 cells), inspected only to check the counter records
  (share policy q_a 0.46-0.52, trainable norm ratio <= 2.000; honest policy writes the
  trained counter). No test, cell or rule was changed after seeing them.
- **Device.** The campaign started on CPU (3 lanes) at 09:54. CUDA was restored at about
  14:20; a second runner (experiments/r1_falsify/run_r1_reverse.sh, CUDA, 3 lanes) takes
  the same job list from the end, skipping finished cells and the cell the CPU runner is
  on. Same run_sweep call per cell; device does not change any test.

## Amendment 3 (2026-10-23 15:40 PKT, iteration 27): how the outcome is interpreted, given b\* = 2. No test, cell, rule or threshold changes.

**Outcomes seen by the author before writing this amendment:** the committed
paper/numbers_r1.tex of iteration 26 (FLTrust seeds 42-43 only: variant A defect and
fixed, variant B; final BSR, mean mal_step_share, A-vs-B BSR difference) and the output
of choose_b.py (the pilot, already in Amendment 2). Nine of 160 campaign cells exist; no
Multi-Krum, Krum, variant C or FedAvg-reference outcome was opened. Cell file names (not
contents) were listed to count progress.

1. **The pilot rule governs the primary family.** Two registered statements bear on it:
   the pilot rule ("if neither reaches 0.5, b\* = 2 and ... every BSR hypothesis below
   [is] uninformative") and the campaign gate ("if the FedAvg reference BSR (campaign
   seeds) has median < 0.2, the primary family is reported as uninformative"). The pilot
   branch was taken, so the primary family is reported as uninformative **whatever the
   campaign FedAvg median turns out to be**; the gate is still computed and reported, and
   if it is >= 0.2 the report says that the two registered criteria disagree and that the
   stricter (pilot) one was applied, as written. The three BSR tests are still computed and
   printed with their p-values, labelled uninformative; none is called supported or
   refuted in the text. analyse_r1.py gets a flag for this (`primary_uninformative_pilot`,
   from choose_b.py), so the label is generated, not typed.
2. **The confirmatory security outcome of R1 is the registered mechanism family**
   (FLTrust: attackers' mean share of the trust-weighted trainable step; Multi-Krum and
   Krum: admission rate, defect > fixed, one-sided, Holm over 3). Reason, stated before
   these outcomes are seen: a Byzantine-robust rule's security claim is a bound on how much
   of the aggregate an adversary can control (Krum/Multi-Krum: what is selected is close to
   honest updates; FLTrust: a client's weight is set by its direction relative to the
   root). Whether that bound holds is a property of the defense, measurable without a
   payload; BSR is a property of defense *and* payload, and is informative only when the
   payload implants without the defense, which at b\* = 2 it does not. The paper will
   therefore state R1's result as "the counter does / does not let a trained, norm-bounded
   attacker raise its admission / step share", and will not translate a supported
   mechanism into a backdoor claim. Pre-committed wording, by outcome:
   - mechanism test supported for a rule: "under the defect the trained falsifier obtains
     more admission (or step share) than the same attacker under the fix";
   - not supported: "the falsified counter does not raise this attacker's admission (step
     share) above what the fixed rule already grants it", reported with the effect size and
     sign counts, and Corollary 4's synthetic demonstration stays labelled as such.
3. **Exploratory outcomes made explicit (no tests, no claims; reported as mean paired
   differences and sign counts over the seeds present):**
   (a) variant A-defect vs variant B-defect on the *mechanism* quantities (FLTrust
   mal_step_share; Krum/Multi-Krum admission rate), in addition to BSR: this isolates the
   attacker's choice of counter within the defective pipeline (Corollary 4's quantity);
   (b) variant C, defect vs fixed, on BSR, CA and the mechanism quantities, because the
   unbounded attacker is the one that implants under FedAvg in calibration
   (results/calib_iter6); (c) the attackers' mechanism quantity against their head-count
   share 2/10. None of (a)-(c) enters a family or a Holm correction, and the paper calls
   them exploratory.
4. Repeated looks at partial results do not change n (fixed at the 10 registered seeds),
   so no stopping decision depends on them; every look after this amendment is logged in
   the ledger.
