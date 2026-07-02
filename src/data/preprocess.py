"""CICIoT2023 loading & preprocessing.

Turns the raw parquet files into clean, scaled numpy arrays plus the metadata
(feature names, class names, benign index, fitted scaler) that the rest of the
pipeline needs. Designed to be dataset-agnostic at the call site so FLNET2023
can be plugged in later behind the same return contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from ..config import PROJECT_ROOT

# The 3 label columns shipped in the HuggingFace mirror; everything else is a
# numeric feature.
LABEL_COLUMNS = ["label", "Label", "attack_class"]

# Which raw column holds the target for each label_mode, and what the benign
# category is called inside that column.
LABEL_MODE = {
    "binary": ("label", 0),
    "grouped": ("attack_class", "Benign"),
    "full": ("Label", "BenignTraffic"),
}


@dataclass
class Dataset:
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    feature_names: list[str]
    class_names: list[str]   # index i -> class_names[i]
    benign_index: int
    scaler: object

    @property
    def num_features(self) -> int:
        return self.x_train.shape[1]

    @property
    def num_classes(self) -> int:
        return len(self.class_names)


def _target_counts(counts: dict, max_rows: int | None, min_per_class: int) -> dict:
    """How many rows to keep per class: a floor per class, then the remaining
    budget distributed proportionally to leftover class frequency."""
    if max_rows is None or sum(counts.values()) <= max_rows:
        return dict(counts)

    keep = {k: min(min_per_class, counts[k]) for k in counts}
    remaining = max_rows - sum(keep.values())
    if remaining > 0:
        leftover = {k: counts[k] - keep[k] for k in counts}
        total_leftover = sum(leftover.values())
        if total_leftover > 0:
            for k in counts:
                extra = int(round(remaining * leftover[k] / total_leftover))
                keep[k] = min(counts[k], keep[k] + extra)
    return keep


def _streaming_subsample(
    path: Path,
    feature_names: list[str],
    label_col: str,
    max_rows: int | None,
    min_per_class: int,
    seed: int,
    batch_size: int = 262_144,
) -> pd.DataFrame:
    """Stratified subsample read straight from parquet in batches.

    The full CICIoT2023 train split is 38.5M rows; materialising it in pandas
    blows up memory. Instead we make one cheap pass over just the label column
    to get class counts, then a second batched pass keeping each class with
    probability target/count (rare classes -> prob 1.0, i.e. fully kept).
    """
    pf = pq.ParquetFile(path)

    # Pass 1: class counts from the label column only.
    counts: dict = {}
    for batch in pf.iter_batches(columns=[label_col], batch_size=batch_size):
        vc = batch.column(0).to_pandas().value_counts()
        for k, v in vc.items():
            counts[k] = counts.get(k, 0) + int(v)

    targets = _target_counts(counts, max_rows, min_per_class)
    probs = {k: (1.0 if counts[k] == 0 else min(1.0, targets[k] / counts[k])) for k in counts}

    # Pass 2: sample rows class-by-class with a per-class cap.
    rng = np.random.RandomState(seed)
    kept_so_far = {k: 0 for k in counts}
    cols = feature_names + [label_col]
    chunks: list[pd.DataFrame] = []
    for batch in pf.iter_batches(columns=cols, batch_size=batch_size):
        bdf = batch.to_pandas()
        masks = []
        labels = bdf[label_col].to_numpy()
        draw = rng.random(len(bdf))
        for k in counts:
            cls_mask = labels == k
            if not cls_mask.any():
                continue
            room = targets[k] - kept_so_far[k]
            if room <= 0:
                continue
            sel = cls_mask & (draw < probs[k])
            n_sel = int(sel.sum())
            if n_sel > room:  # don't exceed the per-class target
                sel_idx = np.where(sel)[0]
                drop = rng.choice(sel_idx, size=n_sel - room, replace=False)
                sel[drop] = False
                n_sel = room
            kept_so_far[k] += n_sel
            masks.append(sel)
        if masks:
            keep_mask = np.logical_or.reduce(masks)
            if keep_mask.any():
                chunks.append(bdf.loc[keep_mask])

    out = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=cols)
    return out.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def _clean_features(x: pd.DataFrame) -> pd.DataFrame:
    """Replace inf, fill NaN with column medians, keep numeric only."""
    x = x.replace([np.inf, -np.inf], np.nan)
    x = x.fillna(x.median(numeric_only=True))
    # Any column still all-NaN (no median) -> 0.
    x = x.fillna(0.0)
    return x


def load_ciciot2023(cfg) -> Dataset:
    """Load and preprocess CICIoT2023 according to ``cfg.data``."""
    dcfg = cfg.data
    seed = cfg.seed
    root = Path(dcfg.root)
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    label_col, benign_value = LABEL_MODE[dcfg.label_mode]

    # Feature names come from the parquet schema (cheap; no data read).
    schema_names = pq.ParquetFile(root / dcfg.train_file).schema.names
    feature_names = [c for c in schema_names if c not in LABEL_COLUMNS]

    train_df = _streaming_subsample(
        root / dcfg.train_file, feature_names, label_col,
        dcfg.max_train_rows, dcfg.min_rows_per_class, seed,
    )
    test_df = _streaming_subsample(
        root / dcfg.test_file, feature_names, label_col,
        dcfg.max_test_rows, dcfg.min_rows_per_class, seed + 1,
    )

    x_train = _clean_features(train_df[feature_names]).to_numpy(dtype=np.float32)
    x_test = _clean_features(test_df[feature_names]).to_numpy(dtype=np.float32)

    # Encode labels. Build the class list from the TRAIN set so indices are
    # stable; benign is forced to a known index.
    raw_train = train_df[label_col].to_numpy()
    raw_test = test_df[label_col].to_numpy()
    class_names = sorted({*raw_train.tolist()}, key=lambda v: (v != benign_value, str(v)))
    # benign first -> index 0 by construction above
    class_to_idx = {c: i for i, c in enumerate(class_names)}
    benign_index = class_to_idx[benign_value]

    def encode(arr):
        # Unseen test classes (shouldn't happen with stratified split) -> -1,
        # dropped below.
        return np.array([class_to_idx.get(v, -1) for v in arr], dtype=np.int64)

    y_train = encode(raw_train)
    y_test = encode(raw_test)
    train_mask = y_train >= 0
    test_mask = y_test >= 0
    x_train, y_train = x_train[train_mask], y_train[train_mask]
    x_test, y_test = x_test[test_mask], y_test[test_mask]

    # Scale features (fit on train only).
    scaler = _make_scaler(dcfg.scaler)
    if scaler is not None:
        x_train = scaler.fit_transform(x_train).astype(np.float32)
        x_test = scaler.transform(x_test).astype(np.float32)

    return Dataset(
        x_train=x_train,
        y_train=y_train,
        x_test=x_test,
        y_test=y_test,
        feature_names=feature_names,
        class_names=[str(c) for c in class_names],
        benign_index=benign_index,
        scaler=scaler,
    )


def _make_scaler(kind: str):
    if kind == "standard":
        from sklearn.preprocessing import StandardScaler

        return StandardScaler()
    if kind == "minmax":
        from sklearn.preprocessing import MinMaxScaler

        return MinMaxScaler()
    if kind in (None, "none"):
        return None
    raise ValueError(f"unknown scaler: {kind}")


# ----------------------------- FLNET2023 -----------------------------------
# FLNET2023 (Sarhan/NMSU, CORE-emulated GEANT-2012 topology) ships per-client
# CSVs extracted with CICFlowMeter, organised by attack category:
#   <root>/<Category>/CSV/Dataset-*.csv   where Category in
#   {DDoS, DoS, Infiltration, Web, Normal}  (Normal = benign).
# The exact CICFlowMeter column set varies by version, so this loader is
# SCHEMA-ADAPTIVE: it labels each row by its category folder and auto-selects
# numeric feature columns, dropping flow identifiers. Verify FLNET_ID_COLUMNS
# against a real header once the data is downloaded.

# Folder name (lower-cased) -> class label. "normal"/"benign" -> benign class.
FLNET_BENIGN_NAMES = {"normal", "benign", "normaltraffic"}

# Identifier / non-feature columns to drop (CICFlowMeter conventions; matched
# case-insensitively, spaces/underscores ignored).
FLNET_ID_COLUMNS = {
    "flowid", "srcip", "dstip", "sourceip", "destinationip", "srcport",
    "dstport", "sourceport", "destinationport", "protocol", "timestamp",
    "label", "attackcategory", "attack", "class",
}


def _norm_col(c: str) -> str:
    return str(c).strip().lower().replace(" ", "").replace("_", "")


def load_flnet2023(cfg) -> Dataset:
    """Load and preprocess FLNET2023 from per-category CICFlowMeter CSVs.

    Walks <root>/<Category>/**/*.csv, labels rows by their top-level category
    folder, auto-discovers numeric feature columns, cleans, stratified-subsamples
    to cfg.data.max_*_rows, and makes a stratified train/test split.
    """
    import glob

    dcfg = cfg.data
    seed = cfg.seed
    root = Path(dcfg.root)
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    if not root.exists():
        raise FileNotFoundError(
            f"FLNET2023 root '{root}' not found. Download the dataset CSVs from the "
            f"project SharePoint and place the category folders (DDoS/ DoS/ "
            f"Infiltration/ Web/ Normal/) under {root}."
        )

    # Discover category folders (top-level dirs that contain CSVs anywhere below).
    frames = []
    for cat_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        csvs = glob.glob(str(cat_dir / "**" / "*.csv"), recursive=True)
        if not csvs:
            continue
        category = cat_dir.name
        for fp in csvs:
            try:
                df = pd.read_csv(fp, low_memory=False)
            except Exception:
                continue
            if df.empty:
                continue
            df["__category__"] = category
            frames.append(df)
    if not frames:
        raise FileNotFoundError(f"no CSVs found under {root}/<Category>/...")

    data = pd.concat(frames, ignore_index=True)
    raw_labels = data["__category__"].to_numpy()

    # Feature columns: numeric, excluding identifiers and the synthetic label col.
    feature_names = []
    for c in data.columns:
        if c == "__category__":
            continue
        if _norm_col(c) in FLNET_ID_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(data[c]):
            feature_names.append(c)
    if not feature_names:
        raise ValueError("FLNET2023: no numeric feature columns discovered")

    x_all = _clean_features(data[feature_names]).to_numpy(dtype=np.float32)

    # Encode labels; benign forced to index 0.
    def is_benign(v):
        return _norm_col(v) in FLNET_BENIGN_NAMES
    cats = sorted(set(raw_labels.tolist()), key=lambda v: (not is_benign(v), str(v)))
    benign_value = next((c for c in cats if is_benign(c)), cats[0])
    class_to_idx = {c: i for i, c in enumerate(cats)}
    benign_index = class_to_idx[benign_value]
    y_all = np.array([class_to_idx[v] for v in raw_labels], dtype=np.int64)

    # Stratified train/test split, then per-class subsample to the row budgets.
    rng = np.random.RandomState(seed)
    test_frac = float(getattr(dcfg, "test_size", 0.2))
    tr_idx, te_idx = [], []
    for c in range(len(cats)):
        idx = np.where(y_all == c)[0]
        rng.shuffle(idx)
        cut = int(len(idx) * (1.0 - test_frac))
        tr_idx.append(idx[:cut]); te_idx.append(idx[cut:])
    tr_idx = np.concatenate(tr_idx); te_idx = np.concatenate(te_idx)

    def subsample(idx, budget):
        if budget is None or len(idx) <= budget:
            return idx
        return rng.choice(idx, size=budget, replace=False)
    tr_idx = subsample(tr_idx, dcfg.max_train_rows)
    te_idx = subsample(te_idx, dcfg.max_test_rows)

    x_train, y_train = x_all[tr_idx], y_all[tr_idx]
    x_test, y_test = x_all[te_idx], y_all[te_idx]

    scaler = _make_scaler(dcfg.scaler)
    if scaler is not None:
        x_train = scaler.fit_transform(x_train).astype(np.float32)
        x_test = scaler.transform(x_test).astype(np.float32)

    return Dataset(
        x_train=x_train,
        y_train=y_train,
        x_test=x_test,
        y_test=y_test,
        feature_names=feature_names,
        class_names=[str(c) for c in cats],
        benign_index=benign_index,
        scaler=scaler,
    )


def load_dataset(cfg) -> Dataset:
    """Dispatch on cfg.data.dataset."""
    name = cfg.data.dataset
    if name == "ciciot2023":
        return load_ciciot2023(cfg)
    if name == "flnet2023":
        return load_flnet2023(cfg)
    raise NotImplementedError(f"dataset '{name}' not wired up yet (have: ciciot2023, flnet2023)")
