/**
 * imu.cpp — MPU6050 IMU Driver Implementation
 *
 * Complementary filter math:
 *   angle = α * (angle + gyro_rate * dt) + (1-α) * accel_angle
 *   where α = IMU_COMP_ALPHA (0.98) — trusts gyro short-term, accel long-term.
 *
 * ZUPT (zero-velocity update):
 *   If |accel_magnitude - g| < tol AND gyro rates ~ 0 → user is stationary.
 *   Reset integrated velocity to stop dead-reckoning from drifting without bound.
 *
 * IMU motion disambiguation:
 *   state.stationary = true  → ultrasonic distance changes are caused by
 *                               EXTERNAL objects (moving person/obstacle)
 *   state.stationary = false → distance changes may be caused by user movement;
 *                               do not classify as "approaching object" yet
 */
#include "imu.h"
#include "../config.h"
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <math.h>

namespace IMU {

static Adafruit_MPU6050 _mpu;
static float _pitch = 0.0f;
static float _roll  = 0.0f;
static float _vel_x = 0.0f;
static float _vel_y = 0.0f;
static float _pos_x = 0.0f;
static float _pos_y = 0.0f;

bool begin() {
    if (!_mpu.begin()) {
        Serial.println("[IMU] MPU6050 not found — check I2C wiring (SDA=21, SCL=22, addr=0x68)");
        return false;
    }
    _mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
    _mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    _mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("[IMU] MPU6050 initialized OK");
    return true;
}

void update(float dt_s, State& state) {
    sensors_event_t a, g, temp;
    _mpu.getEvent(&a, &g, &temp);

    // ── Complementary filter: pitch & roll ────────────────────────────────
    float acc_pitch = atan2f(a.acceleration.y, a.acceleration.z) * (180.0f / M_PI);
    float acc_roll  = atan2f(-a.acceleration.x, a.acceleration.z) * (180.0f / M_PI);

    float gyro_pitch_rate = g.gyro.x * (180.0f / M_PI);  // rad/s → deg/s
    float gyro_roll_rate  = g.gyro.y * (180.0f / M_PI);

    _pitch = IMU_COMP_ALPHA * (_pitch + gyro_pitch_rate * dt_s) + (1.0f - IMU_COMP_ALPHA) * acc_pitch;
    _roll  = IMU_COMP_ALPHA * (_roll  + gyro_roll_rate  * dt_s) + (1.0f - IMU_COMP_ALPHA) * acc_roll;

    // ── Stationary detection (ZUPT) ────────────────────────────────────────
    float accel_mag = sqrtf(
        a.acceleration.x * a.acceleration.x +
        a.acceleration.y * a.acceleration.y +
        a.acceleration.z * a.acceleration.z
    );
    bool stationary = (fabsf(accel_mag - 9.81f) < IMU_STATIONARY_ACCEL_TOL) &&
                      (fabsf(g.gyro.x) < IMU_STATIONARY_GYRO_TOL) &&
                      (fabsf(g.gyro.y) < IMU_STATIONARY_GYRO_TOL) &&
                      (fabsf(g.gyro.z) < IMU_STATIONARY_GYRO_TOL);

    // ── Dead-reckoning (horizontal plane) ─────────────────────────────────
    if (stationary) {
        _vel_x = 0.0f;  // ZUPT: reset velocity to prevent unbounded drift
        _vel_y = 0.0f;
    } else {
        _vel_x += a.acceleration.x * dt_s;
        _vel_y += a.acceleration.y * dt_s;
    }
    _pos_x += _vel_x * dt_s;
    _pos_y += _vel_y * dt_s;

    // ── Populate output state ──────────────────────────────────────────────
    state.pitch_deg       = _pitch;
    state.roll_deg        = _roll;
    state.yaw_rate_dps    = g.gyro.z * (180.0f / M_PI);
    state.accel_x         = a.acceleration.x;
    state.accel_y         = a.acceleration.y;
    state.accel_z         = a.acceleration.z;
    state.gyro_x          = g.gyro.x;
    state.gyro_y          = g.gyro.y;
    state.gyro_z          = g.gyro.z;
    state.vel_x           = _vel_x;
    state.vel_y           = _vel_y;
    state.pos_x_m         = _pos_x;
    state.pos_y_m         = _pos_y;
    state.stationary      = stationary;
    state.orientation_valid = (fabsf(_pitch) < IMU_MAX_TILT_DEG) &&
                              (fabsf(_roll)  < IMU_MAX_TILT_DEG);
}

void resetPosition(State& state) {
    _pos_x = 0.0f;
    _pos_y = 0.0f;
    _vel_x = 0.0f;
    _vel_y = 0.0f;
    state.pos_x_m = 0.0f;
    state.pos_y_m = 0.0f;
    state.vel_x   = 0.0f;
    state.vel_y   = 0.0f;
}

} // namespace IMU
