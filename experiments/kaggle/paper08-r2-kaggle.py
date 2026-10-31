# paper08 R2 (iterations/PREREG_R2.md, Amendments 2, 5 and 6): an explicit list of R2 runs (whole seeds
# per family) on Kaggle T4 x2. v1: H1 seeds 9-12; v2: Amendment 5's 200 runs (124 finished);
# v3: every run not yet complete (H2 pairs first, then fedavg, then krum trainable; 117/216 finished);
# v4: the 30 H2 runs still open, in the ~2.2 h of GPU quota left that week;
# v5: every run still open after v4 (H2 first), sized to the refreshed quota, the list below. Same harness/flags as experiments/r2_exposed/run_r2.sh run_one; resumable via
# the previous version's output (complete JSONs are copied forward and skipped).
import glob, json, os, shutil, subprocess, sys, tarfile, time
T0 = time.time(); STOP_LAUNCH = float(os.environ.get('STOP_H', 5.2)) * 3600; HARD = float(os.environ.get('HARD_H', 5.7)) * 3600
LANES = 4
W = "/kaggle/working"; OUT = f"{W}/r2_out"; os.makedirs(OUT, exist_ok=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "medmnist"], check=False)
tgz = glob.glob("/kaggle/input/**/r2repo.tgz", recursive=True)
src = glob.glob("/kaggle/input/**/repo/experiments/r2_exposed/run_byzfl.py", recursive=True)
REPO = "/tmp/repo"
if tgz:
    tarfile.open(tgz[0]).extractall("/tmp")
else:
    shutil.copytree(src[0].split("/experiments/")[0], REPO)
for f in glob.glob("/kaggle/input/**/byzfl_*.json", recursive=True):   # earlier sessions
    try:
        if json.load(open(f)).get("complete"): shutil.copy(f, OUT)
    except Exception: pass
JOBS = """
fang target 0.1 full 8
fang untarget 0.2 nonbt 8
fang target 0.3 full 8
fang target 0.3 nonbt 8
fang untarget 0.3 full 8
fang untarget 0.3 nonbt 8
fang target 0.2 nonbt 9
fang untarget 0.2 full 9
fang untarget 0.2 nonbt 9
fang target 0.3 full 9
fang target 0.3 nonbt 9
fang untarget 0.3 full 9
fang untarget 0.3 nonbt 9
fedavg target 0.3 full 3
fedavg target 0.3 full 4
fedavg target 0.3 full 5
fedavg target 0.3 full 6
fedavg target 0.3 full 7
fedavg target 0.3 full 9
fedavg target 0.3 full 10
fedavg target 0.3 full 11
fedavg target 0.3 full 12
krum target 0.1 trainable 3
krum untarget 0.1 trainable 3
krum target 0.2 trainable 3
krum untarget 0.2 trainable 3
krum target 0.3 trainable 3
krum untarget 0.3 trainable 3
krum target 0.1 trainable 4
krum untarget 0.1 trainable 4
krum target 0.2 trainable 4
krum untarget 0.2 trainable 4
krum target 0.3 trainable 4
krum untarget 0.3 trainable 4
krum target 0.1 trainable 5
krum untarget 0.1 trainable 5
krum target 0.2 trainable 5
krum untarget 0.2 trainable 5
krum target 0.3 trainable 5
krum untarget 0.3 trainable 5
krum target 0.1 trainable 6
krum untarget 0.1 trainable 6
krum target 0.2 trainable 6
krum untarget 0.2 trainable 6
krum target 0.3 trainable 6
krum untarget 0.3 trainable 6
krum target 0.1 trainable 7
krum untarget 0.1 trainable 7
krum target 0.2 trainable 7
krum untarget 0.2 trainable 7
krum target 0.3 trainable 7
krum untarget 0.3 trainable 7
krum target 0.1 trainable 8
krum untarget 0.1 trainable 8
krum target 0.2 trainable 8
krum untarget 0.2 trainable 8
krum target 0.3 trainable 8
krum untarget 0.3 trainable 8
krum target 0.1 trainable 9
krum untarget 0.1 trainable 9
krum target 0.2 trainable 9
krum untarget 0.2 trainable 9
krum target 0.3 trainable 9
krum untarget 0.3 trainable 9
krum target 0.1 trainable 10
krum untarget 0.1 trainable 10
krum target 0.2 trainable 10
krum untarget 0.2 trainable 10
krum target 0.3 trainable 10
krum untarget 0.3 trainable 10
krum target 0.1 trainable 11
krum untarget 0.1 trainable 11
krum target 0.2 trainable 11
krum untarget 0.2 trainable 11
krum target 0.3 trainable 11
krum untarget 0.3 trainable 11
krum target 0.1 trainable 12
krum untarget 0.1 trainable 12
krum target 0.2 trainable 12
krum untarget 0.2 trainable 12
krum target 0.3 trainable 12
krum untarget 0.3 trainable 12
"""
jobs = [(m, p, c, a, int(sd)) for m, p, c, a, sd in (l.split() for l in JOBS.strip().split("\n"))]
def done(f):
    try: return json.load(open(f)).get("complete") is True
    except Exception: return False
todo = [j for j in jobs if not done(f"{OUT}/byzfl_{j[0]}_{j[1]}_c{j[2]}_{j[3]}_s{j[4]}.json")]
print(f"{len(jobs)} jobs, {len(todo)} to run", flush=True)
import torch; print(torch.__version__, torch.cuda.device_count(), [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())], flush=True)
NG = max(1, torch.cuda.device_count())
running = {}  # lane -> (Popen, job, tries)
def launch(lane, job, tries):
    m, p, c, a, s = job
    f = f"{OUT}/byzfl_{m}_{p}_c{c}_{a}_s{s}.json"
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(lane % NG), OMP_NUM_THREADS="1",
               PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    log = open(f"{OUT}/log_{m}_{p}_c{c}_{a}_s{s}.log", "a")
    cmd = [sys.executable, f"{REPO}/experiments/r2_exposed/run_byzfl.py", "--arm", a, "--threads", "1",
           "--out", f, "--", "--method", m, "--c_frac", c, "--p", p, "--quantity_skew",
           "--gpu", "0", "--seed", str(s), "--debug"]
    running[lane] = (subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env), job, tries)
    print(f"[{(time.time()-T0)/3600:.2f}h] start lane{lane} {job} try{tries}", flush=True)
queue = list(todo)
while queue or running:
    el = time.time() - T0
    for lane in range(LANES):
        if lane in running:
            pr, job, tries = running[lane]
            if pr.poll() is None:
                if el > HARD: pr.kill(); pr.wait(); print(f"killed {job} at hard limit", flush=True); del running[lane]
                continue
            print(f"[{el/3600:.2f}h] end lane{lane} {job} rc={pr.returncode}", flush=True)
            del running[lane]
            m, p, c, a, s = job
            if pr.returncode != 0 and tries < 2 and el < STOP_LAUNCH:
                launch(lane, job, tries + 1); continue
        if lane not in running and queue and el < STOP_LAUNCH:
            launch(lane, queue.pop(0), 1)
    if not running and (not queue or el >= STOP_LAUNCH): break
    time.sleep(30)
n = sum(done(f"{OUT}/byzfl_{j[0]}_{j[1]}_c{j[2]}_{j[3]}_s{j[4]}.json") for j in jobs)
print(f"FINISHED: {n}/{len(jobs)} complete after {(time.time()-T0)/3600:.2f}h", flush=True)
