#!/bin/bash
# iteration 5: campaign-scale replay of P1/P2 cells (Dirichlet, s42) with the round-1
# aliasing fix ON (configs/_r1fix_*.yaml), to compare with the campaign's own cells.
# FedAvg clean (fix-induced trajectory change alone; arms identical so one arm),
# FoolsGold clean both arms, FoolsGold attacked (E_m=5) both arms. 2 threads, serial.
cd /home/ubuntu/Projects/THESIS/completed/usama-phd/paper08-tifs-direction-is-not-enough
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 CUDA_VISIBLE_DEVICES=""
run() { nice -n 5 python3 -m experiments.run_sweep --config configs/_r1fix_$1.yaml --device cpu --rounds 15 \
    --tag r1fix$1_dirichlet --partition dirichlet --defenses $2 --triggers fixed --ratios 0.2 \
    --poisons 0.1 --variants simple --seeds 42 "${@:3}"; }
run full fedavg --skip-attacked
run full foolsgold --skip-attacked
run trainable foolsgold --skip-attacked
run full foolsgold --skip-clean --mal-local-epochs 5
run trainable foolsgold --skip-clean --mal-local-epochs 5
echo REPLAY_DONE
