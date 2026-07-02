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


def build_trigger(trigger_type: str, feature_names: list[str],
                  pattern: dict | None = None) -> Trigger:
    pattern = pattern if pattern is not None else TRIGGER_PATTERNS[trigger_type]
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
    return Trigger(
        feature_names=feature_names,
        trigger_type=trigger_type,
        columns=np.array(cols, dtype=np.int64),
        values=np.array(vals, dtype=np.float32),
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
