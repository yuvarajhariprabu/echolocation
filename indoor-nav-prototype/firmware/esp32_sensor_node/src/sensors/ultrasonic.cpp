/**
 * ultrasonic.cpp — HC-SR04 Time-Multiplexed Driver Implementation
 *
 * Key design choices:
 *  1. readAll() fires sensors one at a time with US_INTER_PING_DELAY_US
 *     dead-time between pings → prevents cross-talk.
 *  2. pulseIn timeout (US_TIMEOUT_US) caps max range at ~4m, bounding
 *     loop timing to a known worst-case.
 *  3. Readings below US_MIN_DIST_CM are discarded as sensor ringing artifacts.
 */
#include "ultrasonic.h"
#include "../config.h"

namespace Ultrasonic {

void begin() {
    pinMode(TRIG_FRONT, OUTPUT);
    pinMode(ECHO_FRONT, INPUT);
    pinMode(TRIG_LEFT,  OUTPUT);
    pinMode(ECHO_LEFT,  INPUT);
    pinMode(TRIG_RIGHT, OUTPUT);
    pinMode(ECHO_RIGHT, INPUT);

    // Ensure TRIG lines start LOW
    digitalWrite(TRIG_FRONT, LOW);
    digitalWrite(TRIG_LEFT,  LOW);
    digitalWrite(TRIG_RIGHT, LOW);
}

float readOne(int trigPin, int echoPin) {
    // Ensure clean LOW state before pulse
    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);

    // 10µs HIGH pulse triggers a ping
    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    // Measure echo duration; timeout caps range at ~4m
    long duration = pulseIn(echoPin, HIGH, US_TIMEOUT_US);

    if (duration == 0) {
        return -1.0f;  // no echo — out of range or no object
    }

    float dist_cm = duration * 0.0343f / 2.0f;

    // Reject ringing artifacts (too close)
    if (dist_cm < US_MIN_DIST_CM) {
        return -1.0f;
    }

    return dist_cm;
}

void readAll(float& front_cm, float& left_cm, float& right_cm) {
    // Sequential fire — NEVER ping multiple sensors simultaneously
    front_cm = readOne(TRIG_FRONT, ECHO_FRONT);
    delayMicroseconds(US_INTER_PING_DELAY_US);  // dead-time between pings

    left_cm  = readOne(TRIG_LEFT, ECHO_LEFT);
    delayMicroseconds(US_INTER_PING_DELAY_US);

    right_cm = readOne(TRIG_RIGHT, ECHO_RIGHT);
    // No trailing delay needed — caller controls timing via vTaskDelayUntil
}

} // namespace Ultrasonic
