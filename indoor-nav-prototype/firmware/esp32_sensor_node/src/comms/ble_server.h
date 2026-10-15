/**
 * ble_server.h — NimBLE GATT Server (Sensor Node → Gateway)
 *
 * Broadcasts obstacle classification events to the edge gateway over BLE.
 *
 * Payload format (sent as JSON string in the GATT characteristic notification):
 * {
 *   "ts":  <millis>,
 *   "cls": <sensor class index 0–8>,
 *   "cf":  <confidence 0.0–1.0>,
 *   "df":  <front_cm>,
 *   "dl":  <left_cm>,
 *   "dr":  <right_cm>,
 *   "flr": <floor_mm>,
 *   "yr":  <yaw_rate_dps>,
 *   "sta": <1 if user stationary, 0 if moving>
 * }
 *
 * Also broadcasts to the ESP32-CAM node (trigger signal):
 * The cam node subscribes to the same service and listens for fast-path classes.
 */
#pragma once
#include <Arduino.h>

namespace BLEServer {

/**
 * Initialize NimBLE server, register GATT service + characteristic.
 * Call once in setup().
 */
void begin();

/**
 * Package and send an obstacle event notification to all subscribed clients.
 *
 * @param classIndex    Sensor model class index (0–8)
 * @param confidence    Model confidence [0,1]
 * @param front_cm      Ultrasonic front distance
 * @param left_cm       Ultrasonic left distance
 * @param right_cm      Ultrasonic right distance
 * @param floor_mm      VL53L0X floor distance
 * @param yaw_rate_dps  Yaw rate from IMU
 * @param stationary    True if user is stationary (ZUPT)
 */
void sendEvent(
    int classIndex, float confidence,
    float front_cm, float left_cm, float right_cm,
    uint16_t floor_mm, float yaw_rate_dps, bool stationary
);

/** @return true if at least one client is connected and subscribed. */
bool isConnected();

} // namespace BLEServer
