/**
 * config.h — Sensor Node Pin Map & Thresholds
 *
 * SINGLE PLACE for all hardware constants. Change here, everything updates.
 * Pin numbers sourced from WIRING.md.
 */
#pragma once

// ─── Ultrasonic Sensors (HC-SR04) ──────────────────────────────────────────
// All ECHO pins go through a 1kΩ/2kΩ voltage divider (5V→3.3V) per WIRING.md
#define TRIG_FRONT   5
#define ECHO_FRONT  18
#define TRIG_LEFT   17
#define ECHO_LEFT   16
#define TRIG_RIGHT  19
#define ECHO_RIGHT  23

// Inter-ping dead-time (µs) to prevent HC-SR04 cross-talk when multiplexed
#define US_INTER_PING_DELAY_US  500

// Ultrasonic range limits
#define US_TIMEOUT_US           25000UL   // 25ms → caps range at ~4m
#define US_MIN_DIST_CM          2.0f      // ignore readings below 2cm (ringing)

// ─── I²C Bus ───────────────────────────────────────────────────────────────
#define I2C_SDA  21
#define I2C_SCL  22

// ─── VL53L0X — Drop / Floor Sensor ────────────────────────────────────────
#define VL53L0X_I2C_ADDR        0x29     // default, no XSHUT pin change needed
// Floor baseline is read on boot. A jump > this threshold = drop-off / stairs.
#define DROPOFF_THRESHOLD_MM    150

// ─── MPU6050 — IMU ─────────────────────────────────────────────────────────
#define MPU6050_I2C_ADDR        0x68     // default (AD0 = GND)

// Complementary filter: how much to trust gyro vs accelerometer angle
// 0.98 = trusts gyro heavily short-term, corrected long-term by accel
#define IMU_COMP_ALPHA          0.98f

// Stationary-detection thresholds (ZUPT — zero-velocity update)
// If |accel_mag - g| < this AND gyro rates < GYRO thresh → assume still
#define IMU_STATIONARY_ACCEL_TOL  0.15f  // m/s²
#define IMU_STATIONARY_GYRO_TOL   0.03f  // rad/s

// Head-tilt guard: if pitch or roll exceeds this, ultrasonic readings are
// likely pointing at floor/ceiling → mark readings invalid
#define IMU_MAX_TILT_DEG        30.0f

// ─── Haptic Motors (via NPN/MOSFET driver — NOT direct GPIO) ───────────────
#define HAPTIC_FRONT   25
#define HAPTIC_LEFT    26
#define HAPTIC_RIGHT   27

// LEDC (PWM) channels for haptics
#define CH_HAPTIC_FRONT  0
#define CH_HAPTIC_LEFT   1
#define CH_HAPTIC_RIGHT  2
#define PWM_FREQ_HZ      5000
#define PWM_RES_BITS     8       // 0–255 duty cycle

// ─── Audio Output ──────────────────────────────────────────────────────────
#define AUDIO_PIN        32
#define CH_AUDIO         3
#define AUDIO_FREQ_HZ    2000    // default alert tone

// ─── Obstacle Distance Thresholds ──────────────────────────────────────────
#define OBSTACLE_NEAR_CM   40    // NEAR zone  → strong haptic
#define OBSTACLE_WARN_CM   90    // WARN zone  → light haptic

// ─── TFLite Micro / Sensor Buffer ──────────────────────────────────────────
#define SENSOR_WINDOW_SIZE  20   // number of time-steps per inference window
// Channels: front_cm, left_cm, right_cm, floor_mm, gyro_x, gyro_y, gyro_z,
//           accel_x, accel_y = 9 channels
#define SENSOR_CHANNELS      9
#define TFLITE_ARENA_SIZE   (32 * 1024)  // 32KB tensor arena (tune per model)

// Class count (must match class_definitions.yaml sensor_classes count)
#define NUM_SENSOR_CLASSES   9
#define CONFIDENCE_THRESHOLD 0.65f       // below this → report class 8 (unknown)

// ─── BLE ───────────────────────────────────────────────────────────────────
// UUIDs shared with edge_gateway/comms/ble_gateway.py — keep in sync
#define BLE_DEVICE_NAME       "BlindNav-Sensor"
#define BLE_SERVICE_UUID      "4A98C7D2-1E3F-4B6A-8D5C-2F9E0A7B3C1D"
#define BLE_CHAR_EVENT_UUID   "5B09D8E3-2F40-5C7B-9E6D-3A0F1B8C4D2E"

// ─── Task Scheduling ───────────────────────────────────────────────────────
#define SENSOR_TASK_PERIOD_MS   50    // 20 Hz sensor polling
#define DECISION_TASK_PERIOD_MS 50    // 20 Hz decision loop
#define SENSOR_TASK_STACK       4096
#define DECISION_TASK_STACK     4096
#define SENSOR_TASK_PRIORITY    2
#define DECISION_TASK_PRIORITY  2
#define SENSOR_TASK_CORE        0
#define DECISION_TASK_CORE      1
