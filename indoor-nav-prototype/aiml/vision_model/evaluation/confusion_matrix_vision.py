#!/usr/bin/env python3
"""
confusion_matrix_vision.py — Evaluate Vision Model on Test Set

Loads FOMO/MobileNet model and runs evaluation on test images in data/raw/vision/.

Usage:
    python confusion_matrix_vision.py
"""

import numpy as np
import yaml
import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns

CLASS_DEF_PATH = Path(__file__).parent.parent.parent / "shared" / "class_definitions.yaml"
with open(CLASS_DEF_PATH) as f:
    defs = yaml.safe_load(f)
CLASS_NAMES = [c["name"] for c in defs["vision_classes"]]


def evaluate_from_labels(pred_dir: Path):
    """
    Load predictions from pred_dir/predictions.json (output from Edge Impulse
    classification testing or a local eval run) and plot confusion matrix.

    predictions.json format:
      [{"true": "chair", "pred": "chair", "conf": 0.89}, ...]
    """
    pred_file = pred_dir / "predictions.json"
    if not pred_file.exists():
        print(f"[EvalVision] {pred_file} not found.")
        print("  Run your Edge Impulse project's Test set evaluation first,")
        print("  then export the results as predictions.json.")
        return

    with open(pred_file) as f:
        preds = json.load(f)

    y_true = [CLASS_NAMES.index(p["true"]) if p["true"] in CLASS_NAMES else len(CLASS_NAMES)-1
              for p in preds]
    y_pred = [CLASS_NAMES.index(p["pred"]) if p["pred"] in CLASS_NAMES else len(CLASS_NAMES)-1
              for p in preds]

    from sklearn.metrics import classification_report, confusion_matrix
    print("\n=== Vision Model — Classification Report ===")
    print(classification_report(y_true, y_pred, target_names=CLASS_NAMES))

    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Greens",
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES, ax=ax)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Vision Model (FOMO) — Confusion Matrix")
    plt.tight_layout()
    out = pred_dir / "confusion_matrix_vision.png"
    plt.savefig(str(out), dpi=150)
    print(f"\n[EvalVision] Plot saved → {out}")


def main():
    pred_dir = Path(__file__).parent
    evaluate_from_labels(pred_dir)


if __name__ == "__main__":
    main()
