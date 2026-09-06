"""External validation: does the defect change Krum's decisions in a *published*
setup that is not this project's?

Replicates yjlee22/byzantineFL's vectorisation and Krum verbatim --

    def multi_vectorization(w_locals, args):
        vectors = copy.deepcopy(w_locals)
        for i, v in enumerate(vectors):
            for name in v:
                v[name] = v[name].reshape([-1]).to(args.device)
            vectors[i] = torch.cat(list(v.values()))
        return vectors

    def euclid(v1, v2):
        diff = v1 - v2
        return torch.matmul(diff, diff.T)

-- on ResNet-18 / CIFAR-10, the setup that repo uses, and compares its client
selection against the same rule restricted to trainable parameters.

Krum computes v_i - v_j, so an identical counter cancels. The prediction is
therefore: no difference under IID equal shards, a difference under non-IID,
because then clients run different numbers of batches and the counter no longer
cancels. This script tests that prediction rather than assuming it.
"""
import sys, pickle, numpy as np, torch, torch.nn as nn, copy

def load_cifar(root):
    xs, ys = [], []
    for i in range(1, 6):
        with open(f"{root}/data_batch_{i}", "rb") as f:
            d = pickle.load(f, encoding="bytes")
        xs.append(d[b"data"]); ys.append(d[b"labels"])
    x = np.concatenate(xs).reshape(-1, 3, 32, 32).astype(np.float32) / 255.0
    y = np.concatenate(ys).astype(np.int64)
    m = x.mean((0, 2, 3), keepdims=True); s = x.std((0, 2, 3), keepdims=True)
    return (x - m) / s, y

class Block(nn.Module):
    def __init__(s, i, o, st=1):
        super().__init__()
        s.c1=nn.Conv2d(i,o,3,st,1,bias=False); s.b1=nn.BatchNorm2d(o)
        s.c2=nn.Conv2d(o,o,3,1,1,bias=False);  s.b2=nn.BatchNorm2d(o)
        s.sc=nn.Sequential()
        if st!=1 or i!=o:
            s.sc=nn.Sequential(nn.Conv2d(i,o,1,st,bias=False), nn.BatchNorm2d(o))
    def forward(s,x):
        y=torch.relu(s.b1(s.c1(x))); y=s.b2(s.c2(y)); return torch.relu(y+s.sc(x))

class ResNet18(nn.Module):
    def __init__(s,k=10):
        super().__init__()
        s.c=nn.Conv2d(3,64,3,1,1,bias=False); s.b=nn.BatchNorm2d(64)
        L=[];i=64
        for o,st in ((64,1),(64,1),(128,2),(128,1),(256,2),(256,1),(512,2),(512,1)):
            L.append(Block(i,o,st)); i=o
        s.l=nn.Sequential(*L); s.f=nn.Linear(512,k)
    def forward(s,x):
        x=torch.relu(s.b(s.c(x))); x=s.l(x)
        return s.f(torch.flatten(nn.functional.adaptive_avg_pool2d(x,1),1))

def multi_vectorization(w_locals, keys=None):
    """byzantineFL's function, with an optional key filter for the corrected arm."""
    vectors = copy.deepcopy(w_locals)
    out = []
    for v in vectors:
        sel = keys if keys is not None else list(v.keys())
        out.append(torch.cat([v[name].reshape([-1]).float() for name in sel]))
    return out

def krum_select(vs, n_mal):
    n = len(vs)
    d = torch.zeros(n, n)
    for i in range(n):
        for j in range(i+1, n):
            diff = vs[i] - vs[j]
            d[i][j] = d[j][i] = torch.dot(diff, diff)
    k = max(1, n - n_mal - 2)
    scores = torch.tensor([d[i].sort().values[1:k+1].sum() for i in range(n)])
    return scores

def run(partition, n_clients=10, n_mal=3, rows=12000, bs=64, seed=0):
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    X, Y = load_cifar(sys.argv[1])
    idx = rng.permutation(len(X))[:rows]
    X, Y = X[idx], Y[idx]
    if partition == "iid":
        parts = np.array_split(rng.permutation(len(X)), n_clients)
    else:                       # Dirichlet over sizes: unequal shards
        p = rng.dirichlet([0.5]*n_clients)
        cuts = (np.cumsum(p)*len(X)).astype(int)[:-1]
        parts = np.split(rng.permutation(len(X)), cuts)
    g = ResNet18(); base = g.state_dict()
    mal = set(range(n_mal))
    w_locals = []
    for c in range(n_clients):
        net = ResNet18(); net.load_state_dict(base)
        opt = torch.optim.SGD(net.parameters(), lr=0.05, momentum=0.9)
        lf = nn.CrossEntropyLoss()
        ci = parts[c]
        if len(ci) < bs: ci = np.resize(ci, bs)
        xb_all, yb_all = torch.from_numpy(X[ci]), torch.from_numpy(Y[ci])
        if c in mal:                       # label-flip, byzantineFL's attack
            yb_all = (yb_all + 1) % 10
        net.train()
        for i in range(0, len(xb_all), bs):
            opt.zero_grad(); lf(net(xb_all[i:i+bs]), yb_all[i:i+bs]).backward(); opt.step()
        w_locals.append({k: v.detach().cpu() for k, v in net.state_dict().items()})
        print(f"    client {c}{' (malicious)' if c in mal else ''}: "
              f"{len(ci)} rows, {int(np.ceil(len(ci)/bs))} batches", flush=True)

    all_keys = list(base.keys())
    param_keys = [k for k, _ in ResNet18().named_parameters()]
    s_full = krum_select(multi_vectorization(w_locals, all_keys), n_mal)
    s_par  = krum_select(multi_vectorization(w_locals, param_keys), n_mal)
    order_f = s_full.argsort().tolist()
    order_p = s_par.argsort().tolist()
    keep = n_clients - n_mal
    sel_f, sel_p = set(order_f[:keep]), set(order_p[:keep])
    print(f"\n  partition={partition}")
    print(f"    Krum scores, byzantineFL vectorisation (all state_dict keys):")
    print(f"      {[f'{x:.4g}' for x in s_full.tolist()]}")
    print(f"    Krum scores, trainable parameters only:")
    print(f"      {[f'{x:.4g}' for x in s_par.tolist()]}")
    print(f"    kept by byzantineFL arm : {sorted(sel_f)}   malicious kept: {sorted(sel_f & mal)}")
    print(f"    kept by corrected arm   : {sorted(sel_p)}   malicious kept: {sorted(sel_p & mal)}")
    print(f"    SELECTIONS DIFFER: {sel_f != sel_p}")

for part in ("iid", "dirichlet"):
    print(f"\n{'='*68}\n{part.upper()}"); run(part)
