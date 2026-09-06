# Counter-defect experiments (5-6 September 2026)

Scripts and raw logs behind the findings in `../../CONTRIBUTION.md`. Kept because
several of these results contradict claims made earlier in the same session, and
the logs are the record of which.

| file | what it establishes |
|---|---|
| `run_scaling.sh`, `scaling.log` | **Refutes** the prediction that the effect grows with batches/round. FoolsGold went +0.460 -> +0.085 -> -0.189 as the counter's norm share rose 80->96->99% |
| `run_seeded.sh`, `seeded.log` | 5-seed A/B. Nothing reaches p<0.05; FoolsGold attacked is +0.209, p=0.072 |
| `ab_full.log`, `ab_trainable.log` | first controlled A/B, single-seed. Showed +0.591 for FoolsGold -- an overestimate, see seeded.log |
| `fgmech.log` | the FoolsGold mechanism: identical inputs, both code paths, 8 clients zeroed vs 2 |
| `central.log`, `mlp.log`, `weights.log` | detector diagnosis. Centralized CNN+LSTM ~= federated, MLP ~= CNN+LSTM, and the four class-weighting schemes |
| `smoke2.log`, `integ.log` | 33/33 and 48/48 verification of the fix across all defenses |
| `run_fg20.sh`, `analyse_fg20.py` | **not yet run** -- 20 seeds, blocked on the GPU. This settles whether +0.209 is real |
| `external_krum.py` | **not yet run** -- ResNet-18/CIFAR-10 replication of yjlee22/byzantineFL's Krum, full vs parameters-only. Blocked on the CIFAR download |
