#!/usr/bin/env python3
"""
windowing.py — Slice continuous sensor logs into fixed-length windows

Reads labeled CSV files from data/raw/sensor/, applies sliding window,
and saves windowed numpy arrays to data/processed/sensor/.

Usage:
    python windowing.py

Output:
    data/processed/sensor/X.npy  — shape (N, window_size, channels)
    data/processed/sensor/y.npy  — shape (N,) integer class labels
    data/processed/sensor/meta.json — class index mapping
"""

import numpy as np
import pandas as pd
import json
from pathlib import Path
import yaml

# Load training config
CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

WINDOW_SIZE  = cfg["data"]["window_size"]    # 20
STEP_SIZE    = cfg["data"]["step_size"]      # 5
CHANNELS     = cfg["data"]["channels"]       # 9
CHANNEL_COLS = cfg["data"]["channel_names"]
CLASS_NAMES  = cfg["classes"]
CLASS_MAP    = {name: i for i, name in enumerate(CLASS_NAMES)}

RAW_DIR  = Path(__file__).parent.parent.parent.parent / "data" / "raw"  / "sensor"
PROC_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"
PROC_DIR.mkdir(parents=True, exist_ok=True)


def load_session(csv_path: Path):
    """Load one labeled CSV session, return (data array, label string)."""
    df = pd.read_csv(csv_path)
    label = df["label"].iloc[0]

    # Handle missing/out-of-range values
    for col in CHANNEL_COLS:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].replace(-1, np.nan)
        # BUG WAS: fillna(..., inplace=True) — deprecated in pandas 2.0, broken in 3.0
        # FIX: use assignment form which works on all versions
        fill_val = df[col].max() if not df[col].isna().all() else 0.0
        df[col] = df[col].fillna(fill_val)

    return df[CHANNEL_COLS].values, label


def sliding_windows(data: np.ndarray, label_idx: int):
    """Slide window over a session, return list of (window_array, label) tuples."""
    windows = []
    n = len(data)
    for start in range(0, n - WINDOW_SIZE + 1, STEP_SIZE):
        w = data[start : start + WINDOW_SIZE]
        windows.append((w, label_idx))
    return windows


def main():
    all_windows = []
    all_labels  = []
    skipped     = 0

    for label_dir in sorted(RAW_DIR.iterdir()):
        if not label_dir.is_dir():
            continue
        label = label_dir.name
        if label not in CLASS_MAP:
            print(f"[Windowing] Skipping unknown label dir: {label}")
            continue
        label_idx = CLASS_MAP[label]

        for csv_file in sorted(label_dir.glob("*.csv")):
            try:
                data, lbl = load_session(csv_file)
                windows = sliding_windows(data, label_idx)
                for w, y in windows:
                    all_windows.append(w)
                    all_labels.append(y)
                print(f"  {csv_file.name}: {len(data)} samples → {len(windows)} windows (label={label})")
            except Exception as e:
                print(f"  SKIP {csv_file.name}: {e}")
                skipped += 1

    if not all_windows:
        print("[Windowing] No data found. Run collect_sensor_data.py first.")
        return

    X = np.array(all_windows, dtype=np.float32)
    y = np.array(all_labels,  dtype=np.int32)

    np.save(PROC_DIR / "X.npy", X)
    np.save(PROC_DIR / "y.npy", y)

    meta = {"class_map": CLASS_MAP, "window_size": WINDOW_SIZE,
            "step_size": STEP_SIZE, "channels": CHANNEL_COLS,
            "total_windows": len(X), "skipped_files": skipped}
    with open(PROC_DIR / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n[Windowing] Done: {X.shape} windows saved to {PROC_DIR}")
    unique, counts = np.unique(y, return_counts=True)
    for cls_idx, cnt in zip(unique, counts):
        print(f"  {CLASS_NAMES[cls_idx]:20s}: {cnt:5d} windows")


if __name__ == "__main__":
    main()
