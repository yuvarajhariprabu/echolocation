/**
 * trigger_listener.cpp — BLE Client Implementation
 *
 * Connects to the sensor node (BlindNav-Sensor) and subscribes to its
 * event characteristic. Parses incoming JSON events and sets the trigger
 * flag when a fast-path class is detected with sufficient confidence.
 *
 * Fast-path classes (defined in config.h TRIGGER_ON_CLASSES):
 *   0 = static_obstacle, 1 = moving_object, 4 = approaching, 6 = crossing
 */
#include "trigger_listener.h"
#include "../config.h"
#include <NimBLEDevice.h>
#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

namespace TriggerListener {

static volatile bool _triggered  = false;
static volatile bool _connected  = false;
static NimBLEClient* _pClient    = nullptr;

static const int TRIGGER_CLASSES[] = TRIGGER_ON_CLASSES;
static const int TRIGGER_CLASS_COUNT = sizeof(TRIGGER_CLASSES) / sizeof(int);

// Simple JSON field extract (avoids ArduinoJson dependency for tiny payload)
static float extractFloat(const char* json, const char* key) {
    const char* p = strstr(json, key);
    if (!p) return -1.0f;
    p += strlen(key) + 2;  // skip key + ":"
    return atof(p);
}

static int extractInt(const char* json, const char* key) {
    return (int)extractFloat(json, key);
}

// ── NimBLE notify callback ────────────────────────────────────────────────
static void notifyCallback(
    NimBLERemoteCharacteristic* /*pChar*/,
    uint8_t* pData, size_t length, bool /*isNotify*/
) {
    if (length == 0) return;

    char buf[250] = {0};
    size_t copy_len = length < sizeof(buf) - 1 ? length : sizeof(buf) - 1;
    memcpy(buf, pData, copy_len);

    int   cls  = extractInt(buf, "\"cls\"");
    float conf = extractFloat(buf, "\"cf\"");

    if (conf < TRIGGER_CONFIDENCE_MIN) return;

    for (int i = 0; i < TRIGGER_CLASS_COUNT; i++) {
        if (cls == TRIGGER_CLASSES[i]) {
            _triggered = true;
            return;
        }
    }
}

// ── NimBLE client callbacks ────────────────────────────────────────────────
class ClientCallbacks : public NimBLEClientCallbacks {
    void onConnect(NimBLEClient* pClient) override {
        _connected = true;
        Serial.println("[Trigger] Connected to sensor node");
    }
    void onDisconnect(NimBLEClient* pClient) override {
        _connected = false;
        Serial.println("[Trigger] Disconnected from sensor node — scanning...");
        NimBLEDevice::getScan()->start(0, nullptr, false);
    }
};

// ── Scan callbacks ─────────────────────────────────────────────────────────
// BUG WAS: strcmp(name, BLE_SENSOR_SERVICE_UUID) — compares name against UUID string (wrong!)
// FIX: match by device name "BlindNav-Sensor" OR by advertising service UUID
class ScanCallbacks : public NimBLEAdvertisedDeviceCallbacks {
    void onResult(NimBLEAdvertisedDevice* advertisedDevice) override {
        bool nameMatch = advertisedDevice->haveName() &&
                         strcmp(advertisedDevice->getName().c_str(), "BlindNav-Sensor") == 0;
        bool svcMatch  = advertisedDevice->isAdvertisingService(NimBLEUUID(BLE_SENSOR_SERVICE_UUID));

        if (!nameMatch && !svcMatch) return;  // not our sensor node

            NimBLEDevice::getScan()->stop();

            _pClient = NimBLEDevice::createClient();
            _pClient->setCallbacks(new ClientCallbacks());

            if (_pClient->connect(advertisedDevice)) {
                NimBLERemoteService* pService = _pClient->getService(BLE_SENSOR_SERVICE_UUID);
                if (pService) {
                    NimBLERemoteCharacteristic* pChar = pService->getCharacteristic(BLE_SENSOR_CHAR_UUID);
                    if (pChar && pChar->canNotify()) {
                        pChar->subscribe(true, notifyCallback);
                        Serial.println("[Trigger] Subscribed to sensor events");
                    }
                }
            }
    }
};

void begin() {
    NimBLEDevice::init("");
    NimBLEScan* pScan = NimBLEDevice::getScan();
    pScan->setAdvertisedDeviceCallbacks(new ScanCallbacks());
    pScan->setActiveScan(true);
    pScan->setInterval(100);
    pScan->setWindow(99);
    pScan->start(0, nullptr, false);  // 0 = scan indefinitely until found
    Serial.println("[Trigger] Scanning for sensor node...");
}

bool triggered()    { return _triggered; }
void clearTrigger() { _triggered = false; }
bool isConnected()  { return _connected; }

} // namespace TriggerListener
