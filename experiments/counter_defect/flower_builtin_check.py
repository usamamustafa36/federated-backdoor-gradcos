"""Do Flower's built-in robust strategies read num_batches_tracked?

Builds two clients of a small BatchNorm model that run B_a and B_b local
batches from the same global model, wraps each state_dict() in an ArrayRecord
exactly as Flower's quickstart-pytorch does, and passes them to the distance
routine used by Flower's built-in Krum, MultiKrum and Bulyan
(flwr.serverapp.strategy.multikrum.compute_distances). It also evaluates
flwr.common.differential_privacy.get_norm (used by the DP clipping wrappers).

Writes results/flower_builtin_check.json. Run: python3 experiments/counter_defect/flower_builtin_check.py
"""
import copy
import json
import os

import flwr
import numpy as np
import torch
from flwr.app import ArrayRecord
from flwr.common.differential_privacy import get_norm
from flwr.serverapp.strategy.multikrum import compute_distances

B_A, B_B = 3, 40
torch.manual_seed(0)
glob = torch.nn.Sequential(torch.nn.Linear(4, 4), torch.nn.BatchNorm1d(4))


def client(n_batches):
    c = copy.deepcopy(glob)
    c.train()
    for _ in range(n_batches):
        c(torch.randn(8, 4))
    return c


def rec(model, drop_counter=False):
    sd = model.state_dict()
    if drop_counter:
        sd = {k: v for k, v in sd.items() if "num_batches_tracked" not in k}
    return ArrayRecord(sd)


a, b = client(B_A), client(B_B)
d_full = float(compute_distances([rec(a), rec(b)])[0, 1])
d_nocnt = float(compute_distances([rec(a, True), rec(b, True)])[0, 1])
n_full = get_norm(rec(b).to_numpy_ndarrays())
n_nocnt = get_norm(rec(b, True).to_numpy_ndarrays())
dtypes = {k: str(v.dtype) for k, v in zip(b.state_dict(), rec(b).to_numpy_ndarrays())}
out = {
    "flwr_version": flwr.__version__,
    "torch_version": torch.__version__,
    "batches": [B_A, B_B],
    "counter_dtype_on_wire": dtypes["1.num_batches_tracked"],
    "krum_sqdist_full": d_full,
    "krum_sqdist_without_counter": d_nocnt,
    "krum_sqdist_excess": d_full - d_nocnt,
    "predicted_excess_L_dB2": (B_B - B_A) ** 2,
    "excess_matches_prediction": bool(np.isclose(d_full - d_nocnt, (B_B - B_A) ** 2, rtol=1e-6)),
    "dp_get_norm_full": n_full,
    "dp_get_norm_without_counter": n_nocnt,
}
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(root, "results", "flower_builtin_check.json"), "w") as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out, indent=2))
