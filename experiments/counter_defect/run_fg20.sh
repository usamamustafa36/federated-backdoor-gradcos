#!/usr/bin/env bash
# 20 seeds per arm on FoolsGold. Settles two questions the 5-seed run left open:
#   (a) is the clean-accuracy gap real?      5 seeds gave +0.209, p=0.072
#   (b) does the fix reduce seed variance?   5 seeds gave sd 0.200 -> 0.087, p=0.136
# Only signal_subspace differs between arms.
cd /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
SP=/tmp/claude-1000/-home-ubuntu-Projects-THESIS-completed-usama-phd-paper08-tifs-direction-is-not-enough/b337ced6-2856-4f94-9f2c-fbfec7a4ab8f/scratchpad
for mode in full trainable; do
  python3 -m experiments.run_sweep --config configs/_ab_${mode}.yaml \
    --device cuda --rounds 15 --tag fg20${mode} \
    --defenses foolsgold --triggers fixed --ratios 0.2 --poisons 0.1 \
    --variants simple --partition dirichlet \
    --seeds 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 \
    >> $SP/fg20.log 2>&1
  echo "=== finished ${mode} ===" >> $SP/fg20.log
done
echo "FG20 COMPLETE" >> $SP/fg20.log
