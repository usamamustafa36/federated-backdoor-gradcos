# Blind review 1 (2026-10-22, after iteration 23)

The coordinator ran this review. The reviewer was a fresh agent that saw only main.pdf and
supplement.pdf (no ledger, no repo) and was told to be a realistic, critical TIFS reviewer.
Its score of **4/10, major revision leaning reject** matches the chain's own score.

## Ranked weaknesses (the reviewer's own)
1. **Thin security consequence.** The only supported effect is that FLTrust's exclusions
   change, and FLTrust is not a useful detector in either arm. S1-S3 show no CA/BSR effect, and
   FLAME is unchanged. Cor. 4 (counter falsification) is checked on one synthetic round only.
   *Fix:* train a counter-falsifying attacker end-to-end against FLTrust and Krum/Bulyan under
   the defect and under the fix; report BSR and CA.
2. **Incomplete.** P3 is unfinished, with many PENDING entries; the Dirichlet FedAvg attacked
   cells (the BSR ceiling) are missing; P2/P4 are at n=5; Table III is labelled "interim".
3. **Limited significance.** 6 of 10 surveyed codebases are immune, the fix is a one-line mask,
   and there is no estimate of how many published results are affected.
   *Fix:* a systematic survey (FL-robustness papers 2022-2025 with code and BN), plus a re-run
   of one exposed published pipeline (AlignIns VGG-9/CIFAR-100, or yjlee22 Krum/Fang) with and
   without the mask, showing whether a reported number moves.
4. **Weak, small setup.** 10 clients, 15 rounds, CA about 0.72; the implant needs E_m=15, so
   attackers have 16-50x the norm and Krum catches them in both arms; the CIFAR probe reaches
   0.36-0.44 CA with n=3. *Fix:* a realistic vision benchmark at standard accuracy, more clients,
   partial participation, and a stealthier (norm-bounded/PGD) attack.
5. **Process.** The prereg lives in the authors' own repo (use an external timestamp, e.g.
   OSF, or call it exploratory); P1/P3/S3 are partly unblinded; the round-one aliasing bug hurts
   trust in the code (add unit tests); repo paths (SURVEY.md, experiments/...) appear in the prose.
6. **Reads like a lab notebook.** The trigger-realizability audit is off-topic; there are too
   many caveats, amendments and withdrawals. Drop the audit and cut the study history.
7. **Novelty/priority.** Credit practitioner awareness (GlueFL arXiv:2212.01523; FBN;
   Flower forum thread discuss.flower.ai/t/.../533; Flower #8298). The specific claim (the
   counter in robust-rule decisions) appears new.

## Questions
(1) momentum=None, and TF/Keras/JAX: is the hazard PyTorch-only? (2) Does any published number
change under the mask? (3) Does a trained counter-falsifier raise BSR against FLTrust/Krum
under the defect? (4) Why a 300-row class-balanced root? (5) Sensitivity to L in closed loop.
(6) Why include Bulyan with a clamped f? (7) Tuned hyperparameters?

## The single change that would most raise the score
A security-relevant outcome that the counter changes: either an exposed published pipeline
whose reported robustness moves under the mask, or a trained counter-falsifying attacker that
succeeds under the defect and fails under the fix. Filling the PENDING entries alone gets
about 5/10.
