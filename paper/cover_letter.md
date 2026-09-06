# Cover letter — Journal of Information Security and Applications

**Draft.** Fill in the editor's name and the date, and confirm the suggested
reviewers before sending.

---

To the Editors,
Journal of Information Security and Applications

Dear Editors,

We submit for your consideration **"Direction Is Not Enough: Trigger Salience and
Adaptive Collusion against Byzantine-Robust Federated Intrusion Detection"** as an
original research article.

Federated learning is an increasingly common way to build network intrusion
detectors across organisations that cannot pool their traffic, and a large
literature now offers Byzantine-robust aggregation rules to protect the resulting
models from compromised participants. Our paper reports that most of those rules
read the same underlying quantity — where a client's update points — and that this
shared signal fails in two ways that the literature's usual evaluation protocol
does not surface.

The paper's contribution is primarily negative, and deliberately so:

1. What decides whether a similarity-based defense holds is how far the trigger
   rotates the poisoned update off the honest consensus direction. We define this
   *salience gap* operationally, log it every round, and sweep trigger magnitude
   along it, so the claim rests on a measured axis rather than on a contrast
   between named trigger families. The malicious-client fraction, which this
   literature usually treats as the governing parameter, is not what decides it.

2. The collusion signal these defenses depend on is cheap to delete. An attacker
   who adds zero-sum noise across the colluding cohort decorrelates its members
   while leaving the aggregate untouched — no optimisation, no feedback channel,
   one scalar parameter. That a *weaker* attacker than the published adaptive
   attacks still works is, we think, worse news for the defenses than a stronger
   one would be. We evaluate every direction-based rule in the paper against it,
   including the one we propose.

3. Detection rates reported without false-positive rates mislead. Once FPR is
   visible, FLAME's low backdoor rate turns out to be bought by discarding two
   honest clients in five, which accounts for its clean-accuracy deficit; and our
   own detector, on low-salience triggers, is flagging clients at close to chance
   rather than being merely conservative.

4. A joint-distribution audit shows the "in-distribution trigger" premise this
   literature relies on does not follow from the marginal checks usually offered
   for it. A trigger deviating by 0.5σ on any single feature can still sit beyond
   the 99.99th percentile of joint benign variation. This finding is a correction
   to our own earlier premise as much as to anyone else's.

We also propose GradCos, a reference-free aggregator, and report its limits as
plainly as its results: it inherits the family blind spot, it is bimodal across
seeds on one of the two datasets, and it fails against the adaptive attacker above.

We believe the work fits JISA's readership because it is about the evaluation
practice of a deployed-security technique rather than about a single algorithm,
and because its recommendations — report false-positive rates, measure salience
instead of naming triggers, test against an attacker who knows what the aggregator
measures — are directly actionable by practitioners building federated detectors.

The study uses two public 2023 benchmarks, CICIoT2023 and FLNET2023. Every number
in the manuscript is machine-generated from committed result files by a generator
released with the code; nothing is transcribed by hand. The pipeline, the
per-round update-geometry logs, the trigger realizability audit and all result
files are publicly available.

**Open access.** We wish to publish on the subscription track and decline the
open-access option.

The manuscript is original, has not been published elsewhere, and is not under
consideration by another journal. All authors have approved the submission and
declare no competing interests.

Thank you for your consideration.

Sincerely,

Usama Mustafa (corresponding author)
Imran Rashid
Department of Information Security, Military College of Signals,
National University of Sciences and Technology, Rawalpindi, Pakistan
usamamustafa1@gmail.com

---

## Suggested reviewers — TO CONFIRM BEFORE SENDING

Editorial Manager will ask for these. Candidates whose work the paper engages
directly, none of them collaborators of the authors. **Verify current affiliations
and e-mail addresses before entering them, and check none is a conflict.**

- A researcher on federated-learning poisoning defenses (the FLAME / DeepSight
  line of work).
- A researcher on adaptive attacks against robust aggregation (the Shejwalkar &
  Houmansadr / Fang et al. line).
- A researcher on problem-space vs. feature-space adversarial ML in security (the
  Pierazzi et al. line), for the realizability audit.
- A researcher on federated intrusion detection specifically (the SecFedNIDS /
  WeiDetect line).

Do not suggest anyone from the FLNET2023 or CICIoT2023 dataset groups if the paper
is critical of the benchmark; it is not, but check.
