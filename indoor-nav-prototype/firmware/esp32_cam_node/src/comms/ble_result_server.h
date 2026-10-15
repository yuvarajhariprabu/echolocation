/**
 * ble_result_server.h — CAM Node GATT Server (Result Advertisement)
 *
 * The CAM node acts as a GATT SERVER so the gateway can connect TO it
 * and subscribe for FOMO result notifications.
 *
 * Architecture correction:
 *   WRONG: CAM tries to scan and connect to gateway (gateway is central, not peripheral)
 *   RIGHT: CAM advertises its own service; gateway (central) connects and subscribes
 *
 * Both roles (trigger client + result server) are supported simultaneously
 * by NimBLE on ESP32.
 */
#pragma once
#include <Arduino.h>

namespace BLEResultServer {

/** Initialize and start advertising the CAM result service. */
void begin();

/**
 * Notify all subscribed clients (i.e. the gateway) of a FOMO result.
 * Only sends if at least one client is subscribed (CCCD enabled).
 *
 * @param classIndex  Vision class index (0–6)
 * @param confidence  FOMO peak activation [0,1]
 * @param grid_x      Grid column
 * @param grid_y      Grid row
 */
void sendResult(int classIndex, float confidence, int grid_x, int grid_y);

/** @return true if a gateway client is connected and subscribed. */
bool isConnected();

} // namespace BLEResultServer
