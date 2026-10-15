#!/usr/bin/env python3
"""
train.py — 1D CNN Training Script

Loads augmented sensor windows, trains the model with class-weighted loss,
saves best checkpoint and training history.

Usage:
    python train.py                     # train on X_aug.npy / y_aug.npy
    python train.py --no-augment        # train on X_norm.npy / y.npy

Requirements:
    pip install tensorflow numpy scikit-learn pyyaml
"""

import argparse
import json
import numpy as np
import yaml
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf

from model_1dcnn import build_model

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

PROC_DIR   = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"
CKPT_DIR   = Path(__file__).parent.parent / "model" / "checkpoints"
CKPT_DIR.mkdir(parents=True, exist_ok=True)

CLASS_NAMES = cfg["classes"]
EPOCHS      = cfg["training"]["epochs"]
BATCH_SIZE  = cfg["training"]["batch_size"]
LR          = cfg["training"]["learning_rate"]
VAL_SPLIT   = cfg["training"]["val_split"]
PATIENCE    = cfg["training"]["early_stopping_patience"]


def load_data(use_augmented: bool):
    if use_augmented and (PROC_DIR / "X_aug.npy").exists():
        X = np.load(PROC_DIR / "X_aug.npy")
        y = np.load(PROC_DIR / "y_aug.npy")
        print(f"[Train] Loaded augmented data: {X.shape}")
    else:
        X = np.load(PROC_DIR / "X_norm.npy")
        y = np.load(PROC_DIR / "y.npy")
        print(f"[Train] Loaded normalized data: {X.shape}")
    return X, y


def make_class_weights(y):
    classes = np.unique(y)
    weights = compute_class_weight("balanced", classes=classes, y=y)
    return dict(zip(classes.tolist(), weights.tolist()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-augment", action="store_true")
    args = parser.parse_args()

    # GPU memory growth
    for gpu in tf.config.list_physical_devices("GPU"):
        tf.config.experimental.set_memory_growth(gpu, True)

    X, y = load_data(not args.no_augment)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=VAL_SPLIT, random_state=42, stratify=y
    )
    print(f"[Train] Train: {X_train.shape}, Val: {X_val.shape}")

    class_weights = make_class_weights(y_train)
    print(f"[Train] Class weights: {class_weights}")

    model = build_model()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LR),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    model.summary()

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(CKPT_DIR / "best_model.h5"),
            monitor="val_accuracy", save_best_only=True, verbose=1
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=PATIENCE,
            restore_best_weights=True, verbose=1
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=5, verbose=1
        ),
        tf.keras.callbacks.TensorBoard(
            log_dir=str(Path(__file__).parent.parent / "model" / "logs")
        ),
    ]

    history = model.fit(
        X_train, y_train,
        epochs=EPOCHS, batch_size=BATCH_SIZE,
        validation_data=(X_val, y_val),
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )

    # Final evaluation
    loss, acc = model.evaluate(X_val, y_val, verbose=0)
    print(f"\n[Train] Final val accuracy: {acc:.4f}  loss: {loss:.4f}")

    # Save history
    hist_path = CKPT_DIR / "history.json"
    with open(hist_path, "w") as f:
        json.dump({k: [float(v) for v in vals] for k, vals in history.history.items()}, f, indent=2)
    print(f"[Train] History saved → {hist_path}")
    print(f"[Train] Best model → {CKPT_DIR / 'best_model.h5'}")
    print("\nNext step: python aiml/sensor_model/export/quantize_int8.py")


if __name__ == "__main__":
    main()
