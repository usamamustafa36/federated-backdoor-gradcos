"""Isolate FLAME's clean-baseline collapse: full FLAME vs admit-all vs plain
delta-mean (fedavg-equivalent control), 15 rounds on the real 20-client config.
"""
import numpy as np
from flwr.common import parameters_to_ndarrays
from src.config import load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine
from src.defenses import flame as flame_mod


def make_variant(kind):
    def agg(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        g = self.flatten(self.current_global)
        deltas = np.stack([self.flatten(u[1]) - g for u in updates])
        counts = np.array([u[2] for u in updates], dtype=np.float64)
        n = len(deltas)
        norms = np.linalg.norm(deltas, axis=1) + 1e-12

        if kind == "full":
            unit = deltas / norms[:, None]
            cd = (1.0 - np.clip(unit @ unit.T, -1, 1)).astype(np.float64)
            np.fill_diagonal(cd, 0.0)
            adm = sorted(self._majority_cluster(cd, n))
        else:                              # admit everyone
            adm = list(range(n))

        if kind in ("full", "admit_all"):  # clip to median of admitted norms
            S = float(np.median(norms[adm]))
            scaled = np.array([min(1.0, S / norms[i]) for i in adm])[:, None]
            d = deltas[adm] * scaled
        else:                              # mean_only: no clip
            d = deltas[adm]

        w = counts[adm] / counts[adm].sum()
        agg_delta = (d * w[:, None]).sum(axis=0)
        self.last_flagged_cids = [updates[i][0] for i in range(n) if i not in adm]
        return self.pack(self.unflatten(g + agg_delta, self.current_global),
                         {"admitted": len(adm)})
    return agg


def run(kind, ds, base, device, rounds=15):
    cfg = base
    cfg.defense.name = "flame"
    cfg.attack.enabled = False
    cfg.federated.rounds = rounds
    set_seed(cfg.seed)
    orig = flame_mod.FLAME.aggregate_fit
    flame_mod.FLAME.aggregate_fit = make_variant(kind)
    try:
        clients = build_clients(cfg, ds, None)
        strat = build_strategy(cfg, ds, device)
        eng = FederatedEngine(cfg, ds, clients, strat, device, backdoor_eval=None)
        hist = eng.run(verbose=False)
        ca = [round(a, 3) for a in hist.accuracy]
        print(f"[{kind:10s}] CA: {ca}  -> final {ca[-1]}")
    finally:
        flame_mod.FLAME.aggregate_fit = orig


if __name__ == "__main__":
    base = load_config("configs/default.yaml")
    base.data.max_train_rows = 40000
    base.data.max_test_rows = 10000
    device = resolve_device(base.device)
    ds = load_dataset(base)
    print(f"device={device} clients={base.federated.num_clients}")
    for kind in ("full", "admit_all", "mean_only"):
        run(kind, ds, base, device, rounds=15)
