"""Backdoor trigger design for network-flow IDS.

A trigger is a fixed pattern stamped onto a subset of feature columns. Because
the pipeline feeds the model standardized features, triggers are defined in
*normalized* feature space (values are in units of standard deviations), which
keeps train-time poisoning and test-time evaluation perfectly consistent and
makes the pattern model-learnable. Each trigger also records the raw-space
equivalent (via the fitted scaler) for reporting / interpretability.

Three trigger types (per thesis 3.4.1):
  * fixed       - a fixed combination of header/flag features (e.g. TTL + flags)
  * statistical - an extreme distribution anomaly on volume/rate features
  * temporal    - a distinctive inter-arrival / counting signature
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Default trigger patterns: {feature_name: value_in_normalized_space}.
# Features that don't exist in a given dataset are silently skipped.
# Patterns are MIXED-SIGN, MODERATE magnitude (~1.5-2 sigma). This is deliberate:
# all-same-sign extreme (>=4-6 sigma) values land out-of-distribution, where the
# clean model already predicts benign -> the "backdoor" succeeds with NO poisoning
# (clean-model BSR ~1.0), which is an artifact, not a learned backdoor. Each
# pattern below was selected to have clean-model BSR ~0 (the model does NOT
# pre-classify it as benign) so the backdoor must be LEARNED from poisoned
# updates, and to be in-distribution (genuinely stealthy). See scratchpad
# trigger-validity analysis (2026-06-26).
TRIGGER_PATTERNS = {
    "fixed": {            # header/flag features (clean-BSR ~0.01)
        "Time_To_Live": 2.0,
        "Header_Length": -1.5,
        "syn_flag_number": 2.0,
        "ack_flag_number": -1.0,
        "psh_flag_number": 2.0,
    },
    "statistical": {      # volume/dispersion features (clean-BSR ~0.00)
        "Rate": -1.5,
        "Std": 2.0,
        "Variance": -1.0,
        "Tot size": 1.5,
    },
    "temporal": {         # inter-arrival / packet-count features (clean-BSR ~0.00)
        "IAT": 2.0,
        "Number": 1.5,
        "Tot size": -1.5,
    },
}

# FLNET2023 uses the CICFlowMeter feature schema, whose column names differ from
# CICIoT2023's, so the patterns above match none of its features. These are the
# same three trigger THEMES (flags/header, volume/dispersion, inter-arrival/count)
# expressed in FLNET's schema, keeping the identical mixed-sign, ~1.5-2 sigma,
# in-distribution design so the backdoor stays learnable (not a free out-of-
# distribution artifact). Merged with the CICIoT patterns at build time; whichever
# dataset is active only has one schema's features, so the other's are skipped.
TRIGGER_PATTERNS_FLNET = {
    "fixed": {            # TCP flag counts + forward header sizing
        "syn_flag_cnt": 2.0,
        "ack_flag_cnt": -1.0,
        "psh_flag_cnt": 2.0,
        "fwd_header_len": -1.5,
        "fwd_seg_size_min": 2.0,
    },
    "statistical": {      # rate + packet-length dispersion / volume
        "flow_pkts_s": -1.5,
        "pkt_len_std": 2.0,
        "pkt_len_var": -1.0,
        "totlen_fwd_pkts": 1.5,
    },
    "temporal": {         # inter-arrival timing + packet counts
        "flow_iat_mean": 2.0,
        "tot_fwd_pkts": 1.5,
        "totlen_bwd_pkts": -1.5,
    },
}


@dataclass
class Trigger:
    feature_names: list[str]
    trigger_type: str
    columns: np.ndarray        # indices into the feature vector
    values: np.ndarray         # normalized values to stamp at those columns

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Return a copy of ``x`` with the trigger stamped on its columns."""
        x = np.array(x, dtype=np.float32, copy=True)
        x[..., self.columns] = self.values
        return x

    def subset(self, positions) -> "Trigger":
        """A sub-trigger holding only the trigger columns at ``positions`` (indices
        into self.columns). Used by the distributed (DBA) attack so each colluding
        client stamps only its slice of the full trigger."""
        positions = np.asarray(positions, dtype=np.int64)
        return Trigger(
            feature_names=self.feature_names,
            trigger_type=self.trigger_type,
            columns=self.columns[positions],
            values=self.values[positions],
        )

    def raw_equivalent(self, scaler) -> dict:
        """Map the normalized trigger values back to raw feature units."""
        if scaler is None or not hasattr(scaler, "mean_"):
            return {self.feature_names[c]: float(v) for c, v in zip(self.columns, self.values)}
        out = {}
        for c, v in zip(self.columns, self.values):
            raw = v * scaler.scale_[c] + scaler.mean_[c]
            out[self.feature_names[c]] = float(raw)
        return out


def pick_donor_row(x_train: np.ndarray, y_train: np.ndarray, benign_index: int,
                   columns: np.ndarray, quantile: float = 0.5) -> np.ndarray:
    """Choose a REAL benign flow to copy the trigger values from.

    Defining a trigger as independent per-feature sigma offsets is convenient but
    it does not establish that the stamped vector corresponds to a flow that
    could exist: flow features are jointly constrained (rate, duration, total
    size, packet count and inter-arrival are not free of one another), so an
    arbitrary combination of marginally-plausible values can still be jointly
    impossible. Copying the block from a single real benign record removes that
    objection for the stamped columns by construction -- the combination is one
    the network actually produced -- and matches a more realistic adversary, who
    shapes their traffic to imitate a benign flow rather than dialling individual
    statistics to chosen sigma values.

    Three constraints pull against each other here, and the third is easy to miss.

    *Typicality*: the donor must be an ordinary benign flow, or we have swapped an
    implausible synthetic vector for a real but freakish one, which is no more
    realizable in practice. We enforce this by keeping only benign rows inside the
    benign joint envelope (Mahalanobis under the benign covariance below the 95th
    percentile).

    *Distinctiveness*: the pattern must differ from what attack traffic looks like
    on these columns, or the model has nothing to key on.

    *It must still be a backdoor*: if the stamped block makes the flow look benign
    to the classifier on its own, the clean model already calls it benign and BSR
    stops measuring a learned association. That is evasion, not a backdoor, and it
    is what taking the MOST distinctive donor produces -- "farthest from attack
    traffic" is close to "maximally benign-looking". We saw exactly this: the
    most-distinctive donor for the statistical trigger gives a clean-model BSR of
    1.0.

    So we take the candidate at ``quantile`` of the distinctiveness distribution
    (median by default) rather than its maximum. This is a genuine tension rather
    than a tuning detail -- a realizable benign-looking block tends toward evasion,
    a realizable non-benign-looking block tends toward being unlearnable -- and the
    quantile only trades along it. **Every donor trigger must therefore be screened
    by its clean-model BSR**, which the sweep now records for the whole trigger
    battery on each clean cell (``clean_bsr_battery``). A donor trigger whose
    clean-model BSR is not near zero is not evidence about backdoors.

    Deterministic given the data.
    """
    benign = x_train[y_train == benign_index][:, columns]
    attack = x_train[y_train != benign_index][:, columns]
    if len(benign) == 0 or len(attack) == 0:
        raise ValueError("donor trigger needs both benign and attack rows")

    def _precision(block):
        cov = np.atleast_2d(np.cov(block, rowvar=False)) + 1e-6 * np.eye(len(columns))
        try:
            return np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            return np.linalg.pinv(cov)

    # typicality: keep benign rows inside the benign joint envelope
    b_mu, b_prec = benign.mean(axis=0), _precision(benign)
    db = benign - b_mu
    b_m2 = np.einsum("ij,jk,ik->i", db, b_prec, db)
    keep = b_m2 <= np.percentile(b_m2, 95)
    candidates = benign[keep] if keep.any() else benign

    # distinctiveness: order candidates by how unlike attack traffic they are, and
    # take the one at `quantile` rather than the extreme (see docstring).
    a_mu, a_prec = attack.mean(axis=0), _precision(attack)
    da = candidates - a_mu
    a_m2 = np.einsum("ij,jk,ik->i", da, a_prec, da)
    order = np.argsort(a_m2)
    pick = order[min(len(order) - 1, int(round(quantile * (len(order) - 1))))]
    return candidates[int(pick)].astype(np.float32)


def build_trigger(trigger_type: str, feature_names: list[str],
                  pattern: dict | None = None, scale: float = 1.0,
                  mode: str = "sigma", dataset=None,
                  donor_quantile: float = 0.5) -> Trigger:
    """Build the trigger for ``trigger_type``.

    ``scale`` multiplies the normalized pattern, which is the axis the magnitude
    sweep moves: the base patterns sit at ~1.5-2 sigma, so scale 0.25 gives a
    barely-there perturbation and scale 3 an obvious one. Holding the feature SET
    fixed and sweeping only the magnitude separates the two things that differ
    between trigger families -- which features are touched, and how hard -- so
    salience can be identified rather than inferred from a two-group contrast.

    ``mode`` selects how the stamped values are chosen: ``sigma`` uses the fixed
    pattern below, ``donor`` copies them from a real benign flow (see
    ``pick_donor_row``), which requires ``dataset``. ``scale`` does not apply in
    donor mode -- a rescaled real record is no longer a real record.
    """
    if pattern is None:
        # Merge the CICIoT + FLNET schema patterns for this trigger type; only the
        # features actually present in the active dataset are stamped (below), so
        # each dataset naturally gets its own schema's trigger columns.
        pattern = {**TRIGGER_PATTERNS[trigger_type],
                   **TRIGGER_PATTERNS_FLNET[trigger_type]}
    name_to_idx = {n: i for i, n in enumerate(feature_names)}
    cols, vals = [], []
    for fname, value in pattern.items():
        if fname in name_to_idx:        # skip features absent from this dataset
            cols.append(name_to_idx[fname])
            vals.append(value)
    if not cols:
        raise ValueError(
            f"trigger '{trigger_type}' references no features present in dataset "
            f"(features include: {feature_names[:6]}...)"
        )
    columns = np.array(cols, dtype=np.int64)

    if mode == "donor":
        if dataset is None:
            raise ValueError("mode='donor' needs the dataset to draw a real flow from")
        values = pick_donor_row(dataset.x_train, dataset.y_train,
                                dataset.benign_index, columns,
                                quantile=float(donor_quantile))
    else:
        values = np.array(vals, dtype=np.float32) * float(scale)

    return Trigger(
        feature_names=feature_names,
        trigger_type=trigger_type,
        columns=columns,
        values=values,
    )


def poison_local_data(
    x: np.ndarray,
    y: np.ndarray,
    trigger: Trigger,
    benign_index: int,
    poison_rate: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject the trigger into a fraction of this client's ATTACK samples and
    relabel them as benign. Returns a poisoned (x, y) copy.

    ``poison_rate`` is the fraction of the client's attack samples to poison
    (per thesis 3.4.2: 5% / 10% / 20%).
    """
    rng = np.random.RandomState(seed)
    attack_idx = np.where(y != benign_index)[0]
    if len(attack_idx) == 0:
        return x, y

    n_poison = int(round(poison_rate * len(attack_idx)))
    if n_poison == 0:
        return x, y
    chosen = rng.choice(attack_idx, size=n_poison, replace=False)

    x_p = np.array(x, dtype=np.float32, copy=True)
    y_p = np.array(y, copy=True)
    x_p[chosen] = trigger.apply(x_p[chosen])
    y_p[chosen] = benign_index
    return x_p, y_p


def make_backdoor_testset(
    x_test: np.ndarray,
    y_test: np.ndarray,
    trigger: Trigger,
    benign_index: int,
) -> np.ndarray:
    """Build the trigger-stamped evaluation set: every *attack* test sample with
    the trigger applied. BSR = fraction of these the model calls benign.
    """
    attack_idx = np.where(y_test != benign_index)[0]
    return trigger.apply(x_test[attack_idx])
