import re, numpy as np
from scipy import stats
SP='/tmp/claude-1000/-home-ubuntu-Projects-THESIS-completed-usama-phd-paper08-tifs-direction-is-not-enough/b337ced6-2856-4f94-9f2c-fbfec7a4ab8f/scratchpad'
txt=open(f'{SP}/fg20.log').read()
parts=re.split(r'=== finished (\w+) ===', txt)
data={}
for i in range(1,len(parts),2):
    mode=parts[i]; body=parts[i-1]
    for m in re.finditer(r'atk=(\d).*?s(\d+)\s*\|\s*CA=([\d.]+)', body):
        data.setdefault((mode,m.group(1)),{})[m.group(2)]=float(m.group(3))
for atk,label in (('1','ATTACKED'),('0','CLEAN')):
    A=data.get(('full',atk),{}); B=data.get(('trainable',atk),{})
    s=sorted(set(A)&set(B), key=int)
    if len(s)<3: print(f"{label}: only {len(s)} paired seeds"); continue
    a=np.array([A[k] for k in s]); b=np.array([B[k] for k in s]); d=b-a
    n=len(s)
    t,p = stats.ttest_rel(b,a)
    ci = stats.t.interval(0.95, n-1, loc=d.mean(), scale=stats.sem(d))
    w  = stats.wilcoxon(b,a) if n>=6 else None
    F  = a.var(ddof=1)/b.var(ddof=1)
    pf = 2*min(stats.f.cdf(F,n-1,n-1), 1-stats.f.cdf(F,n-1,n-1))
    lev= stats.levene(a,b)
    print(f"\n=== FoolsGold, {label}, n={n} paired seeds ===")
    print(f"  defect present : {a.mean():.3f} +/- {a.std(ddof=1):.3f}")
    print(f"  corrected      : {b.mean():.3f} +/- {b.std(ddof=1):.3f}")
    print(f"  mean dCA       : {d.mean():+.3f}   95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")
    print(f"  paired t       : t={t:.2f}  p={p:.4f}   (t_crit={stats.t.ppf(0.975,n-1):.2f})")
    if w: print(f"  Wilcoxon       : W={w.statistic:.0f}  p={w.pvalue:.4f}")
    print(f"  Cohen's dz     : {d.mean()/d.std(ddof=1):.2f}")
    print(f"  seeds improved : {(d>0).sum()}/{n}")
    print(f"  VARIANCE  F={F:.2f} p={pf:.4f} | Levene p={lev.pvalue:.4f}")
