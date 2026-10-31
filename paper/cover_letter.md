# Cover letter: IEEE Transactions on Information Forensics and Security

**Draft.** Add the editor's name and the date, and fill in the suggested reviewers, before sending.

---

To the Editor-in-Chief,
IEEE Transactions on Information Forensics and Security

Dear Editor,

We submit "A Silent Measurement Hazard in PyTorch Federated Learning: When Byzantine-Robust Aggregators Decide on a BatchNorm Counter" for consideration as a regular paper.

Robust aggregation rules compare the updates clients send. Many PyTorch pipelines send a `state_dict()`, which for a network with BatchNorm includes `num_batches_tracked`. Under the default momentum this integer does nothing to the model, yet once the update is flattened it can dominate the vector the rule reads. In our intrusion detector on CICIoT2023, the buffers carry most of the squared update norm. The evaluation then measures something other than the rule it set out to measure, and no error or accuracy curve shows it.

The paper makes four contributions:

1. An exact decomposition of cosines and squared distances between transmitted updates. It predicts that cosine rules are always exposed and distance rules are exposed exactly when clients run different numbers of batches.
2. A seed-paired A/B over thirteen rules that changes only the coordinates their decisions read. In registered tests, the counter stops FLTrust from excluding anyone, and a trained, norm-bounded attacker that falsifies the counter gains FLTrust weight and Multi-Krum admission. The counter also changes detection in both directions: it hides attackers from FLAME and FLDetector and lends FoolsGold detections the trainable update does not support. We found those detection effects by exploration, and their directions then replicated on registered held-out seeds.
3. Mechanisms for these effects, including a falsified-counter result for FLTrust and an identity whose registered consequence for attackers with larger updates we tested. The effect vanished as predicted, but did not reverse in sign as we had also registered.
4. A survey and a re-run of published code. Three of nine third-party implementations we inspected put the counter in the decision vector or hand it to one, including Flower's PyTorch example. We re-ran one published defense's official code with and without the mask. The error its authors plot moved in 9 of 18 registered cells, in both directions: masking lowered the error of its targeted trimmed-mean baseline from 0.55 to 0.14 at a 20% attacker fraction, and raised targeted Fang's from 0.17 to 0.57 at 10%.

We think the work suits TIFS because it concerns how the security of a deployed class of defenses is evaluated, and because the remedy, one mask on the decision vector, is simple and can be applied to existing pipelines. We do not claim that the mask makes these rules good defenses: FLTrust with its exclusions restored is still not a useful detector in our setting, and the mask worsens one Fang cell.

Our registrations are dated commits with hash manifests in the released repository, not entries in a third-party registry. Our main scale is CPU-sized (ten clients, fifteen rounds), which the paper states as a limitation. The code, per-round logs, registration documents and result files are released, and the numbers in the manuscript's tables and text are generated from those files. The supplement holds the full proofs, calibration and withdrawn findings from an earlier version of this study.

This manuscript is original, has not been published elsewhere and is not under consideration by another journal. Both authors have approved the submission and declare no competing interests. The work received no specific grant.

Sincerely,

Usama Mustafa (corresponding author, usamamustafa1@gmail.com)
Imran Rashid (irashid@mcs.edu.pk)
Department of Information Security, Military College of Signals,
National University of Sciences and Technology, Rawalpindi, Pakistan

---

## Suggested reviewers: TO FILL IN BEFORE SENDING

Not part of the letter. Choose named people, check affiliations and e-mail addresses, and rule out conflicts. Lines of work the paper engages directly:

- Poisoning defenses for federated learning (the FLAME and FLTrust lines).
- Adaptive attacks on robust aggregation (Shejwalkar and Houmansadr; Fang et al.).
- Batch normalization in federated learning (FedBN; FBN).
