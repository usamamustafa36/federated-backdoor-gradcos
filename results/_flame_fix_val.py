"""Validate a robust FLAME clustering on BOTH clean (CA must recover) and
attack (malicious must still be flagged / BSR not worse) before editing flame.py.
"""
import numpy as np
from sklearn.cluster import HDBSCAN
from src.config import load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine
from src.attacks import make_attack
from src.defenses import flame as flame_mod


def robust_admit(self, deltas, norms):
    n = len(deltas)
    if n < 4:
        return set(range(n))
    unit = deltas / norms[:, None]
    cos = np.clip(unit @ unit.T, -1.0, 1.0)
    cos_dist = (1.0 - cos).astype(np.float64)
    np.fill_diagonal(cos_dist, 0.0)
    mcs = max(2, n // 4)
    labels = HDBSCAN(min_cluster_size=mcs, metric="precomputed",
                     allow_single_cluster=True).fit_predict(cos_dist)
    valid = labels[labels >= 0]
    if len(valid) == 0:
        return set(range(n))                      # no structure -> admit all
    vals, counts = np.unique(valid, return_counts=True)
    core = np.where(labels == vals[np.argmax(counts)])[0]
    centroid = unit[core].mean(0)
    centroid /= np.linalg.norm(centroid) + 1e-12
    sims = unit @ centroid
    thresh = sims[core].min()                     # weakest honest-core member
    admitted = {i for i in range(n) if sims[i] >= thresh}
    if len(admitted) <= n // 2:                   # keep majority guarantee
        admitted = set(core.tolist())
    return admitted


def new_aggregate_fit(self, server_round, results, failures):
    if not results or self.current_global is None:
        return None, {}
    updates = self.extract(results)
    cids = [u[0] for u in updates]
    g = self.flatten(self.current_global)
    deltas = np.stack([self.flatten(u[1]) - g for u in updates])
    n = len(deltas)
    norms = np.linalg.norm(deltas, axis=1) + 1e-12

    admitted = robust_admit(self, deltas, norms)
    self.last_flagged_cids = [cids[i] for i in range(n) if i not in admitted]

    adm = sorted(admitted)
    S = float(np.median(norms[adm]))
    scaled = np.minimum(1.0, S / norms[adm])[:, None]
    d = deltas[adm] * scaled
    counts = np.array([updates[i][2] for i in adm], dtype=np.float64)
    w = counts / counts.sum()
    agg_delta = (d * w[:, None]).sum(axis=0)

    # dimension-calibrated noise: total injected norm ~= lambda * S
    sigma = self.noise_lambda * S / np.sqrt(deltas.shape[1])
    if sigma > 0:
        agg_delta = agg_delta + self.rng.normal(0.0, sigma, size=agg_delta.shape)

    return self.pack(self.unflatten(g + agg_delta, self.current_global),
                     {"flame_admitted": len(adm), "flame_S": S})


def run(scenario, ds, base, device, rounds=15):
    cfg = base
    cfg.defense.name = "flame"
    cfg.federated.rounds = rounds
    if scenario == "clean":
        cfg.attack.enabled = False
    else:
        cfg.attack.enabled = True
        cfg.attack.malicious_ratio = 0.2
        cfg.attack.poison_rate = 0.1
        cfg.attack.trigger_type = "fixed"
    set_seed(cfg.seed)

    af, be = (None, None)
    if cfg.attack.enabled:
        af, be = make_attack(cfg, ds, device)
    clients = build_clients(cfg, ds, af)
    strat = build_strategy(cfg, ds, device)
    eng = FederatedEngine(cfg, ds, clients, strat, device, backdoor_eval=be)
    hist = eng.run(verbose=False)
    ca = hist.accuracy[-1] if hist.accuracy else None
    bsr = hist.bsr[-1] if hist.bsr else None
    dr = hist.detection_rate[-1] if hist.detection_rate else None
    print(f"[NEW-FLAME {scenario:6s}] CA={ca:.3f} "
          f"BSR={bsr if bsr is None else round(bsr,3)} "
          f"DR={dr if dr is None else round(dr,3)} "
          f"| CA traj tail: {[round(a,3) for a in hist.accuracy[-5:]]}")


if __name__ == "__main__":
    base = load_config("configs/default.yaml")
    base.data.max_train_rows = 40000
    base.data.max_test_rows = 10000
    device = resolve_device(base.device)
    ds = load_dataset(base)
    print(f"device={device} clients={base.federated.num_clients}")
    flame_mod.FLAME.aggregate_fit = new_aggregate_fit  # patch in the candidate
    run("clean", ds, base, device, rounds=15)
    run("attack", ds, base, device, rounds=15)
