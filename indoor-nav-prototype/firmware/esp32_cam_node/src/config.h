/**
 * config.h — ESP32-CAM Vision Node Configuration
 *
 * AI-Thinker ESP32-CAM board pin layout.
 * DO NOT change camera pins — they are fixed by the AI-Thinker PCB layout.
 */
#pragma once

// ─── Camera (OV2640 — AI-Thinker fixed pinout) ─────────────────────────────
// Reference: https://github.com/espressif/esp32-camera/blob/master/examples/
//            camera_example/main/take_picture.c  (AI-Thinker configuration)
#define CAM_PIN_PWDN     32
#define CAM_PIN_RESET    -1   // tied to 3.3V on AI-Thinker board
#define CAM_PIN_XCLK      0
#define CAM_PIN_SIOD     26   // I2C SDA for camera
#define CAM_PIN_SIOC     27   // I2C SCL for camera
// Data bus: D7..D0 = Y9..Y2 in esp32-camera driver terminology
#define CAM_PIN_D7       35   // Y9
#define CAM_PIN_D6       34   // Y8
#define CAM_PIN_D5       39   // Y7
#define CAM_PIN_D4       36   // Y6  ← was 38 (WRONG)
#define CAM_PIN_D3       21   // Y5  ← was 37 (WRONG)
#define CAM_PIN_D2       19   // Y4  ← was 36 (WRONG)
#define CAM_PIN_D1       18   // Y3  ← was 21 (WRONG)
#define CAM_PIN_D0        5   // Y2  ← was 19 (WRONG)
#define CAM_PIN_VSYNC    25
#define CAM_PIN_HREF     23
#define CAM_PIN_PCLK     22

// Capture resolution for FOMO (must match Edge Impulse project input size)
// FOMO typically uses 96×96. Adjust if your EI project uses a different size.
#define FOMO_INPUT_WIDTH   96
#define FOMO_INPUT_HEIGHT  96

// JPEG quality (not used for FOMO — we capture raw RGB/grayscale)
// Keep FRAMESIZE_96X96 for FOMO; upgrade only for data collection mode
#define CAM_FRAMESIZE    FRAMESIZE_96X96
#define CAM_PIXEL_FORMAT PIXFORMAT_GRAYSCALE

// ─── BLE ───────────────────────────────────────────────────────────────────
// UUIDs — must match the sensor node's BLE_SERVICE_UUID for trigger detection
// AND must match gateway's ble_gateway.py cam UUIDs
#define BLE_DEVICE_NAME          "BlindNav-CAM"
#define BLE_SENSOR_SERVICE_UUID  "4A98C7D2-1E3F-4B6A-8D5C-2F9E0A7B3C1D"  // sensor node service to listen to
#define BLE_SENSOR_CHAR_UUID     "5B09D8E3-2F40-5C7B-9E6D-3A0F1B8C4D2E"  // char to subscribe for trigger
#define BLE_CAM_SERVICE_UUID     "6C10E9F4-3B51-6D8C-AF7E-4A1B2C9D5E3F"  // our service UUID
#define BLE_CAM_RESULT_CHAR_UUID "7D21FA25-4B62-7E9D-BE8F-5C2A3D0E6F4B"  // result characteristic

// ─── Trigger ───────────────────────────────────────────────────────────────
// Sensor node classes that trigger a camera capture (match sensor class indices)
// 0=static_obstacle, 1=moving_object, 4=approaching, 6=crossing
#define TRIGGER_ON_CLASSES       {0, 1, 4, 6}
#define TRIGGER_CONFIDENCE_MIN   0.65f   // only trigger if sensor confidence >= this

// ─── FOMO Inference ────────────────────────────────────────────────────────
#define NUM_VISION_CLASSES    7          // person/chair/table/door/stairs/wall/unknown
#define FOMO_TFLITE_ARENA_SIZE  (64 * 1024)   // 64KB — FOMO is slightly heavier
#define VISION_CONFIDENCE_MIN 0.65f

// ─── Task Scheduling ───────────────────────────────────────────────────────
#define TRIGGER_CHECK_PERIOD_MS  20     // Poll trigger every 20ms
#define CAM_TASK_STACK          8192    // Camera + PSRAM ops need more stack
#define CAM_TASK_PRIORITY          2
