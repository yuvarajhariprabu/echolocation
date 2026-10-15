#!/usr/bin/env python3
"""
evaluate.py — Model Evaluation: Confusion Matrix + Per-Class Metrics

Usage:
    python evaluate.py

Requires best_model.h5 to exist (run train.py first).
"""

import numpy as np
import json
from pathlib import Path
import yaml
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

CLASS_NAMES = cfg["classes"]
PROC_DIR    = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"
CKPT_DIR    = Path(__file__).parent.parent / "model" / "checkpoints"


def main():
    model = tf.keras.models.load_model(str(CKPT_DIR / "best_model.h5"))
    print("[Eval] Model loaded")

    X = np.load(PROC_DIR / "X_norm.npy")
    y = np.load(PROC_DIR / "y.npy")

    y_pred_prob = model.predict(X, verbose=0)
    y_pred = np.argmax(y_pred_prob, axis=1)

    print("\n=== Classification Report ===")
    print(classification_report(y, y_pred, target_names=CLASS_NAMES))

    cm = confusion_matrix(y, y_pred)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Sensor Model — Confusion Matrix")
    plt.tight_layout()

    out = CKPT_DIR / "confusion_matrix.png"
    plt.savefig(str(out), dpi=150)
    print(f"\n[Eval] Confusion matrix saved → {out}")

    # Per-class accuracy for model_registry.md
    per_class_acc = cm.diagonal() / cm.sum(axis=1)
    for name, acc in zip(CLASS_NAMES, per_class_acc):
        print(f"  {name:20s}: {acc:.3f}")


if __name__ == "__main__":
    main()
