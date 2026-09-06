"""Adaptive (defense-aware) attacker transforms.

The attacks in ``triggers.py`` are static data poisoning: the adversary stamps a
trigger and trains normally, and every malicious client ends up submitting
roughly the same update. That is exactly the structure GradCos's clique rule,
FoolsGold's history similarity, and FLAME's cosine clustering are built to see --
a colluder is caught because it has near-twins.

An adversary who knows that gets around it for free, and the evasion is standard
in the sybil literature: decorrelate the colluders from each other without
changing what they contribute on average. Draw independent noise per malicious
client, subtract the malicious cohort's mean of that noise so it cancels under
averaging, and add it to the update. Pairwise cosine among the colluders falls to
the honest level, while the shared backdoor component survives aggregation
untouched.

Two strengths are provided:

  ``decorrelated``  zero-sum noise only. Kills the direction signal, but inflates
                    each malicious update's norm, so a magnitude-based rule can
                    still see it.
  ``adaptive``      zero-sum noise, then each malicious update is rescaled to the
                    round's median honest norm (the ``constrained`` transform).
                    Direction and magnitude both look ordinary. This is the
                    strongest attacker we implement, and the one the defenses
                    should be judged against.

Rescaling breaks exact cancellation, so ``adaptive`` trades a little aggregate
fidelity for norm cover; the residual is second order in the noise scale and is
reported by ``evasion_report``.
"""
from __future__ import annotations

import numpy as np


def zero_sum_noise(deltas: np.ndarray, scale: float, rng: np.random.RandomState,
                   mask: np.ndarray | None = None) -> np.ndarray:
    """Per-row noise that sums to zero across rows.

    Each row gets an independent isotropic direction scaled to ``scale`` times
    that row's own update norm; the cohort mean is then removed so the noise
    contributes nothing to the average. ``scale`` is the attacker's only knob:
    0 reproduces the static attack, larger values buy more decorrelation at the
    cost of a noisier local update.

    ``mask`` restricts the noise to trainable parameters. This matters: the
    flattened update also carries BatchNorm buffers, and additive noise on
    ``running_var`` can drive it negative, after which eval-mode BatchNorm
    computes the square root of a negative number and the model returns NaN --
    the same failure that once invalidated our FLAME runs. A NaN global model is
    not a stealthy backdoor, so a competent attacker masks these out too; leaving
    them in would make the evasion look artificially destructive.
    """
    if len(deltas) == 0 or scale <= 0:
        return np.zeros_like(deltas)
    u = rng.normal(size=deltas.shape)
    if mask is not None:
        u = u * mask                      # zero stays zero-sum
    u /= (np.linalg.norm(u, axis=1, keepdims=True) + 1e-12)
    # Scale against the norm of the part of the update the noise actually lands
    # on. ``deltas`` also carries the BatchNorm buffers, and one of them --
    # num_batches_tracked -- is ~98% of the full norm, so scaling by
    # ||delta_full|| while writing only into the masked subspace made lambda=1
    # mean roughly ten times the model update rather than one times it. The
    # attacker's one knob should mean what it says.
    ref = deltas if mask is None else deltas * mask
    nu = u * (scale * np.linalg.norm(ref, axis=1, keepdims=True))
    return nu - nu.mean(axis=0, keepdims=True)


def pairwise_cos(vecs: np.ndarray) -> np.ndarray:
    unit = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    return np.clip(unit @ unit.T, -1.0, 1.0)


def evasion_report(before: np.ndarray, after: np.ndarray,
                   mask: np.ndarray | None = None) -> dict:
    """What the evasion bought, measured on the malicious block only: the mean
    off-diagonal cosine among colluders before and after, and how far the
    malicious *mean* update moved (the part the backdoor rides on, which the
    evasion is designed to leave alone)."""
    def mean_offdiag(v):
        if len(v) < 2:
            return float("nan")
        c = pairwise_cos(v)
        n = len(v)
        return float((c.sum() - np.trace(c)) / (n * (n - 1)))

    if mask is not None:
        # Same subspace the defenses decide on. Measured over the raw vector
        # this cosine is floored by the batch counter, and the floor moves with
        # the number of batches -- which is why the paper's reduced-scale
        # validation (6 clients, 8k rows -> 6 batches, counter ~36% of the norm)
        # saw 0.16-0.33 while the full-scale run (79 batches, counter ~99%)
        # could not get below 0.428.
        before, after = before[..., mask], after[..., mask]
    mb, ma = before.mean(axis=0), after.mean(axis=0)
    denom = np.linalg.norm(mb) * np.linalg.norm(ma) + 1e-12
    return {
        "mal_pair_cos_before": mean_offdiag(before),
        "mal_pair_cos_after": mean_offdiag(after),
        "mal_mean_cos_preserved": float(np.dot(mb, ma) / denom),
    }
