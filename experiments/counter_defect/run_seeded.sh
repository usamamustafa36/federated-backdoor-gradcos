#!/usr/bin/env bash
# FoolsGold is bimodal across seeds by this project's own measurement (s.d. 0.489).
# A single run per arm cannot separate the defect's effect from that bimodality.
# Five seeds per arm, everything else identical, only signal_subspace varies.
cd /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
SP=/tmp/claude-1000/-home-ubuntu-Projects-THESIS-completed-usama-phd-paper08-tifs-direction-is-not-enough/b337ced6-2856-4f94-9f2c-fbfec7a4ab8f/scratchpad
for mode in full trainable; do
  python3 -m experiments.run_sweep --config configs/_ab_${mode}.yaml \
    --device cuda --rounds 15 --tag sd${mode} \
    --defenses foolsgold flame gradcos --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --partition dirichlet --seeds 42 43 44 45 46 >> $SP/seeded.log 2>&1
  echo "=== finished ${mode} ===" >> $SP/seeded.log
done
echo "SEEDED SWEEP COMPLETE" >> $SP/seeded.log
