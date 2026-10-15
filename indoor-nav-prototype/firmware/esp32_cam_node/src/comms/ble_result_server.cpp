/**
 * ble_result_server.cpp — CAM Node GATT Server Implementation
 *
 * The ESP32-CAM advertises its own GATT service.
 * The gateway (Raspberry Pi / laptop) connects as central and subscribes.
 * This is the correct BLE topology: edge devices advertise, gateway scans.
 *
 * NimBLE simultaneous roles on ESP32:
 *   - GATT CLIENT  → connects to sensor node (TriggerListener)
 *   - GATT SERVER  → this file; gateway connects to us
 * Both roles run concurrently on the same NimBLE stack.
 */
#include "ble_result_server.h"
#include "../config.h"
#include <NimBLEDevice.h>
#include <stdio.h>

namespace BLEResultServer {

static NimBLEServer*         _pServer   = nullptr;
static NimBLECharacteristic* _pResChar  = nullptr;
static bool                  _connected = false;
static int                   _clients   = 0;

class ServerCallbacks : public NimBLEServerCallbacks {
    void onConnect(NimBLEServer* pServer) override {
        _clients++;
        _connected = true;
        Serial.printf("[BLEResult] Gateway connected (%d clients)\n", _clients);
        pServer->startAdvertising();  // keep advertising for gateway reconnect
    }
    void onDisconnect(NimBLEServer* pServer) override {
        _clients = max(0, _clients - 1);
        _connected = (_clients > 0);
        Serial.println("[BLEResult] Gateway disconnected");
        pServer->startAdvertising();
    }
};

void begin() {
    // NimBLEDevice::init() already called by TriggerListener::begin().
    // We share the same BLE stack — just add a server role.
    _pServer = NimBLEDevice::createServer();
    _pServer->setCallbacks(new ServerCallbacks());

    // Create our CAM result service
    NimBLEService* pService = _pServer->createService(BLE_CAM_SERVICE_UUID);

    _pResChar = pService->createCharacteristic(
        BLE_CAM_RESULT_CHAR_UUID,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    pService->start();

    // Advertise both services so gateway can find and connect to us
    NimBLEAdvertising* pAdv = NimBLEDevice::getAdvertising();
    pAdv->addServiceUUID(BLE_CAM_SERVICE_UUID);
    pAdv->setScanResponse(true);
    pAdv->start();

    Serial.printf("[BLEResult] Advertising CAM service. Gateway connects to subscribe.\n");
}

void sendResult(int classIndex, float confidence, int grid_x, int grid_y) {
    if (!_pResChar || _clients == 0) return;

    char buf[100];
    snprintf(buf, sizeof(buf),
        "{\"ts\":%lu,\"vcls\":%d,\"vcf\":%.2f,\"gx\":%d,\"gy\":%d}",
        (unsigned long)millis(), classIndex, confidence, grid_x, grid_y
    );
    _pResChar->setValue(buf);
    _pResChar->notify();
}

bool isConnected() { return _connected; }

} // namespace BLEResultServer
