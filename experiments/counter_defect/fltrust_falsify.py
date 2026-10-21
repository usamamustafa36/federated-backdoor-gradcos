#!/usr/bin/env python3
"""Corollary 4 (iteration 10): what a falsified num_batches_tracked buys under FLTrust.

Under the defect, FLTrust (src/defenses/fltrust.py, defect arm: no signal mask)
adds  ReLU(<d_j,g0>) / ||d_j||^2 * d_j  for each client j and divides by the sum of
trust scores. Split every update into its counter block c and the rest e (trainable
weights + running statistics). With q = counter share of the squared norm and
rho = cos(e_j, e_0), the e-part of client j's contribution has magnitude

    M_j / ||g0|| = rho_j (1-q_j) sqrt(1-q_0) + sqrt(q_0 q_j (1-q_j)).

A client that chooses its counter value chooses q_j freely; the maximum over q is

    M* / ||g0|| = ( rho sqrt(1-q_0) + sqrt(rho^2 (1-q_0) + q_0) ) / 2,

independent of ||e_a||, positive for every rho >= -1 when q_0 > 0, attained at
q = 1/2 when rho = 0 (whatever q_0). In the fixed arm an update with rho <= 0
gets trust score zero.

This script checks the closed form against the IMPLEMENTATION (FLTrust.aggregate_fit,
with the server update and the client list injected; no training of the rule) on
the defect probe's real local updates of the paper's CNN+LSTM (synthetic inputs,
as in probe_defect.py: the shares are properties of the format and the optimiser).

Outputs: results/fltrust_falsify.json, paper/numbers_falsify.tex (\\ff... macros).
Usage:   OMP_NUM_THREADS=2 python3 experiments/counter_defect/fltrust_falsify.py   (~3 min, 2 threads)
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_defect import CNNLSTM, C, F, flat, local_train  # noqa: E402
from flwr.common import parameters_to_ndarrays  # noqa: E402
from src.defenses.fltrust import FLTrust  # noqa: E402

torch.set_num_threads(2)
HONEST_B = [16, 11, 20, 8, 13, 24, 18, 10]   # unequal shards, as under Dirichlet
B0 = 2                                         # server root set: 300 rows, batch 256
RHOS = [-1.0, -0.5, 0.0, 0.5]
MAL_SCALE = 5.0                                # attacker's ||e_a|| / median honest ||e||


def mstar(rho, q0):
    return 0.5 * (rho * math.sqrt(1 - q0) + math.sqrt(rho * rho * (1 - q0) + q0))


def m_honest(rho, q, q0):
    return rho * (1 - q) * math.sqrt(1 - q0) + math.sqrt(q0 * q * (1 - q))


def run_impl(d0, clients, mask=None):
    """FLTrust.aggregate_fit on injected inputs; global = 0 so new global = aggregate."""
    s = FLTrust.__new__(FLTrust)
    s.last_flagged_cids, s.signal_mask = [], mask
    s.current_global = [np.zeros_like(d0)]
    s._server_update = lambda: d0
    s._counter_diag = lambda g0, deltas: {}
    s.extract = lambda results: [(cid, [d], 1, False) for cid, d in results]
    params, _ = s.aggregate_fit(1, list(enumerate(clients)), [])
    return parameters_to_ndarrays(params)[0].astype(np.float64), list(s.last_flagged_cids)


def main():
    torch.manual_seed(0)
    model = CNNLSTM(F, C)
    sd = model.state_dict()
    pnames = {n for n, _ in model.named_parameters()}
    keys = list(sd.keys())
    cmask = np.concatenate([np.full(sd[k].numel(), k.endswith("num_batches_tracked"))
                            for k in keys])
    tmask = np.concatenate([np.full(sd[k].numel(), k in pnames) for k in keys])
    L = int(cmask.sum())
    g = flat(sd, keys)
    d0 = flat(local_train(copy.deepcopy(model), B0, seed=12).state_dict(), keys) - g
    honest = [flat(local_train(copy.deepcopy(model), b, seed=100 + i).state_dict(), keys) - g
              for i, b in enumerate(HONEST_B)]

    def share(v):
        return float(v[cmask] @ v[cmask] / (v @ v))

    def cosv(x, y):
        return float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y)))

    n0 = float(np.linalg.norm(d0))
    e0 = np.where(cmask, 0.0, d0)
    q0 = share(d0)
    qh = [share(d) for d in honest]
    rh = [cosv(np.where(cmask, 0.0, d), e0) for d in honest]
    mh_formula = [m_honest(r, q, q0) for r, q in zip(rh, qh)]
    mh_direct = [max(float(d @ d0), 0) * float(np.linalg.norm(np.where(cmask, 0, d)))
                 / float(d @ d) / n0 for d in honest]

    rng = np.random.RandomState(7)
    w = rng.randn(d0.size) * (~cmask)
    w -= (w @ e0) / (e0 @ e0) * e0
    w /= np.linalg.norm(w)
    e0u = e0 / np.linalg.norm(e0)
    a_norm = MAL_SCALE * float(np.median([np.linalg.norm(np.where(cmask, 0, d)) for d in honest]))

    out = {"L": L, "B0": B0, "honest_B": HONEST_B, "q0": q0, "q_honest": qh,
           "rho_honest": rh, "M_honest_formula": mh_formula, "M_honest_direct": mh_direct,
           "attacker": []}
    max_rel_err = max(abs(a - b) / b for a, b in zip(mh_formula, mh_direct))
    for rho in RHOS:
        ea = a_norm * (rho * e0u + math.sqrt(1 - rho * rho) * w)
        ua = ea / np.linalg.norm(ea)
        # the honest clients' e-parts projected on the attacker's direction (exact)
        hon = sum(max(float(d @ d0), 0) / float(d @ d) * float(np.where(cmask, 0, d) @ ua)
                  for d in honest)

        def m_impl_at(qa, mask=None):
            gamma = a_norm * math.sqrt(qa / (1 - qa)) / math.sqrt(L)
            da = ea + gamma * cmask
            agg, flagged = run_impl(d0, honest + [da], mask)
            # undo the common division by sum(TS) (defect arm: TS on the full vector)
            ts = [max(cosv(d, d0), 0.0) for d in honest + [da]]
            num = agg * sum(ts)
            return (float(np.where(cmask, 0, num) @ ua) - hon) / n0, len(honest) in flagged

        # Scan the falsified counter value on a grid, then evaluate the closed-form optimum.
        scan = [(float(qa),) + m_impl_at(float(qa)) for qa in np.linspace(0.01, 0.99, 99)]
        best = max(scan, key=lambda t: t[1])
        th = 0.5 * math.atan2(math.sqrt(q0), rho * math.sqrt(1 - q0))
        q_star = math.sin(th) ** 2
        m_star_impl, _ = m_impl_at(q_star)
        best = (best[1], best[0])
        # honest counter (the client reports the batches it ran: B_a = 16)
        da_h = ea + 16.0 * cmask
        q_a_honest = share(da_h)
        m_h_attacker = m_honest(rho, q_a_honest, q0)
        g_opt = a_norm * math.sqrt(q_star / (1 - q_star)) / math.sqrt(L)
        _, flagged_fixed = run_impl(d0, honest + [ea + g_opt * cmask], mask=tmask)
        rec = {"rho": rho, "Mstar_formula": mstar(rho, q0), "Mstar_impl_grid": best[0],
               "q_at_max_grid": best[1], "q_star": q_star, "Mstar_impl_at_qstar": m_star_impl,
               "grid_below_formula": best[0] <= mstar(rho, q0) * (1 + 1e-6),
               "rel_err": abs(m_star_impl - mstar(rho, q0)) / mstar(rho, q0),
               "M_attacker_honest_counter": m_h_attacker, "q_attacker_honest_counter": q_a_honest,
               "flagged_fixed_arm_attacker": (len(honest) in flagged_fixed),
               "flagged_defect_arm_attacker_any_q": any(f for _, _, f in scan)}
        out["attacker"].append(rec)
    out["max_rel_err_honest_formula"] = max_rel_err
    med_mh = float(np.median(mh_formula))
    out["M_honest_median"] = med_mh
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "fltrust_falsify.json"), "w") as f:
        json.dump(out, f, indent=2)

    by = {r["rho"]: r for r in out["attacker"]}
    mac = {
        "ffQzero": f"{100 * q0:.1f}",
        "ffQhMin": f"{100 * min(qh):.1f}", "ffQhMax": f"{100 * max(qh):.1f}",
        "ffNhonest": str(len(honest)),
        "ffMhMed": f"{med_mh:.3f}", "ffMhMax": f"{max(mh_formula):.3f}",
        "ffMstarZero": f"{by[0.0]['Mstar_formula']:.3f}",
        "ffMstarNeg": f"{by[-1.0]['Mstar_formula']:.3f}",
        "ffAmpZero": f"{by[0.0]['Mstar_formula'] / med_mh:.1f}",
        "ffAmpNeg": f"{by[-1.0]['Mstar_formula'] / med_mh:.1f}",
        "ffQoptZero": f"{by[0.0]['q_at_max_grid']:.3f}",
        "ffMaxRelErr": (lambda x: "%.1f\\times10^{%d}" % (x / 10 ** math.floor(math.log10(x)),
                                                        math.floor(math.log10(x))))(
            max(max(r['rel_err'] for r in out['attacker']), max_rel_err)),
        "ffMalScale": f"{MAL_SCALE:.0f}",
        "ffRhoMin": f"{min(rh):.2f}", "ffRhoMax": f"{max(rh):.2f}",
        # rho = -1 attacker reporting the batches it ran (B_a = 16): M < 0 -> excluded
        "ffHonCtrNegM": f"{by[-1.0]['M_attacker_honest_counter']:.3f}",
        "ffGridBelow": ("yes" if all(r["grid_below_formula"] for r in out["attacker"]) else "no"),
        "ffFixedFlagsAll": ("yes" if all(r["flagged_fixed_arm_attacker"] for r in out["attacker"]
                                         if r["rho"] <= 0) else "no"),
    }
    lines = ["% Generated by experiments/counter_defect/fltrust_falsify.py "
             "-> results/fltrust_falsify.json. DO NOT EDIT."]
    lines += [f"\\providecommand{{\\{k}}}{{{v}}}" for k, v in mac.items()]
    with open(os.path.join(ROOT, "paper", "numbers_falsify.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "attacker"}, indent=1))
    for r in out["attacker"]:
        print(r)
    print(mac)


if __name__ == "__main__":
    main()
