#!/usr/bin/env bash
# Does the defect's effect grow with batches per local round, as the scaling law
# L*B^2/(L*B^2+T^2) predicts? Same defenses, same rounds, same clients; only the
# rows per client (hence B) and the signal_subspace flag vary.
cd /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
SP=/tmp/claude-1000/-home-ubuntu-Projects-THESIS-completed-usama-phd-paper08-tifs-direction-is-not-enough/b337ced6-2856-4f94-9f2c-fbfec7a4ab8f/scratchpad
for tag in b16 b39 b78; do
  for mode in full trainable; do
    python3 -m experiments.run_sweep --config configs/_sc_${tag}_${mode}.yaml \
      --device cuda --rounds 15 --tag sc${tag}${mode} \
      --defenses foolsgold flame gradcos --triggers fixed --ratios 0.2 --poisons 0.1 \
      --variants simple --partition dirichlet >> $SP/scaling.log 2>&1
    echo "=== finished ${tag} ${mode} ===" >> $SP/scaling.log
  done
done
echo "SCALING SWEEP COMPLETE" >> $SP/scaling.log
