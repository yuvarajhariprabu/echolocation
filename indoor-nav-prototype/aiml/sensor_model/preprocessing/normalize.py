#!/usr/bin/env python3
"""
normalize.py — Per-Channel Min-Max Normalization

Fits normalization parameters on the training set and saves them to JSON.
These params MUST be copied into firmware normalize.cpp (CH_MIN/CH_MAX arrays).

Usage:
    python normalize.py              # fit on processed/sensor/X.npy, save params
    python normalize.py --apply      # also transform and save X_norm.npy
"""

import numpy as np
import json
import argparse
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

CHANNEL_NAMES = cfg["data"]["channel_names"]
PROC_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"
PARAMS_PATH = PROC_DIR / "normalization_params.json"


def fit_and_save(X: np.ndarray) -> dict:
    """Compute per-channel min/max across all windows and timesteps."""
    # X shape: (N, window_size, channels)
    X_flat = X.reshape(-1, X.shape[-1])  # (N*window_size, channels)

    ch_min = X_flat.min(axis=0).tolist()
    ch_max = X_flat.max(axis=0).tolist()

    params = {
        "channel_names": CHANNEL_NAMES,
        "ch_min": ch_min,
        "ch_max": ch_max,
    }

    with open(PARAMS_PATH, "w") as f:
        json.dump(params, f, indent=2)

    print(f"[Normalize] Params saved → {PARAMS_PATH}")
    print("\nCopy these into firmware/esp32_sensor_node/src/preprocessing/normalize.cpp:\n")
    print("static const float CH_MIN[SENSOR_CHANNELS] = {")
    for i, (name, v) in enumerate(zip(CHANNEL_NAMES, ch_min)):
        sep = "," if i < len(CHANNEL_NAMES) - 1 else ""
        print(f"    {v:.4f}f{sep}  // {name}")
    print("};\n")
    print("static const float CH_MAX[SENSOR_CHANNELS] = {")
    for i, (name, v) in enumerate(zip(CHANNEL_NAMES, ch_max)):
        sep = "," if i < len(CHANNEL_NAMES) - 1 else ""
        print(f"    {v:.4f}f{sep}  // {name}")
    print("};")

    return params


def apply_normalization(X: np.ndarray, params: dict) -> np.ndarray:
    ch_min = np.array(params["ch_min"], dtype=np.float32)
    ch_max = np.array(params["ch_max"], dtype=np.float32)
    ranges = ch_max - ch_min
    ranges[ranges < 1e-6] = 1.0  # avoid divide-by-zero for constant channels
    return np.clip((X - ch_min) / ranges, 0.0, 1.0).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Also normalize X.npy and save as X_norm.npy")
    args = parser.parse_args()

    X_path = PROC_DIR / "X.npy"
    if not X_path.exists():
        print(f"[Normalize] X.npy not found at {X_path}. Run windowing.py first.")
        return

    X = np.load(X_path)
    print(f"[Normalize] Loaded X: {X.shape}")

    params = fit_and_save(X)

    if args.apply:
        X_norm = apply_normalization(X, params)
        np.save(PROC_DIR / "X_norm.npy", X_norm)
        print(f"\n[Normalize] Normalized data saved → {PROC_DIR / 'X_norm.npy'}")


if __name__ == "__main__":
    main()
