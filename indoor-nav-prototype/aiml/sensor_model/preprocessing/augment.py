#!/usr/bin/env python3
"""
augment.py — Sensor Data Augmentation

Sensor time-series data is expensive to collect at scale.
This script synthesizes additional training samples via:
  1. Gaussian noise injection     — simulates sensor measurement noise
  2. Time warping                 — simulates variation in movement speed
  3. Channel-wise sensor dropout  — simulates sensor malfunction or occlusion
  4. Amplitude scaling            — simulates varying distances/speeds

Usage:
    python augment.py --multiplier 3    # generate 3x the existing dataset

Output: appends augmented samples to X_norm.npy and y.npy
"""

import numpy as np
import argparse
from pathlib import Path

PROC_DIR = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"


def add_noise(X: np.ndarray, std: float = 0.02) -> np.ndarray:
    """Add Gaussian noise (std as fraction of normalized range [0,1])."""
    return np.clip(X + np.random.normal(0, std, X.shape).astype(np.float32), 0.0, 1.0)


def time_warp(X: np.ndarray) -> np.ndarray:
    """
    Resample each window along the time axis with a random smooth warp.
    Simulates walking faster/slower through the same scenario.
    """
    N, T, C = X.shape
    result = np.empty_like(X)
    for i in range(N):
        # Random warp: slight compression/expansion of time axis
        orig_t  = np.linspace(0, 1, T)
        warp_t  = np.sort(orig_t + np.random.uniform(-0.05, 0.05, T))
        warp_t  = np.clip(warp_t, 0, 1)
        for c in range(C):
            result[i, :, c] = np.interp(orig_t, warp_t, X[i, :, c])
    return result


def channel_dropout(X: np.ndarray, dropout_prob: float = 0.15) -> np.ndarray:
    """
    Randomly zero out entire channels for individual samples.
    Simulates a sensor failing or being occluded.
    Channels 0-2 (ultrasonics) and 4-8 (IMU) are candidates.
    """
    result = X.copy()
    N, T, C = X.shape
    for i in range(N):
        for c in range(C):
            if np.random.random() < dropout_prob:
                result[i, :, c] = 1.0  # encode as "max range / no reading"
    return result


def amplitude_scale(X: np.ndarray, scale_range: tuple = (0.85, 1.15)) -> np.ndarray:
    """Per-channel random amplitude scaling."""
    N, T, C = X.shape
    scales = np.random.uniform(*scale_range, size=(N, 1, C)).astype(np.float32)
    return np.clip(X * scales, 0.0, 1.0)


def augment(X: np.ndarray, y: np.ndarray, multiplier: int):
    """Generate `multiplier` additional copies of (X, y) with mixed augmentations."""
    aug_X_list = [X]
    aug_y_list = [y]

    for _ in range(multiplier):
        Xa = X.copy()
        # Apply random combination of augmentations
        if np.random.random() > 0.3: Xa = add_noise(Xa)
        if np.random.random() > 0.5: Xa = time_warp(Xa)
        if np.random.random() > 0.4: Xa = channel_dropout(Xa)
        if np.random.random() > 0.4: Xa = amplitude_scale(Xa)
        aug_X_list.append(Xa)
        aug_y_list.append(y)

    return np.concatenate(aug_X_list, axis=0), np.concatenate(aug_y_list, axis=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--multiplier", type=int, default=3,
                        help="How many synthetic copies to generate (default: 3)")
    args = parser.parse_args()

    X = np.load(PROC_DIR / "X_norm.npy")
    y = np.load(PROC_DIR / "y.npy")
    print(f"[Augment] Input: {X.shape}, classes: {np.bincount(y)}")

    X_aug, y_aug = augment(X, y, args.multiplier)

    # Shuffle
    idx = np.random.permutation(len(X_aug))
    X_aug, y_aug = X_aug[idx], y_aug[idx]

    np.save(PROC_DIR / "X_aug.npy", X_aug)
    np.save(PROC_DIR / "y_aug.npy", y_aug)
    print(f"[Augment] Output: {X_aug.shape}, classes: {np.bincount(y_aug)}")
    print(f"[Augment] Saved → {PROC_DIR / 'X_aug.npy'}")


if __name__ == "__main__":
    main()
