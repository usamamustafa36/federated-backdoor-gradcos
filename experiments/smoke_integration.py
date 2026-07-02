"""Tiny end-to-end smoke: attack + defense + BSR/DR in one short run.

Shrinks data/clients/rounds so it finishes fast on CPU. Proves the whole
pipeline wires together; NOT a real result.

    python -m experiments.smoke_integration
    python -m experiments.smoke_integration gradcos
"""
import sys

from src.config import load_config, resolve_device, set_seed
from src.data.preprocess import load_dataset
from src.attacks import make_attack
from src.fl.build import build_clients, build_strategy
from src.fl.engine import FederatedEngine


def main():
    defense = sys.argv[1] if len(sys.argv) > 1 else "gradcos"
    cfg = load_config()
    # shrink everything for a quick check
    cfg.data.max_train_rows = 8000
    cfg.data.max_test_rows = 4000
    cfg.federated.num_clients = 6
    cfg.federated.clients_per_round = 6
    cfg.federated.rounds = 2
    cfg.attack.enabled = True
    cfg.attack.malicious_ratio = 0.34          # 2 of 6
    cfg.attack.poison_rate = 0.2
    cfg.attack.trigger_type = "fixed"
    cfg.defense.name = defense
    set_seed(cfg.seed)

    device = resolve_device(cfg.device)
    ds = load_dataset(cfg)
    attack_factory, backdoor_eval = make_attack(cfg, ds, device)
    clients = build_clients(cfg, ds, attack_factory)
    strategy = build_strategy(cfg, ds, device)
    print(f"defense={defense} device={device} clients={len(clients)} "
          f"malicious={[c.cid for c in clients if c.malicious]}")
    engine = FederatedEngine(cfg, ds, clients, strategy, device, backdoor_eval=backdoor_eval)
    engine.run(verbose=True)
    print("integration OK")


if __name__ == "__main__":
    main()
