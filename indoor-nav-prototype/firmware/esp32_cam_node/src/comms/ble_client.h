/**
 * ble_client.h — BLE Client: Sends vision results to the gateway
 */
#pragma once
#include <Arduino.h>

namespace BLEClient {

/** Initialize NimBLE client, scan for gateway. */
void begin();

/**
 * Send a FOMO inference result to the gateway.
 *
 * @param classIndex  Vision class index (0–6)
 * @param confidence  FOMO peak activation confidence [0,1]
 * @param grid_x      Grid column of detection
 * @param grid_y      Grid row of detection
 */
void sendResult(int classIndex, float confidence, int grid_x, int grid_y);

/** @return true if connected to gateway. */
bool isConnected();

} // namespace BLEClient
