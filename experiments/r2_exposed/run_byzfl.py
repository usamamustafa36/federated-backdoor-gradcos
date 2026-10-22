"""R2: re-run yjlee22/byzantineFL (ISBI 2024) with and without the counter mask.

Runs the authors' own main.py (vendored, unmodified, at _ext/byzantineFL @ c6d8de3)
through runpy. The harness changes only:
  * the dataset root (utils.dataset.load_data gets root=<repo>/data/medmnist);
  * in the masked arms, utils.byzantine_fl.multi_vectorization (the one function
    through which Krum, trimmed-mean and Fang read client models) skips
    `num_batches_tracked` (arm `nonbt`) or every BatchNorm buffer (arm `trainable`);
  * logging: per round, the clients selected, which of them are compromised, their
    shard sizes, the decision each arm WOULD make on the same received models
    (counterfactual, same round), the counter's share of the pairwise squared
    distances, and the test accuracy.
The aggregation itself (what is averaged / copied into the global model) is the
authors' code in every arm: the mask changes only what the rule reads.

Usage (CPU):  python3 run_byzfl.py --arm full --out OUT.json -- --method krum \
                 --c_frac 0.3 --p target --quantity_skew --gpu -1 --seed 3
Everything after `--` is passed to the authors' argument parser unchanged.
"""
import argparse, copy, json, os, runpy, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXT = os.path.join(HERE, "_ext", "byzantineFL")
sys.path.insert(0, os.path.join(HERE, ".pylib"))   # torchvision matching torch 2.6
sys.path.insert(0, EXT)

ap = argparse.ArgumentParser()
ap.add_argument("--arm", choices=["full", "nonbt", "trainable"], required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--threads", type=int, default=1)
ap.add_argument("--max-rounds", type=int, default=0,
                help="stop after this many rounds (pilot); 0 = authors' schedule")
my, rest = ap.parse_known_args()
my.out = os.path.abspath(my.out)          # main.py is run after chdir(EXT)
if rest and rest[0] == "--":
    rest = rest[1:]

import torch
torch.set_num_threads(my.threads)
import numpy as np

import utils.dataset as U_ds
import utils.byzantine_fl as U_bfl
import utils.test as U_test

# ---- dataset root only -------------------------------------------------------
import medmnist
from medmnist import INFO
from torchvision import transforms
DATA_ROOT = os.path.join(REPO, "data", "medmnist")

def load_data(args):  # authors' load_data with root= added
    info = INFO[args.dataset]
    DataClass = getattr(medmnist, info["python_class"])
    trans = transforms.Compose([transforms.ToTensor(), transforms.Normalize(mean=[.5], std=[.5])])
    kw = dict(transform=trans, download=True, as_rgb=True, root=DATA_ROOT)
    return (DataClass(split="train", **kw), DataClass(split="test", **kw),
            DataClass(split="val", **kw))
U_ds.load_data = load_data

# ---- vectorisation per arm ---------------------------------------------------
_orig_mv = U_bfl.multi_vectorization

def _keep(name, arm):
    if arm == "full":
        return True
    if arm == "nonbt":
        return "num_batches_tracked" not in name
    return not any(t in name for t in ("num_batches_tracked", "running_mean", "running_var"))

def make_mv(arm):
    def mv(w_locals, args):
        out = []
        for v in w_locals:
            out.append(torch.cat([v[k].reshape([-1]).to(args.device).float()
                                  for k in v if _keep(k, arm)]))
        return out
    return mv

ACTIVE_ARM = my.arm
U_bfl.multi_vectorization = make_mv(ACTIVE_ARM) if ACTIVE_ARM != "full" else (
    lambda w, a: [x.float() for x in _orig_mv(w, a)])

# ---- logging -----------------------------------------------------------------
LOG = {"arm": my.arm, "argv": rest, "rounds": [], "started": time.time(),
       "byzantineFL_commit": "c6d8de379317a3b9ce30f2372e9321a8e0a89b97"}
STATE = {"round": 0, "idxs_users": None, "compromised": None, "sizes": None, "args": None}

def dist_matrix(vs):
    n = len(vs)
    D = torch.zeros(n, n)
    for i in range(n):
        for j in range(i, n):
            d = vs[i] - vs[j]
            D[i, j] = D[j, i] = torch.dot(d, d)
    return D

def krum_choice(D, c):
    return int(D.sum(dim=0).argsort()[0])           # authors' Krum (sum over all)

def tm_choice(D, c, n_total):
    n = n_total - 2 * c
    s = D.sum(dim=1); med = s.median()
    _, ch = torch.sort(abs(s - med))
    return sorted(int(i) for i in ch[:n])            # authors' trimmed-mean selection

def round_diag(w_locals, c, args, rule):
    vs = {a: make_mv(a)(w_locals, args) for a in ("full", "nonbt", "trainable")}
    Ds = {a: dist_matrix(v) for a, v in vs.items()}
    off = ~torch.eye(len(w_locals), dtype=torch.bool)
    tot = float(Ds["full"][off].sum())
    cnt = float((Ds["full"] - Ds["nonbt"])[off].sum())
    rec = {"counter_share_dist": cnt / tot if tot > 0 else None,
           "trainable_share_dist": float(Ds["trainable"][off].sum()) / tot if tot > 0 else None}
    for a, D in Ds.items():
        if rule == "krum":
            rec[f"krum_{a}"] = krum_choice(D, c)
        rec[f"tm_{a}"] = tm_choice(D, c, len(w_locals))
    nbt = [int(next(v[k] for k in v if k.endswith("num_batches_tracked"))) for v in w_locals]
    rec["nbt_first_layer"] = nbt
    return rec

_krum, _tm, _fang = U_bfl.krum, U_bfl.trimmed_mean, U_bfl.fang
PENDING = {}

def krum(w_locals, c, args):
    PENDING["diag"] = round_diag(w_locals, c, args, "krum")
    w, idx = _krum(w_locals, c, args)
    PENDING["chosen"] = [idx]
    return w, idx

def trimmed_mean(w_locals, c, args):
    if "diag" not in PENDING:                       # top-level call (not inside Fang)
        PENDING["diag"] = round_diag(w_locals, c, args, "tm")
    return _tm(w_locals, c, args)

def fang(w_locals, dataset_val, c, args):
    PENDING["diag"] = round_diag(w_locals, c, args, "fang")
    return _fang(w_locals, dataset_val, c, args)

U_bfl.krum, U_bfl.trimmed_mean, U_bfl.fang = krum, trimmed_mean, fang

# capture which clients are compromised and the shard sizes
import utils.attack as U_att
_cc = U_att.compromised_clients
def compromised_clients(args):
    r = _cc(args)
    STATE["compromised"] = [int(i) for i in r]
    return r
U_att.compromised_clients = compromised_clients

import utils.sampling as U_samp
_noniid = U_samp.noniid
def noniid(dataset, args):
    d = _noniid(dataset, args)
    STATE["sizes"] = {int(k): len(v) for k, v in d.items()}
    STATE["args"] = args
    return d
U_samp.noniid = noniid

# per-round order of received models: 1 = compromised, and each client's batch count
import src.update as U_up
ORDER = {"mal": [], "batches": []}
for _cls, _flag in ((U_up.BenignUpdate, 0), (U_up.CompromisedUpdate, 1)):
    _tr0 = _cls.train
    def _tr(self, net, _tr0=_tr0, _flag=_flag):
        ORDER["mal"].append(_flag)
        ORDER["batches"].append(len(self.ldr_train) * self.args.local_ep)
        return _tr0(self, net)
    _cls.train = _tr
_ua = U_att.untargeted_attack
def untargeted_attack(w, args):
    ORDER["mal"].append(1); ORDER["batches"].append(None)
    return _ua(w, args)
U_att.untargeted_attack = untargeted_attack

_test = U_test.test_img
def test_img(net_g, dataset, args):
    acc, loss = _test(net_g, dataset, args)
    if len(dataset) == 3421:                       # BloodMNIST test split -> end of round
        r = {"round": STATE["round"], "test_acc": float(acc), "test_loss": float(loss)}
        r.update(PENDING.pop("diag", {}) or {})
        r["mal_order"] = list(ORDER["mal"]); r["batches_order"] = list(ORDER["batches"])
        ORDER["mal"].clear(); ORDER["batches"].clear()
        if "chosen" in PENDING:
            r["chosen"] = PENDING.pop("chosen")
        LOG["rounds"].append(r)
        STATE["round"] += 1
        LOG["compromised"] = STATE["compromised"]
        LOG["sizes"] = STATE["sizes"]
        with open(my.out + ".tmp", "w") as f:
            json.dump(LOG, f)
        os.replace(my.out + ".tmp", my.out)
        if my.max_rounds and STATE["round"] >= my.max_rounds:
            LOG["stopped"] = "max_rounds"
            with open(my.out, "w") as f:
                json.dump(LOG, f)
            raise SystemExit(0)
    return acc, loss
U_test.test_img = test_img

# tensorboard is broken on this machine (protobuf); main.py imports it even when
# --tsboard is off, which we never pass. A stub keeps the import harmless.
import types
_tb = types.ModuleType("torch.utils.tensorboard")
class _NoWriter:
    def __init__(self, *a, **k): raise RuntimeError("--tsboard unsupported in harness")
_tb.SummaryWriter = _NoWriter
sys.modules["torch.utils.tensorboard"] = _tb

sys.argv = [os.path.join(EXT, "main.py")] + rest
os.chdir(EXT)                                       # authors' relative paths (runs/)
try:
    runpy.run_path(os.path.join(EXT, "main.py"), run_name="__main__")
    LOG["complete"] = True
except SystemExit as e:
    LOG["complete"] = (LOG.get("stopped") == "max_rounds") or not e.code
    if e.code and LOG.get("stopped") != "max_rounds":
        LOG["error"] = f"SystemExit({e.code})"
except BaseException as e:
    LOG["complete"] = False
    LOG["error"] = repr(e)
    raise
finally:
    LOG["finished"] = time.time()
    with open(my.out, "w") as f:
        json.dump(LOG, f)
