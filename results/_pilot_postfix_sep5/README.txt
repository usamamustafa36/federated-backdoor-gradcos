Post-fix PILOT runs of 5 September 2026 (after the num_batches_tracked fix).
Valid code path, but reduced/heterogeneous scales (5-15 rounds, 40k-200k rows,
1-5 seeds) and run on the GPU. They are the source of the numbers quoted in
CONTRIBUTION.md / experiments/counter_defect/*.log. Moved here (iteration 1,
2026-10-21) so the paper generator never mixes them with the main campaigns:
  ab*    single-seed full-vs-trainable A/B          (_ab_{full,trainable}.yaml)
  sd*    5-seed full-vs-trainable A/B, Dirichlet    (seeded.log)
  scb*   batches-per-round scaling, B=16/39/78       (scaling.log)
  integ* 48-cell integration check of every defense (integ.log)
The '_' prefix keeps them out of aggregate_multiseed.py / load_results; it does
NOT mean they are void. The pre-fix runs are in ../_pre_counterfix/.
