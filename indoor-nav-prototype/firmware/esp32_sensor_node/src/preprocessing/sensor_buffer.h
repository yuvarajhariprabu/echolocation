/**
 * sensor_buffer.h — Sliding Window Buffer for 1D CNN Input
 *
 * Maintains a fixed-size rolling window of sensor readings across all channels.
 * When the window is full, the oldest sample is overwritten (ring buffer).
 *
 * Input channels (9 total, must match class_definitions.yaml and train_config.yaml):
 *   [0] front_cm      — ultrasonic front distance
 *   [1] left_cm       — ultrasonic left distance
 *   [2] right_cm      — ultrasonic right distance
 *   [3] floor_mm      — VL53L0X floor distance (normalized)
 *   [4] gyro_x        — IMU gyro X (rad/s)
 *   [5] gyro_y        — IMU gyro Y (rad/s)
 *   [6] gyro_z        — IMU gyro Z (rad/s)
 *   [7] accel_x       — IMU accel X (m/s²)
 *   [8] accel_y       — IMU accel Y (m/s²)
 */
#pragma once
#include <Arduino.h>
#include "../config.h"

namespace SensorBuffer {

/**
 * A single timestep of sensor readings (normalized floats).
 */
struct Sample {
    float channels[SENSOR_CHANNELS];
};

/**
 * The full sliding window, flattened to a 1D array as TFLite expects:
 *   layout: [step0_ch0, step0_ch1, ..., step0_ch8,
 *            step1_ch0, ..., stepN_ch8]
 * Total size: SENSOR_WINDOW_SIZE * SENSOR_CHANNELS floats
 */
struct Window {
    float data[SENSOR_WINDOW_SIZE * SENSOR_CHANNELS];
    bool  full;   // true once at least SENSOR_WINDOW_SIZE samples have been pushed
};

/** Initialize/clear the buffer. Call once in setup(). */
void begin();

/**
 * Push a new sample into the ring buffer.
 * Normalizes the sample via normalize.h before storing.
 * @param s  Normalized sample (all channels in [0,1] or [-1,1] range)
 */
void push(const Sample& s);

/**
 * Export the current window in the flattened layout TFLite expects.
 * @param win  Output window structure
 * @return true if window is full; false if not enough samples yet
 */
bool getWindow(Window& win);

/** Reset the buffer (clears all samples, sets full=false). */
void reset();

} // namespace SensorBuffer
