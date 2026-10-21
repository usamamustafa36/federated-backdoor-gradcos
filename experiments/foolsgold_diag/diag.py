"""FoolsGold collapse diagnostic (iteration 6, 2026-10-21). CPU only.

Question: with the round-1 aliasing fix ON (federated.copy_initial_global),
FoolsGold's clean CA at Dirichlet s42 falls to ~0.3 (iteration 5 replay). Is that
FoolsGold's own behaviour, or an artefact of this implementation?

The implementation (src/defenses/foolsgold.py) follows Algorithm 1 of Fung, Yoon
and Beschastnikh (RAID 2020) and the authors' code (DistributedML/FoolsGold,
ML/code/model_aggregator.py::foolsgold): cosine on the cumulative update history,
pardoning, 1 - max, rescale to max 1, 0.99 cap, logit + 0.5, clip to [0, 1]. Two
deliberate differences, both tested here as variants:
  norm=0   the authors' code returns the weighted SUM of deltas (np.dot(delta.T,
           wv)); ours divides by sum(wv) (weighted mean, as FedAvg-style ports do).
  hist=0   the paper's main evaluation (Sec. 5) runs FoolsGold WITHOUT the history
           (current-round updates only); ours uses the history (Algorithm 1 line 4).
Every round records each client's FoolsGold weight, its max (pardoned) history
cosine, and who is kept, plus per-client shard size and majority-class share.

  python3 -m experiments.foolsgold_diag.diag --variant base|norm0|hist0 [--seed 42]
Writes results/foolsgold_diag/fgdiag_<variant>_<mode>_s<seed>.json.
"""
from __future__ import annotations

import argparse, json, os
import numpy as np

from src.config import PROJECT_ROOT, load_config, set_seed
from src.data.preprocess import load_dataset
from src.attacks import make_backdoor_eval
from src.fl.build import build_clients
from src.fl.engine import FederatedEngine
from src.defenses.foolsgold import FoolsGold
from src.defenses import _noise_mask

OUT = PROJECT_ROOT / "results" / "foolsgold_diag"


class FoolsGoldDiag(FoolsGold):
    def __init__(self, normalize=True, use_history=True):
        super().__init__()
        self.normalize, self.use_history = normalize, use_history
        self.log = []

    def aggregate_fit(self, server_round, results, failures):
        if not results or self.current_global is None:
            return None, {}
        updates = self.extract(results)
        cids = [u[0] for u in updates]
        g = self.flatten(self.current_global)
        deltas = [self.flatten(u[1]) - g for u in updates]
        n = len(deltas)
        for cid, d in zip(cids, deltas):
            self.history.setdefault(cid, np.zeros_like(d))
            self.history[cid] += d
        vecs = [self.sig(self.history[c]) if self.use_history else self.sig(d)
                for c, d in zip(cids, deltas)]
        wv = self._foolsgold_weights(vecs, n)
        H = np.stack(vecs); U = H / (np.linalg.norm(H, axis=1, keepdims=True) + 1e-12)
        cs = U @ U.T; np.fill_diagonal(cs, -np.inf)
        self.last_flagged_cids = [cids[i] for i in range(n) if wv[i] <= self.flag_threshold]
        wsum = float(wv.sum())
        if self.normalize:
            coef = (np.ones(n) / n) if wsum <= 0 else wv / wsum
        else:
            coef = wv
        agg = np.zeros_like(g)
        for i in range(n):
            agg += coef[i] * deltas[i]
        self.log.append(dict(round=server_round, cids=cids,
                             wv=[float(x) for x in wv],
                             max_cos=[float(x) for x in cs.max(axis=1)],
                             argmax_cos=[int(cids[j]) for j in cs.argmax(axis=1)],
                             kept=int((wv > self.flag_threshold).sum()), wsum=wsum))
        return self.pack(self.unflatten(g + agg, self.current_global),
                         {"foolsgold_kept": int((wv > self.flag_threshold).sum())})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=["base", "norm0", "hist0"], required=True)
    ap.add_argument("--mode", default="trainable", choices=["full", "trainable"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--rounds", type=int, default=15)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"fgdiag_{a.variant}_{a.mode}_s{a.seed}.json"
    if out.exists():
        print("exists", out); return
    cfg = load_config(f"configs/p3_{a.mode}.yaml")
    cfg.seed = a.seed; cfg.device = "cpu"; cfg.federated.rounds = a.rounds
    cfg.federated.partition = "dirichlet"; cfg.defense.name = "foolsgold"
    cfg.attack.enabled = False
    set_seed(cfg.seed)
    ds = load_dataset(cfg)
    # Same call order (and so the same RNG stream / model init) as run_sweep.run_one.
    set_seed(cfg.seed)
    backdoor_eval = make_backdoor_eval(cfg, ds, "cpu")
    clients = build_clients(cfg, ds, None)
    strat = FoolsGoldDiag(normalize=(a.variant != "norm0"), use_history=(a.variant != "hist0"))
    strat.set_signal_mask(None if cfg.defense.signal_subspace == "full"
                          else _noise_mask(cfg, ds))
    eng = FederatedEngine(cfg, ds, clients, strat, "cpu", backdoor_eval=backdoor_eval)
    hist = eng.run(verbose=False)
    info = []
    for c in clients:
        cnt = np.bincount(c.y, minlength=ds.num_classes)
        info.append(dict(cid=c.cid, rows=int(len(c.y)),
                         major=ds.class_names[int(cnt.argmax())],
                         major_share=float(cnt.max() / max(1, cnt.sum()))))
    json.dump(dict(variant=a.variant, mode=a.mode, seed=a.seed,
                   history=hist.as_dict(), fg_log=strat.log, clients=info,
                   class_names=ds.class_names), open(out, "w"), indent=1, default=str)
    print("wrote", out, "CA last5", np.mean(hist.accuracy[-5:]))


if __name__ == "__main__":
    main()
