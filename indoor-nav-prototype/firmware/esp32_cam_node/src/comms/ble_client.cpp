/**
 * ble_client.cpp — NimBLE Client: CAM node → Gateway
 *
 * Connects to the gateway's GATT server and sends FOMO results as
 * compact JSON notifications. Privacy-safe: only classification metadata
 * (class index, confidence, grid position) is transmitted — never pixels.
 */
#include "ble_client.h"
#include "../config.h"
#include <NimBLEDevice.h>
#include <stdio.h>

namespace BLEClient {

static NimBLEClient*         _pClient     = nullptr;
static NimBLERemoteCharacteristic* _pChar = nullptr;
static volatile bool         _connected   = false;

class ClientCallbacks : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient*) override {
        _connected = true;
        Serial.println("[BLEClient] Connected to gateway");
    }
    void onDisconnect(NimBLEClient*) override {
        _connected = false;
        Serial.println("[BLEClient] Disconnected from gateway");
        NimBLEDevice::getScan()->start(0, nullptr, false);
    }
};

class ScanCallbacks : public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice* dev) override {
        if (dev->isAdvertisingService(NimBLEUUID(BLE_CAM_SERVICE_UUID))) {
            // Found our service — actually we advertise, so look for gateway
            // The gateway acts as a GATT server too; scan for its service UUID
        }
        // Simpler: connect to any device named "BlindNav-Gateway"
        if (dev->haveName() &&
            strcmp(dev->getName().c_str(), "BlindNav-Gateway") == 0) {

            NimBLEDevice::getScan()->stop();
            _pClient = NimBLEDevice::createClient();
            _pClient->setCallbacks(new ClientCallbacks());

            if (_pClient->connect(dev)) {
                NimBLERemoteService* svc = _pClient->getService(BLE_CAM_SERVICE_UUID);
                if (svc) {
                    _pChar = svc->getCharacteristic(BLE_CAM_RESULT_CHAR_UUID);
                }
            }
        }
    }
};

void begin() {
    // We also act as a GATT server so the sensor node can trigger us,
    // AND as a GATT client to push results to the gateway.
    // NimBLE supports concurrent server + client roles.
    NimBLEScan* pScan = NimBLEDevice::getScan();
    pScan->setAdvertisedDeviceCallbacks(new ScanCallbacks());
    pScan->setActiveScan(true);
    pScan->start(0, nullptr, false);
    Serial.println("[BLEClient] Scanning for gateway...");
}

void sendResult(int classIndex, float confidence, int grid_x, int grid_y) {
    if (!_connected || !_pChar) return;

    char buf[100];
    snprintf(buf, sizeof(buf),
        "{\"ts\":%lu,\"vcls\":%d,\"vcf\":%.2f,\"gx\":%d,\"gy\":%d}",
        (unsigned long)millis(), classIndex, confidence, grid_x, grid_y
    );
    _pChar->writeValue(buf, strlen(buf), false);
}

bool isConnected() { return _connected; }

} // namespace BLEClient
