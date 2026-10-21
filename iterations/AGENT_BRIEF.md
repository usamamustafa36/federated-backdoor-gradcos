# Brief for every iteration agent

You are one iteration in a long chain (50+) of agents improving one research paper
until it is acceptable at a strong journal. You do one iteration, record it, and stop.
The next agent continues from what you leave.

Repo: /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
Branch: counter-defect-and-jisa-reformat (commit here; never push, never touch main).

## Read first (in order)
1. iterations/LEDGER.md: every previous iteration. The last entry's priorities are your
   starting point unless you find something more important.
2. RESUME_HERE.md, CONTRIBUTION.md, PUBLISHABILITY.md, REFRAME.md, QA_FINDINGS.md,
   SUBMISSION_STATUS.md: the state of the science and the known blockers.
3. paper/main.tex (+ numbers.tex, refs.bib, make_numbers.py, make_figs.py).

## What one iteration is
1. **Review.** Act as the harshest plausible reviewer at the target venue (currently Elsevier
   JISA, though you may argue for a stronger venue if the evidence supports it; the
   BatchNorm `num_batches_tracked` finding may be a top-venue result). Score 1-10 with a
   verdict (reject / major / minor / accept). List blockers ranked by how likely each is to
   cause rejection.
2. **Fix.** Take the highest-leverage blocker(s) you can make real progress on this
   iteration, and do the work: code, experiments, analysis, writing, figures, related work,
   proofs. Think beyond the current framing. A sharper claim, a new analytic result, a
   cleaner experiment, a stronger baseline, or a reorganised paper can be worth more than
   polishing.
3. **Verify.** Rebuild the PDF (`cd paper && make` or the Makefile target) and run
   `paper/tools/check_manuscript.py` if it exists. Fix whatever you broke.
4. **Record.** Append one entry to iterations/LEDGER.md in its format, then
   `git add` the files you changed and commit with a message saying what the iteration did.
   End the commit message with:
   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

## Hard rules
- **No fabrication, ever.** Every number in the paper comes from a result file through the
  generator (make_numbers.py / numbers.tex). Never type a result into the paper by hand.
  If a result is not measured yet, leave it \PENDING and say so. Never invent citations:
  verify a reference exists (web search) before adding it to refs.bib.
- Report negative results honestly. If an experiment refutes a claim, the claim goes.
- **Shared machine.** Other people's jobs run here (e.g. stage_sensing.py, isf_build.py,
  firefox, claude). Never kill a process you did not start. Keep CPU use to about 12 of the
  20 cores.
- **GPU available again (user reset CUDA at 13:24, 2026-10-21).** Use `--device cuda` for
  campaigns. Before launching, check `python3 -c "import torch; torch.ones(1,device='cuda')"`.
  There is one RTX 4060 (8 GB): run one GPU campaign at a time, with as many parallel lanes
  as fit in memory. If CUDA errors with "unknown error", it is in the zombie state again, and
  only the user can fix it with sudo. Note it in the ledger and fall back to CPU (at most ~12
  cores). Make campaigns resumable so a CUDA death costs only the current cell. With the GPU,
  prefer full-scale experiments (full rounds, more seeds) over the earlier CPU reductions.
- **GPU state at 17:50, 2026-10-21 (after a reboot killed all jobs):** P3 relaunched on CUDA,
  4 lanes, under `systemd-inhibit` (log results/postfix_p3/campaign.log). 4 lanes fill the
  8 GB card (~2.5 GB peak each), so a 5th GPU process OOMs. Do not add GPU jobs while P3
  runs; queue them after it, or run small probes on CPU. The horizon probe (iteration 7)
  OOMed on CUDA and now runs on CPU (`HORIZON_DEVICE=cpu`, results/calib_iter7/horizon.log).
  Always wrap long jobs in `systemd-inhibit --what=sleep:idle:handle-lid-switch --mode=block`.
- **Iteration 9 correction:** 4 lanes did NOT fit: attacked cells OOMed in the BSR eval
  (4096-row chunk = 1.66 GiB cuDNN LSTM allocation) and failed silently (run_sweep isolates
  errors, rc=0). Fixed at 18:02 (chunk 1024, expandable_segments). Always `grep -c ERROR` the
  per-job logs before trusting "done(rc=0)". A gap-filler (experiments/postfix/fill_p3_gaps.sh)
  re-runs the resumable driver after the first pass. run_sweep now fsyncs results and ignores
  0-byte JSONs (the 17:45 reboot left two).
- **Long jobs:** launch with nohup into a log under experiments/ or results/, record PID, log
  path and ETA in the ledger, and do not wait hours for them. The next agent harvests them.
  Make jobs resumable (skip completed cells). Before launching, check that no earlier
  iteration's job is still running the same thing (`ps aux | grep run_sweep`).
- Keep a .bak copy before restructuring main.tex substantially.
- Don't delete results or earlier agents' work. Superseded material moves to a `_`-prefixed
  folder.
- Finish within a reasonable session: one solid improvement fully done beats five half-done.

## When to declare the paper finished
Only when your honest review scores it accept or minor revision with no open blocker,
every number is generated, the PDF builds clean, and you would bet on it surviving three
hostile reviewers. Say so explicitly in your ledger entry with "VERDICT: READY". Never
inflate the score to end the chain. Overrating is the worst failure here.

## Your final message
Reply in under 200 words: iteration number, score before and after, what changed, jobs left
running, top priority for the next agent, and whether VERDICT: READY.
