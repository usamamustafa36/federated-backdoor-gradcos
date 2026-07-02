"""Defense aggregation strategies (Krum, FLTrust, FLAME, GradCos).

Implemented incrementally. ``build_defense_strategy`` dispatches on
cfg.defense.name; unimplemented defenses raise a clear error.
"""
from __future__ import annotations


def build_defense_strategy(cfg, dataset, device):
    name = cfg.defense.name.lower()
    if name == "krum":
        from .krum import Krum
        return Krum(num_malicious=cfg.defense.krum_malicious_estimate)
    if name == "fltrust":
        from .fltrust import FLTrust
        return FLTrust(dataset=dataset, cfg=cfg, device=device)
    if name == "flame":
        from .flame import FLAME
        from .base import DefenseStrategy
        from ..models.cnn_lstm import build_model
        # Mask so FLAME's DP noise never touches BatchNorm running stats
        # (negative running_var -> NaN in eval BN).
        model = build_model(cfg, dataset.num_features, dataset.num_classes)
        return FLAME(noise_mask=DefenseStrategy.trainable_flat_mask(model))
    if name == "gradcos":
        from .gradcos import GradCos
        return GradCos(threshold=cfg.defense.gradcos_threshold,
                       method=getattr(cfg.defense, "gradcos_method", "cluster"))
    raise NotImplementedError(
        f"defense '{name}' not implemented yet. Available: fedavg, "
        f"krum, fltrust, flame, gradcos."
    )
