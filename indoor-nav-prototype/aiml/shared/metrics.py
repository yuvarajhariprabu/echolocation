"""
metrics.py — Shared Evaluation Utilities

Used by both sensor_model/evaluate.py and vision_model/evaluation/
"""

import numpy as np
import time
from typing import List


def f1_per_class(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> List[float]:
    """Compute per-class F1 score."""
    f1_scores = []
    for c in range(num_classes):
        tp = np.sum((y_pred == c) & (y_true == c))
        fp = np.sum((y_pred == c) & (y_true != c))
        fn = np.sum((y_pred != c) & (y_true == c))
        precision = tp / (tp + fp + 1e-8)
        recall    = tp / (tp + fn + 1e-8)
        f1 = 2 * precision * recall / (precision + recall + 1e-8)
        f1_scores.append(float(f1))
    return f1_scores


class LatencyTimer:
    """Measure inference latency on-device (call from firmware test bench)."""

    def __init__(self):
        self._start = None

    def start(self):
        self._start = time.perf_counter()

    def stop_ms(self) -> float:
        if self._start is None:
            return 0.0
        return (time.perf_counter() - self._start) * 1000.0
