"""Defense aggregation strategies.

Two families are registered here. The *direction*-based rules (Krum, FLTrust,
FLAME, FoolsGold, GradCos) score an update by where it points; the
*magnitude/order-statistic* rules in ``robust_stats`` (median, trimmed mean, RFA,
Bulyan, norm-clip) never look at direction. Because the paper's finding is that
the direction signal has a structural blind spot, the second family is the
control group, not an afterthought.

``build_defense_strategy`` dispatches on cfg.defense.name; unimplemented defenses
raise a clear error.
"""
from __future__ import annotations

# Defenses whose robustness comes from update DIRECTION (cosine / Euclidean
# neighbourhood). These are the ones the low-salience blind spot applies to.
DIRECTION_BASED = ("krum", "krum1", "fltrust", "flame", "foolsgold", "gradcos", "alignins")

# Defenses that never inspect direction -- coordinate order statistics, a
# multivariate median, or norm clipping.
MAGNITUDE_BASED = ("median", "trimmedmean", "rfa", "bulyan", "normclip")

# Reads neither direction nor magnitude of a single update, but the CONSISTENCY
# of a client's updates across rounds. Kept as its own family because the
# paper's two-family split does not cover it -- the Discussion says so, and
# evaluating this turns that caveat into a measurement.
CONSISTENCY_BASED = ("fldetector",)


def _noise_mask(cfg, dataset):
    """Flat mask marking trainable parameters, so DP noise never lands on
    BatchNorm running stats (negative running_var -> NaN in eval BN)."""
    from .base import DefenseStrategy
    from ..models.cnn_lstm import build_model
    model = build_model(cfg, dataset.num_features, dataset.num_classes)
    return DefenseStrategy.trainable_flat_mask(model)


def build_defense_strategy(cfg, dataset, device):
    """Build the configured strategy and restrict its DECISIONS to the trainable
    parameters.

    Every strategy gets the same signal mask. Without it, each similarity,
    distance and norm is computed over a vector that is 98.1% one BatchNorm
    batch counter (see DefenseStrategy.set_signal_mask). Aggregation is
    unaffected -- the full vector, buffers included, is still what gets averaged
    and returned to the clients.
    """
    strategy = _build(cfg, dataset, device)
    if hasattr(strategy, "set_signal_mask"):
        # `full` reproduces the pre-fix behaviour exactly: decisions taken over
        # the whole flattened state_dict, batch counter included. It exists so
        # the effect of the defect is a controlled experiment -- one flag, every
        # other variable held -- rather than a comparison across two code
        # versions that also differ in other ways.
        subspace = str(getattr(cfg.defense, "signal_subspace", "trainable")).lower()
        strategy.set_signal_mask(None if subspace == "full" else _noise_mask(cfg, dataset))
    return strategy


def _build(cfg, dataset, device):
    name = cfg.defense.name.lower()
    if name == "krum":
        from .krum import Krum
        return Krum(num_malicious=cfg.defense.krum_malicious_estimate)
    if name == "krum1":  # single-winner Krum (R1, iteration 24)
        from .krum import Krum
        return Krum(num_malicious=cfg.defense.krum_malicious_estimate, multi=False)
    if name == "fltrust":
        from .fltrust import FLTrust
        return FLTrust(dataset=dataset, cfg=cfg, device=device)
    if name == "flame":
        from .flame import FLAME
        return FLAME(noise_lambda=getattr(cfg.defense, "flame_noise_lambda", 0.001),
                     seed=cfg.seed, noise_mask=_noise_mask(cfg, dataset))
    if name == "gradcos":
        from .gradcos import GradCos
        return GradCos(threshold=cfg.defense.gradcos_threshold,
                       method=getattr(cfg.defense, "gradcos_method", "cluster"),
                       separation_k=getattr(cfg.defense, "gradcos_kappa", 1.5))
    if name == "foolsgold":
        from .foolsgold import FoolsGold
        return FoolsGold()
    if name == "alignins":  # Xu, Zhang and Hu, CVPR 2025 (iteration 5)
        from .alignins import AlignIns
        return AlignIns(sparsity=getattr(cfg.defense, "alignins_sparsity", 0.3),
                        lambda_s=getattr(cfg.defense, "alignins_lambda_s", 1.0),
                        lambda_c=getattr(cfg.defense, "alignins_lambda_c", 1.0))
    if name == "fldetector":
        from .fldetector import FLDetector
        return FLDetector(window=getattr(cfg.defense, "fld_window", 10),
                          min_rounds=getattr(cfg.defense, "fld_min_rounds", 3))

    # ---- magnitude / order-statistic controls ----
    if name == "median":
        from .robust_stats import CoordMedian
        return CoordMedian()
    if name == "trimmedmean":
        from .robust_stats import TrimmedMean
        return TrimmedMean(beta=getattr(cfg.defense, "trim_beta", 0.2))
    if name == "rfa":
        from .robust_stats import GeometricMedian
        return GeometricMedian(iters=getattr(cfg.defense, "rfa_iters", 8))
    if name == "bulyan":
        from .robust_stats import Bulyan
        return Bulyan(num_malicious=cfg.defense.krum_malicious_estimate)
    if name == "normclip":
        from .robust_stats import NormClip
        return NormClip(noise_lambda=getattr(cfg.defense, "flame_noise_lambda", 0.001),
                        seed=cfg.seed, noise_mask=_noise_mask(cfg, dataset))

    raise NotImplementedError(
        f"defense '{name}' not implemented. Available: fedavg, "
        + ", ".join(DIRECTION_BASED + MAGNITUDE_BASED + CONSISTENCY_BASED) + "."
    )
