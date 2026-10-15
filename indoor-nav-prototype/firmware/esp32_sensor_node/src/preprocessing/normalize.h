/**
 * normalize.h — Per-Channel Min-Max Normalization
 *
 * Params are computed by aiml/sensor_model/preprocessing/normalize.py
 * during training and must be copied here manually (or auto-generated)
 * after the first training run.
 *
 * Channel order MUST match sensor_buffer.h and train_config.yaml:
 *   0: front_cm, 1: left_cm, 2: right_cm, 3: floor_mm,
 *   4: gyro_x, 5: gyro_y, 6: gyro_z, 7: accel_x, 8: accel_y
 */
#pragma once
#include <Arduino.h>
#include "../config.h"
#include "sensor_buffer.h"

namespace Normalize {

/**
 * Normalize a raw sensor reading into a Sample (all channels in [0,1]).
 *
 * @param front_cm   Raw front ultrasonic distance (cm), or -1 if invalid
 * @param left_cm    Raw left  ultrasonic distance (cm), or -1 if invalid
 * @param right_cm   Raw right ultrasonic distance (cm), or -1 if invalid
 * @param floor_mm   Raw floor ToF distance (mm), or 0 if invalid
 * @param gyro_x     Raw IMU gyro X (rad/s)
 * @param gyro_y     Raw IMU gyro Y (rad/s)
 * @param gyro_z     Raw IMU gyro Z (rad/s)
 * @param accel_x    Raw IMU accel X (m/s²)
 * @param accel_y    Raw IMU accel Y (m/s²)
 * @param out        Output normalized Sample
 */
void normalize(
    float front_cm, float left_cm, float right_cm,
    float floor_mm,
    float gyro_x, float gyro_y, float gyro_z,
    float accel_x, float accel_y,
    SensorBuffer::Sample& out
);

} // namespace Normalize
