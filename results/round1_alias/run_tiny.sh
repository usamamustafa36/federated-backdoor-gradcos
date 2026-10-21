#!/bin/bash
# iteration 5: serial queue, 2 threads. clean bug-vs-fix on 4 rules x 2 arms x 2 seeds,
# then attacked (E_m=5) for fedavg + foolsgold.
cd /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=""
for mode in trainable full; do
  nice -n 5 python3 -m experiments.round1_alias.check_alias outcome --modes $mode --defenses foolsgold fedavg fltrust flame --attacks 0 --seeds 42 43 --name clean_$mode
done
for mode in trainable full; do
  nice -n 5 python3 -m experiments.round1_alias.check_alias outcome --modes $mode --defenses fedavg foolsgold --attacks 1 --seeds 42 43 --name atk_$mode
done
