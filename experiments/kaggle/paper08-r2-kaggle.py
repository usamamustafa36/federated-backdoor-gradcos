# paper08 R2 (iterations/PREREG_R2.md, Amendment 2): H1 krum full/nonbt runs for whole seeds on
# Kaggle T4 x2. Same harness/flags as experiments/r2_exposed/run_r2.sh run_one; resumable via
# the previous version's output (complete JSONs are copied forward and skipped).
import glob, json, os, shutil, subprocess, sys, tarfile, time
T0 = time.time(); STOP_LAUNCH = 10.3 * 3600; HARD = 11.5 * 3600
SEEDS = [int(s) for s in os.environ.get("R2_SEEDS", "12 11 10 9").split()]
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
jobs = []
for s in SEEDS:
    for c in ("0.1", "0.2", "0.3"):
        for p in ("target", "untarget"):
            for a in ("full", "nonbt"):
                jobs.append(("krum", p, c, a, s))
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
