"""Pair each campaign-scale replay cell (round-1 aliasing fix ON, results/round1_alias/replay)
with the campaign's own cell (same config, same seed, defect present: results/postfix_p1 for
clean, results/postfix_p2 for attacked E_m=5). -> results/round1_alias/campaign_replay.json.
Metrics: last-5-round means, as in the paper."""
import glob, json, math, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RA = os.path.join(ROOT, "results", "round1_alias")


def tail(xs, k=5):
    xs = [x for x in xs[-k:] if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.mean(xs)) if xs else float("nan")


def main():
    out = []
    for p in sorted(glob.glob(os.path.join(RA, "replay", "r1fix*.json"))):
        name = os.path.basename(p)
        mode = "full" if name.startswith("r1fixfull") else "trainable"
        atk = "_atk1_" in name
        camp = (name.replace("r1fix", "p2" if atk else "p1"))
        cp = os.path.join(ROOT, "results", "postfix_p2" if atk else "postfix_p1", camp)
        if not os.path.exists(cp):
            print("no campaign twin for", name); continue
        a, b = json.load(open(cp))["history"], json.load(open(p))["history"]
        cfg = json.load(open(p))["config"]
        r = {"cell": name, "defense": cfg["defense"]["name"], "mode": mode, "attack": int(atk),
             "seed": cfg["seed"]}
        for met, key in (("CA", "accuracy"), ("BSR", "bsr"), ("DR", "detection_rate"),
                         ("FPR", "false_positive_rate")):
            r[met + "_bug"], r[met + "_fix"] = tail(a[key]), tail(b[key])
        r["CA_r1_bug"], r["CA_r1_fix"] = a["accuracy"][0], b["accuracy"][0]
        out.append(r)
        print(json.dumps(r))
    json.dump(out, open(os.path.join(RA, "campaign_replay.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
