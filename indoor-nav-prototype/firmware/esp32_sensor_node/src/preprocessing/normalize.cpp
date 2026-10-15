/**
 * normalize.cpp — Per-Channel Min-Max Normalization Implementation
 *
 * ┌──────────────────────────────────────────────────────────────────────────┐
 * │ IMPORTANT: Update CH_MIN[] and CH_MAX[] after your first training run.  │
 * │ Run: python aiml/sensor_model/preprocessing/normalize.py                │
 * │ It prints the min/max per channel — copy those values here.             │
 * └──────────────────────────────────────────────────────────────────────────┘
 *
 * Formula: normalized = clamp((raw - min) / (max - min), 0.0, 1.0)
 * Invalid readings (-1 for ultrasonics, 0 for ToF) are mapped to 1.0
 * (maximum range / no detection) — this encodes "no obstacle" meaningfully.
 */
#include "normalize.h"
#include <math.h>

namespace Normalize {

// ── Per-channel normalization parameters ─────────────────────────────────────
// Placeholder values — REPLACE after running normalize.py on your collected data
// Channel order: front_cm, left_cm, right_cm, floor_mm, gyro_x, gyro_y, gyro_z, accel_x, accel_y
static const float CH_MIN[SENSOR_CHANNELS] = {
     2.0f,   // front_cm   — sensor minimum detection (US_MIN_DIST_CM)
     2.0f,   // left_cm
     2.0f,   // right_cm
     30.0f,  // floor_mm   — close floor (sensor above low surface)
    -5.0f,   // gyro_x     — rad/s
    -5.0f,   // gyro_y
    -5.0f,   // gyro_z
    -20.0f,  // accel_x    — m/s² (±2g range mapped approx)
    -20.0f,  // accel_y
};

static const float CH_MAX[SENSOR_CHANNELS] = {
    400.0f,  // front_cm   — ~4m max range
    400.0f,  // left_cm
    400.0f,  // right_cm
    2000.0f, // floor_mm   — 2m drop = stair flight
     5.0f,   // gyro_x
     5.0f,   // gyro_y
     5.0f,   // gyro_z
    20.0f,   // accel_x
    20.0f,   // accel_y
};

// Clamp to [0,1]
static inline float clamp01(float x) {
    if (x < 0.0f) return 0.0f;
    if (x > 1.0f) return 1.0f;
    return x;
}

void normalize(
    float front_cm, float left_cm, float right_cm,
    float floor_mm,
    float gyro_x, float gyro_y, float gyro_z,
    float accel_x, float accel_y,
    SensorBuffer::Sample& out
) {
    // Out-of-range / invalid readings → encode as "max range" (no obstacle)
    float raws[SENSOR_CHANNELS] = {
        front_cm < 0   ? CH_MAX[0] : front_cm,
        left_cm  < 0   ? CH_MAX[1] : left_cm,
        right_cm < 0   ? CH_MAX[2] : right_cm,
        floor_mm == 0  ? CH_MAX[3] : (float)floor_mm,
        gyro_x, gyro_y, gyro_z,
        accel_x, accel_y
    };

    for (int i = 0; i < SENSOR_CHANNELS; i++) {
        float range = CH_MAX[i] - CH_MIN[i];
        if (fabsf(range) < 1e-6f) {
            out.channels[i] = 0.0f;
        } else {
            out.channels[i] = clamp01((raws[i] - CH_MIN[i]) / range);
        }
    }
}

} // namespace Normalize
