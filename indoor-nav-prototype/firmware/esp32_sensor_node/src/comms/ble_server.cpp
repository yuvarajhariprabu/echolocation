/**
 * ble_server.cpp — NimBLE GATT Server Implementation
 *
 * Uses h2zero/NimBLE-Arduino (lighter than bluedroid, no blocking calls).
 *
 * Architecture:
 *  - One GATT Service (BLE_SERVICE_UUID)
 *  - One Characteristic (BLE_CHAR_EVENT_UUID):
 *      Properties: READ | NOTIFY
 *      Value: JSON event string
 *      Descriptor: 0x2902 (CCCD — client writes 0x0001 to subscribe)
 *
 * Both the gateway AND the ESP32-CAM node subscribe to this characteristic.
 * The CAM node uses it as its trigger source.
 */
#include "ble_server.h"
#include "../config.h"
#include <NimBLEDevice.h>
#include <stdio.h>

namespace BLEServer {

static NimBLEServer*         _pServer  = nullptr;
static NimBLECharacteristic* _pEvtChar = nullptr;
static bool                  _connected = false;

// ── NimBLE server callbacks ───────────────────────────────────────────────
class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) override {
        _connected = true;
        Serial.println("[BLE] Client connected");
        // Allow additional connections (gateway + cam node)
        pServer->startAdvertising();
    }
    void onDisconnect(NimBLEServer* pServer) override {
        Serial.println("[BLE] Client disconnected");
        if (pServer->getConnectedCount() == 0) {
            _connected = false;
        }
        pServer->startAdvertising();
    }
};

void begin() {
    NimBLEDevice::init(BLE_DEVICE_NAME);
    NimBLEDevice::setPower(ESP_PWR_LVL_P9);  // max TX power

    _pServer = NimBLEDevice::createServer();
    _pServer->setCallbacks(new ServerCallbacks());

    NimBLEService* pService = _pServer->createService(BLE_SERVICE_UUID);

    _pEvtChar = pService->createCharacteristic(
        BLE_CHAR_EVENT_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    pService->start();

    NimBLEAdvertising* pAdv = NimBLEDevice::getAdvertising();
    pAdv->addServiceUUID(BLE_SERVICE_UUID);
    pAdv->setScanResponse(true);
    pAdv->start();

    Serial.printf("[BLE] Advertising as \"%s\"\n", BLE_DEVICE_NAME);
}

void sendEvent(
    int classIndex, float confidence,
    float front_cm, float left_cm, float right_cm,
    uint16_t floor_mm, float yaw_rate_dps, bool stationary
) {
    if (!_pEvtChar) return;

    // Compact JSON payload (no spaces, short keys to fit in one BLE packet ≤244B)
    char buf[220];
    snprintf(buf, sizeof(buf),
        "{\"ts\":%lu,\"cls\":%d,\"cf\":%.2f,\"df\":%.1f,\"dl\":%.1f,"
        "\"dr\":%.1f,\"flr\":%u,\"yr\":%.1f,\"sta\":%d}",
        (unsigned long)millis(),
        classIndex, confidence,
        front_cm, left_cm, right_cm,
        floor_mm, yaw_rate_dps,
        stationary ? 1 : 0
    );

    _pEvtChar->setValue(buf);
    _pEvtChar->notify();
}

bool isConnected() {
    return _connected;
}

} // namespace BLEServer
