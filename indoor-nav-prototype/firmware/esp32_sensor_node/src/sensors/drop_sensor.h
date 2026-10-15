/**
 * drop_sensor.h — VL53L0X Time-of-Flight Drop/Stair Sensor Driver
 *
 * Measures floor distance. A large jump from the baseline reading
 * indicates a drop-off (stairs, step, ramp).
 */
#pragma once
#include <Arduino.h>
#include <Adafruit_VL53L0X.h>

namespace DropSensor {

/**
 * Initialize VL53L0X over I2C.
 * @return true if sensor found and initialized; false on failure.
 */
bool begin();

/**
 * Calibrate floor baseline (call once when user is standing on level ground).
 * Takes CALIBRATION_SAMPLES readings and averages them.
 */
void calibrate();

/**
 * Read current floor distance.
 * @param dist_mm  Output: floor distance in mm
 * @return true if reading is valid; false if sensor timeout/error
 */
bool read(uint16_t& dist_mm);

/**
 * Determine if the current reading indicates a drop-off.
 * Uses baseline + DROPOFF_THRESHOLD_MM from config.h.
 * @param dist_mm  Current floor reading
 */
bool isDropoff(uint16_t dist_mm);

} // namespace DropSensor
