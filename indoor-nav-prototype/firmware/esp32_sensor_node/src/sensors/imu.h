/**
 * imu.h — MPU6050 IMU Driver
 *
 * Provides:
 *  - Pitch/roll via complementary filter (gyro + accelerometer fusion)
 *  - Yaw rate (raw gyro Z)
 *  - 2D dead-reckoning position estimate (very drift-prone; use for short intervals only)
 *  - Stationary detection (ZUPT — zero-velocity update) to fight dead-reckoning drift
 *  - IMU-based motion disambiguation: was this a user movement or an external object change?
 */
#pragma once
#include <Arduino.h>

namespace IMU {

struct State {
    float pitch_deg;     // Head tilt forward/backward
    float roll_deg;      // Head tilt side to side
    float yaw_rate_dps;  // Rotation rate around vertical axis (deg/s)
    float accel_x;       // Raw accel X (m/s²) — body-frame
    float accel_y;       // Raw accel Y (m/s²) — body-frame
    float accel_z;       // Raw accel Z (m/s²) — body-frame
    float gyro_x;        // Raw gyro X (rad/s)
    float gyro_y;        // Raw gyro Y (rad/s)
    float gyro_z;        // Raw gyro Z (rad/s)
    float pos_x_m;       // Dead-reckoning X position (m) — drifts over time
    float pos_y_m;       // Dead-reckoning Y position (m) — drifts over time
    float vel_x;         // Integrated velocity X (zeroed when stationary)
    float vel_y;         // Integrated velocity Y (zeroed when stationary)
    bool  stationary;    // True if ZUPT detected (no real movement)
    bool  orientation_valid; // True if pitch/roll within IMU_MAX_TILT_DEG
};

/**
 * Initialize MPU6050.
 * @return true on success, false if not found on I2C bus.
 */
bool begin();

/**
 * Update the IMU state. Call once per sensor loop iteration.
 * @param dt_s  Time delta since last call (seconds)
 * @param state Output state structure (updated in-place)
 */
void update(float dt_s, State& state);

/**
 * Reset dead-reckoning position to (0,0).
 * Call when user is at a known landmark.
 */
void resetPosition(State& state);

} // namespace IMU
