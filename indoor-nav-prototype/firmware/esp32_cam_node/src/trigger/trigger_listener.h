/**
 * trigger_listener.h — BLE Client: listens for sensor node obstacle events
 *
 * The ESP32-CAM subscribes to the sensor node's GATT characteristic.
 * When a "fast-path" class event arrives with sufficient confidence,
 * it signals the capture loop to run one inference cycle.
 *
 * Privacy design rule: camera stays POWERED DOWN between triggers.
 * No continuous capture. No frame storage or transmission.
 */
#pragma once
#include <Arduino.h>

namespace TriggerListener {

/**
 * Initialize NimBLE client, scan for sensor node, subscribe to event char.
 * Non-blocking: connection happens asynchronously in the BLE task.
 */
void begin();

/**
 * @return true if a trigger event has been received since last clearTrigger().
 *         Thread-safe — uses atomic flag.
 */
bool triggered();

/** Clear the trigger flag after processing. */
void clearTrigger();

/** @return true if connected to the sensor node. */
bool isConnected();

} // namespace TriggerListener
