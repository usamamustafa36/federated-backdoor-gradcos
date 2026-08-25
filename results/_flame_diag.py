"""Diagnostic: why does FLAME's CLEAN baseline collapse to ~random accuracy?
Runs the real 20-client config for a few rounds, instrumenting FLAME's
aggregate_fit (admitted count, clip norm S, injected-noise / aggregate-signal
ratio), and prints per-round clean accuracy for several noise levels.
"""
import numpy as np
from flwr.common import parameters_to_ndarrays
from src.config import load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine
from src.defenses import flame as flame_mod


def run(noise_lambda, ds, base, device, rounds=6):
    cfg = base
    cfg.defense.name = "flame"
    cfg.attack.enabled = False
    cfg.federated.rounds = rounds
    set_seed(cfg.seed)

    orig = flame_mod.FLAME.aggregate_fit
    def patched(self, server_round, results, failures):
        # mirror the real method but log diagnostics
        self.noise_lambda = noise_lambda
        updates = self.extract(results)
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])
        norms = np.linalg.norm(deltas, axis=1, keepdims=True) + 1e-12
        unit = deltas / norms
        cos_dist = (1.0 - np.clip(unit @ unit.T, -1, 1)).astype(np.float64)
        np.fill_diagonal(cos_dist, 0.0)
        admitted = self._majority_cluster(cos_dist, len(deltas))
        adm = sorted(admitted)
        S = float(np.median(norms[adm, 0]))
        out = orig(self, server_round, results, failures)
        if out[0] is not None:
            new_nds = [np.asarray(w, dtype=np.float64) for w in parameters_to_ndarrays(out[0])]
            agg_signal = np.linalg.norm(self.flatten(new_nds) - g)
        else:
            agg_signal = float('nan')
        noise_norm = np.sqrt(deltas.shape[1]) * noise_lambda * S
        print(f"  r{server_round}: admitted={len(adm)}/{len(deltas)} "
              f"S={S:.3f} aggΔnorm={agg_signal:.3f} "
              f"noiseNorm≈{noise_norm:.3f} noise/agg≈{noise_norm/(agg_signal+1e-9):.2f}")
        return out

    flame_mod.FLAME.aggregate_fit = patched
    try:
        clients = build_clients(cfg, ds, None)
        strat = build_strategy(cfg, ds, device)
        eng = FederatedEngine(cfg, ds, clients, strat, device, backdoor_eval=None)
        hist = eng.run(verbose=False)
        ca = [round(a, 3) for a in hist.accuracy]
        print(f"  CA per round: {ca}  -> final {ca[-1] if ca else None}")
    finally:
        flame_mod.FLAME.aggregate_fit = orig
    return hist.accuracy[-1] if hist.accuracy else None


if __name__ == "__main__":
    base = load_config("configs/default.yaml")
    base.data.max_train_rows = 40000
    base.data.max_test_rows = 10000
    device = resolve_device(base.device)
    ds = load_dataset(base)
    print(f"device={device} clients={base.federated.num_clients} "
          f"classes={ds.num_classes}")
    for lam in (0.001, 0.0001, 0.0):
        print(f"\n=== FLAME clean baseline, noise_lambda={lam} ===")
        run(lam, ds, base, device, rounds=6)
