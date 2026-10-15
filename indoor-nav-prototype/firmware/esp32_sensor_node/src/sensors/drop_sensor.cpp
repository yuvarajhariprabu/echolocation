/**
 * drop_sensor.cpp — VL53L0X Drop/Stair Sensor Implementation
 *
 * The sensor faces downward and reads floor distance.
 * A baseline is measured at startup on level ground.
 * Readings that exceed baseline + DROPOFF_THRESHOLD_MM are flagged as drop-offs.
 */
#include "drop_sensor.h"
#include "../config.h"

namespace DropSensor {

static Adafruit_VL53L0X _tof;
static uint16_t _baseline_mm = 0;
static const int CALIBRATION_SAMPLES = 20;

bool begin() {
    // Wire.begin() must be called before this (in main.cpp setup)
    if (!_tof.begin()) {
        Serial.println("[DropSensor] VL53L0X not found — check I2C wiring (SDA=21, SCL=22)");
        return false;
    }
    // Use long-range mode for better reliability with downward pointing
    _tof.startRangeContinuous(33);  // 33ms inter-measurement
    Serial.println("[DropSensor] VL53L0X initialized OK");
    return true;
}

void calibrate() {
    Serial.println("[DropSensor] Calibrating floor baseline...");
    uint32_t sum = 0;
    int valid = 0;

    for (int i = 0; i < CALIBRATION_SAMPLES; i++) {
        VL53L0X_RangingMeasurementData_t m;
        _tof.getRangingMeasurement(&m, false);
        if (m.RangeStatus != 4) {  // status 4 = phase fail / out of range
            sum += m.RangeMillimeter;
            valid++;
        }
        delay(40);
    }

    if (valid > 0) {
        _baseline_mm = sum / valid;
        Serial.printf("[DropSensor] Baseline = %u mm\n", _baseline_mm);
    } else {
        _baseline_mm = 300;  // safe default: ~30cm floor clearance
        Serial.println("[DropSensor] Calibration failed — using default 300mm baseline");
    }
}

bool read(uint16_t& dist_mm) {
    VL53L0X_RangingMeasurementData_t m;
    _tof.getRangingMeasurement(&m, false);

    if (m.RangeStatus == 4) {
        // Phase fail: out of range or timeout
        dist_mm = 0;
        return false;
    }
    dist_mm = m.RangeMillimeter;
    return true;
}

bool isDropoff(uint16_t dist_mm) {
    if (dist_mm == 0) return false;  // invalid reading — don't false-alarm
    if (_baseline_mm == 0) {
        // Fallback if calibrate() was never called
        return dist_mm > DROPOFF_THRESHOLD_MM;
    }
    return (dist_mm > _baseline_mm + DROPOFF_THRESHOLD_MM);
}

} // namespace DropSensor
