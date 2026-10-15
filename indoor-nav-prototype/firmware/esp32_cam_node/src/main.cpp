/**
 * main.cpp — ESP32-CAM Vision Node Entry Point
 *
 * BLE Architecture (corrected):
 *   - TriggerListener  = GATT CLIENT  → subscribes to sensor node events
 *   - BLEResultServer  = GATT SERVER  → gateway connects to us and subscribes
 *
 * Both NimBLE roles run concurrently on the same stack.
 * TriggerListener::begin() calls NimBLEDevice::init() once.
 * BLEResultServer::begin() adds the server role on the same initialized stack.
 *
 * Privacy rule: raw frames NEVER stored or transmitted.
 *               Only {classIndex, confidence, grid_x, grid_y} leaves this device.
 */

#include <Arduino.h>
#include "config.h"
#include "camera/camera_init.h"
#include "inference/fomo_runner.h"
#include "trigger/trigger_listener.h"
#include "comms/ble_result_server.h"   // ← replaces ble_client.h (wrong BLE topology)

void setup() {
    Serial.begin(115200);
    Serial.println("[CAM] BlindNav Vision Node booting...");

    // BLE CLIENT role: trigger listener (connect to sensor node)
    // This also calls NimBLEDevice::init() — must be FIRST
    TriggerListener::begin();

    // BLE SERVER role: result server (gateway connects to us)
    // Must be after TriggerListener::begin() which initialises NimBLE
    BLEResultServer::begin();

    // Camera init
    if (!CameraInit::begin()) {
        Serial.println("[CAM] FATAL: Camera init failed — check AI-Thinker pinout");
        while (true) delay(1000);  // halt; no point running without camera
    }

    // FOMO model init
    if (!FOMORunner::begin()) {
        Serial.println("[CAM] WARNING: FOMO model not loaded (stub placeholder) — inference disabled");
    }

    Serial.println("[CAM] Ready. Waiting for sensor trigger...");
    Serial.println("[CAM] BLE: scanning for BlindNav-Sensor + advertising for gateway");
}

void loop() {
    // Poll trigger flag (set by BLE notify callback in TriggerListener)
    if (TriggerListener::triggered()) {
        TriggerListener::clearTrigger();

        Serial.println("[CAM] Triggered — capturing frame");

        // Capture one frame
        camera_fb_t* fb = CameraInit::captureFrame();
        if (!fb) {
            Serial.println("[CAM] Frame capture failed — skipping cycle");
        } else {
            // Run FOMO inference
            FOMORunner::Detection det = FOMORunner::infer(fb);

            // IMMEDIATELY return frame buffer — no storage, no transmission of pixels
            CameraInit::returnFrameBuffer(fb);
            fb = nullptr;  // explicitly null to prevent accidental reuse

            // Send only the inference result via GATT notification to gateway
            if (det.valid) {
                Serial.printf("[CAM] Detection: cls=%d conf=%.2f grid=(%d,%d)\n",
                    det.classIndex, det.confidence, det.grid_x, det.grid_y);
                BLEResultServer::sendResult(det.classIndex, det.confidence, det.grid_x, det.grid_y);
            } else {
                Serial.println("[CAM] No detection above confidence threshold");
                // Still notify gateway so it knows cam ran (class=unknown, conf=0)
                BLEResultServer::sendResult(NUM_VISION_CLASSES - 1, 0.0f, 0, 0);
            }
        }
    }

    delay(TRIGGER_CHECK_PERIOD_MS);
}
