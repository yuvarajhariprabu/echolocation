/**
 * ultrasonic.h — HC-SR04 Time-Multiplexed Driver
 *
 * Sensors are ALWAYS fired sequentially (never simultaneously) to prevent
 * cross-talk interference between the three HC-SR04 units.
 */
#pragma once
#include <Arduino.h>

namespace Ultrasonic {

/**
 * Initialize all three ultrasonic sensor pins.
 * Must be called once in setup().
 */
void begin();

/**
 * Read all three sensors sequentially with a dead-time gap between pings.
 * Writes results to the three output pointers (in cm).
 * Returns false if a sensor reports out-of-range (timeout → -1).
 *
 * @param front_cm  Output: front sensor distance (cm), or -1 if out of range
 * @param left_cm   Output: left  sensor distance (cm), or -1 if out of range
 * @param right_cm  Output: right sensor distance (cm), or -1 if out of range
 */
void readAll(float& front_cm, float& left_cm, float& right_cm);

/**
 * Read a single HC-SR04.
 * @param trigPin  GPIO for TRIG
 * @param echoPin  GPIO for ECHO (after voltage divider)
 * @return Distance in cm, or -1.0f if no echo within timeout
 */
float readOne(int trigPin, int echoPin);

} // namespace Ultrasonic
