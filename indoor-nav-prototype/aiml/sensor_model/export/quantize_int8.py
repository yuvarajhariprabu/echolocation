#!/usr/bin/env python3
"""
quantize_int8.py — Post-Training INT8 Quantization

Converts best_model.h5 → model.tflite with INT8 quantization.
Uses a representative dataset (real sensor windows) to calibrate scale factors.

Usage:
    python quantize_int8.py

Output:
    model.tflite  (in this directory)
    Size target: < 100KB for ESP32-S3 flash
"""

import numpy as np
import tensorflow as tf
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

REP_SAMPLES = cfg["export"]["representative_samples"]
PROC_DIR    = Path(__file__).parent.parent.parent.parent / "data" / "processed" / "sensor"
CKPT_DIR    = Path(__file__).parent.parent / "model" / "checkpoints"
OUT_DIR     = Path(__file__).parent
TFLITE_PATH = OUT_DIR / "model.tflite"


def representative_dataset():
    """Yields batches of real sensor windows for INT8 calibration."""
    X = np.load(PROC_DIR / "X_norm.npy")
    indices = np.random.choice(len(X), size=min(REP_SAMPLES, len(X)), replace=False)
    for i in indices:
        sample = X[i:i+1].astype(np.float32)
        yield [sample]


def main():
    model = tf.keras.models.load_model(str(CKPT_DIR / "best_model.h5"))
    print(f"[Quantize] Loaded model from {CKPT_DIR / 'best_model.h5'}")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type  = tf.int8   # or tf.float32 if firmware uses float input
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()

    with open(TFLITE_PATH, "wb") as f:
        f.write(tflite_model)

    size_kb = len(tflite_model) / 1024
    print(f"[Quantize] Saved: {TFLITE_PATH}  ({size_kb:.1f} KB)")
    if size_kb > 100:
        print("[Quantize] WARNING: Model > 100KB — consider reducing filters or window size")
    else:
        print("[Quantize] Size OK ✓")

    print("\nNext step: python aiml/sensor_model/export/convert_to_c_array.py")


if __name__ == "__main__":
    main()
