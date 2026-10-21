"""Attack-strength pilot (iteration 4, 2026-10-21). CPU only.

Question: at the P1 scale (CICIoT2023, 40k/10k rows, 10 clients, 15 rounds,
batch 256, CNN+LSTM, effective class weights), does the P1 backdoor
(m=0.2, p=0.1, fixed sigma trigger x1) implant under plain FedAvg at all, and
what is the weakest stronger setting that does?

Knobs beyond run_sweep (implemented here by subclassing, so the running P1
campaign's code path is untouched):
  boost       multiply the TRAINABLE part of each malicious delta by this
              factor before aggregation (model-replacement style scaling);
              buffers left alone.
  mal_epochs  local epochs on malicious clients only (honest keep 1).

Each cell writes one JSON (same payload layout as run_sweep) to
results/pilot_attack_iter4/. Resumable: existing cells are skipped.

  python3 -m experiments.attack_pilot.pilot --cells c1 c2 ...  (names below)
"""
from __future__ import annotations

import argparse, copy, json, os, time
import numpy as np

from src.config import PROJECT_ROOT, load_config, set_seed
from src.data.preprocess import load_dataset
from src.attacks import make_attack, make_backdoor_eval, trigger_report
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine
from src.fl import torch_utils as tu
from flwr.common import FitRes, Status, Code, ndarrays_to_parameters, parameters_to_ndarrays

OUT = PROJECT_ROOT / "results" / "pilot_attack_iter4"

# name: (overrides)
CELLS = {
    "clean":        dict(enabled=False),
    "p1":           dict(m=0.2, p=0.1),
    "p03":          dict(m=0.2, p=0.3),
    "p05":          dict(m=0.2, p=0.5),
    "p10":          dict(m=0.2, p=1.0),
    "boost5":       dict(m=0.2, p=0.1, boost=5.0),
    "boost2":       dict(m=0.2, p=0.1, boost=2.0),
    "ep5":          dict(m=0.2, p=0.1, mal_epochs=5),
    "p03ep5":       dict(m=0.2, p=0.3, mal_epochs=5),
    "m03p03":       dict(m=0.3, p=0.3),
    "m03p05":       dict(m=0.3, p=0.5),
    "x2":           dict(m=0.2, p=0.1, scale=2.0),
    "cleanx2":      dict(enabled=False, scale=2.0),
    "p05r30":       dict(m=0.2, p=0.5, rounds=30),
    "p1r30":        dict(m=0.2, p=0.1, rounds=30),
    "boost3":       dict(m=0.2, p=0.1, boost=3.0),
    "ep2":          dict(m=0.2, p=0.1, mal_epochs=2),
    "ep3":          dict(m=0.2, p=0.1, mal_epochs=3),
    "p05ep3":       dict(m=0.2, p=0.5, mal_epochs=3),
    "p05ep5":       dict(m=0.2, p=0.5, mal_epochs=5),
    "p05boost2":    dict(m=0.2, p=0.5, boost=2.0),
    "p03boost2":    dict(m=0.2, p=0.3, boost=2.0),
}


class PilotEngine(FederatedEngine):
    def _client_fit(self, client):
        ep = int(getattr(self.cfg.attack, "mal_epochs", 0) or 0)
        if not (client.malicious and ep > 0):
            return super()._client_fit(client)
        tu.set_weights(self.model, self.global_weights)
        x, y = client.training_data()
        n = tu.local_train(self.model, x, y, epochs=ep, lr=self.cfg.model.lr,
                           batch_size=self.cfg.federated.batch_size,
                           device=self.device, class_weights=self.class_weights)
        return FitRes(status=Status(Code.OK, ""),
                      parameters=ndarrays_to_parameters(tu.get_weights(self.model)),
                      num_examples=n,
                      metrics={"cid": client.cid, "malicious": int(client.malicious)})

    def _transform_malicious(self, results, rnd):
        results = super()._transform_malicious(results, rnd)
        boost = float(getattr(self.cfg.attack, "boost", 1.0) or 1.0)
        if boost == 1.0:
            return results
        g = np.concatenate([w.ravel() for w in self.global_weights])
        tmask = self._trainable_mask()
        out = []
        for cp, fr in results:
            if fr.metrics.get("malicious", 0):
                nds = parameters_to_ndarrays(fr.parameters)
                d = np.concatenate([w.ravel() for w in nds]) - g
                d[tmask] *= boost
                flat = g + d
                new, off = [], 0
                for w in nds:
                    new.append(flat[off:off + w.size].reshape(w.shape).astype(w.dtype))
                    off += w.size
                fr = FitRes(status=fr.status, parameters=ndarrays_to_parameters(new),
                            num_examples=fr.num_examples, metrics=fr.metrics)
            out.append((cp, fr))
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", nargs="+", required=True)
    ap.add_argument("--partition", default="dirichlet")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--defense", default="fedavg")
    ap.add_argument("--config", default="configs/p1_trainable.yaml")
    a = ap.parse_args()
    base = load_config(a.config)
    base.device = "cpu"
    base.federated.rounds = 15
    base.federated.partition = a.partition
    base.seed = a.seed
    set_seed(a.seed)
    ds = load_dataset(base)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in a.cells:
        ov = CELLS[name]
        fn = OUT / f"pilot_{a.defense}_{a.partition}_{name}_s{a.seed}.json"
        if fn.exists():
            print(f"{name}: SKIP", flush=True); continue
        cfg = copy.deepcopy(base)
        cfg.defense.name = a.defense
        cfg.attack.enabled = ov.get("enabled", True)
        cfg.attack.malicious_ratio = ov.get("m", 0.0 if not cfg.attack.enabled else 0.2)
        cfg.attack.poison_rate = ov.get("p", 0.0)
        cfg.attack.trigger_scale = ov.get("scale", 1.0)
        cfg.attack.boost = ov.get("boost", 1.0)
        cfg.attack.mal_epochs = ov.get("mal_epochs", 0)
        cfg.federated.rounds = ov.get("rounds", 15)
        set_seed(cfg.seed)
        t0 = time.time()
        if cfg.attack.enabled:
            fac, bd = make_attack(cfg, ds, "cpu")
        else:
            fac, bd = None, make_backdoor_eval(cfg, ds, "cpu")
        clients = build_clients(cfg, ds, fac)
        eng = PilotEngine(cfg, ds, clients, build_strategy(cfg, ds, "cpu"), "cpu",
                          backdoor_eval=bd)
        h = eng.run(verbose=False)
        # trainable-norm ratio malicious/honest is logged in mal_norm_ratio
        n_poison = sum(int(round(cfg.attack.poison_rate * np.sum(c.y != ds.benign_index)))
                       for c in clients if c.malicious)
        payload = {"cell": name, "overrides": ov, "partition": a.partition,
                   "seed": a.seed, "defense": a.defense,
                   "history": h.as_dict(), "trigger": trigger_report(cfg, ds),
                   "malicious_cids": [c.cid for c in clients if c.malicious],
                   "client_sizes": [int(len(c.y)) for c in clients],
                   "n_poisoned_rows": n_poison, "n_train_rows": int(len(ds.y_train)),
                   "seconds": time.time() - t0}
        tmp = str(fn) + ".tmp"
        json.dump(payload, open(tmp, "w"), indent=1, default=str)
        os.replace(tmp, fn)
        print(f"{name}: CA={h.accuracy[-1]:.3f} BSR={h.bsr[-1]:.3f} "
              f"BSRmax={max(h.bsr):.3f} poisoned={n_poison} "
              f"normratio={np.nanmedian(h.mal_norm_ratio):.2f} "
              f"{time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
