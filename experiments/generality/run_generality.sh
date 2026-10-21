#!/bin/bash
# Iteration 19: CPU generality campaign (ResNet-20 / CIFAR-10). Resumable: each
# job skips if its JSON exists and resumes from its per-round checkpoint.
# 6 lanes x 2 threads = 12 cores. Log: results/generality_cifar/campaign.log
cd "$(dirname "$0")/../.."
JOBS=experiments/generality/jobs.txt
: > "$JOBS"
for s in 0 1 2; do for p in dirichlet iid; do echo "fedavg $p $s" >> "$JOBS"; done; done
for s in 0 1 2; do for a in fltrust_full fltrust_trainable; do echo "$a dirichlet $s" >> "$JOBS"; done; done
for s in 0 1 2; do for a in mkrum_full mkrum_trainable; do echo "$a dirichlet $s" >> "$JOBS"; done; done
mkdir -p results/generality_cifar/logs
cat "$JOBS" | xargs -P 6 -L 1 bash -c 'python3 experiments/generality/cifar_resnet20.py --agg $0 --partition $1 --seed $2 --rounds 20 --n-train 10000 --threads 2 > results/generality_cifar/logs/$0_$1_s$2.log 2>&1; echo "$(date +%T) done $0 $1 $2 rc=$?"'
echo "$(date +%T) GENERALITY COMPLETE"
