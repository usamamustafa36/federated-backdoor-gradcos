"""Smoke test: load + preprocess + partition the dataset and print a summary.

Run from project root:  python -m experiments.smoke_data
"""
from src.config import load_config, set_seed
from src.data.preprocess import load_dataset
from src.data.partition import partition_data, partition_summary


def main():
    cfg = load_config()
    set_seed(cfg.seed)

    print(f"Loading {cfg.data.dataset} (label_mode={cfg.data.label_mode}) ...")
    ds = load_dataset(cfg)
    print(f"  x_train={ds.x_train.shape}  x_test={ds.x_test.shape}")
    print(f"  features={ds.num_features}  classes={ds.num_classes}")
    print(f"  benign_index={ds.benign_index}  benign_class='{ds.class_names[ds.benign_index]}'")
    print(f"  class_names={ds.class_names}")

    import numpy as np
    vals, counts = np.unique(ds.y_train, return_counts=True)
    print("  train class counts:")
    for v, c in zip(vals, counts):
        print(f"    {ds.class_names[v]:<22} {c}")

    print(f"\nPartitioning across {cfg.federated.num_clients} clients "
          f"({cfg.federated.partition}) ...")
    parts = partition_data(
        ds.y_train,
        cfg.federated.num_clients,
        cfg.federated.partition,
        cfg.federated.dirichlet_alpha,
        cfg.seed,
    )
    print(partition_summary(parts, ds.y_train, ds.num_classes))


if __name__ == "__main__":
    main()
