"""
model_1dcnn.py — 1D CNN Architecture for Sensor Classification

Input:  (batch, window_size, channels) = (batch, 20, 9) float32 normalized
Output: (batch, num_classes) softmax probabilities

Architecture:
    Conv1D(32) → BN → ReLU → Dropout
    Conv1D(64) → BN → ReLU → Dropout
    Conv1D(64) → BN → ReLU
    GlobalAveragePooling1D
    Dense(64) → ReLU → Dropout
    Dense(num_classes) → Softmax

Design choices:
  - GlobalAvgPool instead of Flatten: smaller model, less overfitting, compatible
    with INT8 quantization (avoids large dense layers that bloat .tflite size).
  - BatchNorm: helps convergence with small sensor datasets.
  - No LSTM/GRU: Conv1D is faster to quantize and runs reliably on TFLite Micro.
"""

import tensorflow as tf
from tensorflow.keras import layers, models
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "train_config.yaml"
with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

WINDOW_SIZE  = cfg["data"]["window_size"]
CHANNELS     = cfg["data"]["channels"]
NUM_CLASSES  = cfg["model"]["num_classes"]
FILTERS      = cfg["model"]["filters"]
KERNEL_SIZE  = cfg["model"]["kernel_size"]
DROPOUT      = cfg["model"]["dropout"]
DENSE_UNITS  = cfg["model"]["dense_units"]


def build_model(
    window_size: int  = WINDOW_SIZE,
    channels: int     = CHANNELS,
    num_classes: int  = NUM_CLASSES,
    filters: list     = FILTERS,
    kernel_size: int  = KERNEL_SIZE,
    dropout: float    = DROPOUT,
    dense_units: int  = DENSE_UNITS,
) -> tf.keras.Model:
    """Build and return the 1D CNN model (uncompiled)."""

    inp = layers.Input(shape=(window_size, channels), name="sensor_input")
    x = inp

    for i, f in enumerate(filters):
        x = layers.Conv1D(f, kernel_size, padding="same", name=f"conv1d_{i}")(x)
        x = layers.BatchNormalization(name=f"bn_{i}")(x)
        x = layers.ReLU(name=f"relu_{i}")(x)
        if i < len(filters) - 1:
            x = layers.Dropout(dropout, name=f"drop_conv_{i}")(x)

    x = layers.GlobalAveragePooling1D(name="gap")(x)
    x = layers.Dense(dense_units, activation="relu", name="dense_0")(x)
    x = layers.Dropout(dropout, name="drop_dense")(x)
    out = layers.Dense(num_classes, activation="softmax", name="output")(x)

    return models.Model(inputs=inp, outputs=out, name="sensor_1dcnn")


def model_summary():
    m = build_model()
    m.summary()
    print(f"\nTotal params: {m.count_params():,}")


if __name__ == "__main__":
    model_summary()
