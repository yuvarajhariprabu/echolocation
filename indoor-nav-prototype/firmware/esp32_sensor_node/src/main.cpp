/**
 * main.cpp — ESP32 Sensor Node Entry Point
 *
 * Architecture:
 *   Core 0: sensorTask   — polls HC-SR04 × 3, VL53L0X, MPU6050 at 20Hz
 *                          normalizes readings, pushes to SensorBuffer
 *   Core 1: decisionTask — reads from SensorBuffer, runs TFLite inference
 *                          (or rule-based fallback), drives haptics + BLE
 *
 * Shared state is protected by a FreeRTOS mutex.
 *
 * FAST PATH (design rule #1):
 *   Drop-off and near-obstacle alerts trigger haptic feedback immediately
 *   inside the decision task WITHOUT waiting on BLE send or camera pipeline.
 *
 * BUILD MODES:
 *   USE_TINYML=0 (default): rule-based obstacle detection (threshold on cm values)
 *   USE_TINYML=1:           1D CNN inference from model_data.h
 */

#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "sensors/ultrasonic.h"
#include "sensors/drop_sensor.h"
#include "sensors/imu.h"
#include "preprocessing/sensor_buffer.h"
#include "preprocessing/normalize.h"
#include "inference/tflite_runner.h"
#include "comms/ble_server.h"

// ─── Shared state ───────────────────────────────────────────────────────────
struct SharedState {
    float front_cm, left_cm, right_cm;
    uint16_t floor_mm;
    bool dropoff;
    IMU::State imu;
    int  classIndex;     // latest sensor model output (or rule-based)
    float confidence;
    unsigned long ts;
};

static SharedState g_state;
static SemaphoreHandle_t g_mutex;

// ─── PWM helpers ────────────────────────────────────────────────────────────
static void hapticSetup() {
    ledcSetup(CH_HAPTIC_FRONT, PWM_FREQ_HZ, PWM_RES_BITS);
    ledcAttachPin(HAPTIC_FRONT, CH_HAPTIC_FRONT);
    ledcSetup(CH_HAPTIC_LEFT,  PWM_FREQ_HZ, PWM_RES_BITS);
    ledcAttachPin(HAPTIC_LEFT,  CH_HAPTIC_LEFT);
    ledcSetup(CH_HAPTIC_RIGHT, PWM_FREQ_HZ, PWM_RES_BITS);
    ledcAttachPin(HAPTIC_RIGHT, CH_HAPTIC_RIGHT);
    ledcSetup(CH_AUDIO, AUDIO_FREQ_HZ, 10);
    ledcAttachPin(AUDIO_PIN, CH_AUDIO);
}

enum AlertZone { NONE, WARN, NEAR };

static AlertZone classifyDist(float cm) {
    if (cm < 0)                  return NONE;  // out of range = clear
    if (cm < OBSTACLE_NEAR_CM)   return NEAR;
    if (cm < OBSTACLE_WARN_CM)   return WARN;
    return NONE;
}

static void setHaptic(int ch, AlertZone zone) {
    switch (zone) {
        case NEAR: ledcWrite(ch, 255); break;
        case WARN: ledcWrite(ch, 90);  break;
        default:   ledcWrite(ch, 0);   break;
    }
}

static void playDropoffAlert() {
    // Distinct triple-beep — must be unambiguously different from obstacle haptics
    for (int i = 0; i < 3; i++) {
        ledcWriteTone(CH_AUDIO, 2000);
        delay(80);
        ledcWriteTone(CH_AUDIO, 0);
        delay(80);
    }
}

// ─── Sensor Task (Core 0) ───────────────────────────────────────────────────
static void sensorTask(void* /*param*/) {
    const TickType_t period  = pdMS_TO_TICKS(SENSOR_TASK_PERIOD_MS);
    TickType_t       lastWake = xTaskGetTickCount();
    unsigned long    lastMs   = millis();

    for (;;) {
        unsigned long now = millis();
        float dt = (lastMs == 0) ? 0.05f : (float)(now - lastMs) / 1000.0f;
        if (dt <= 0.0f) dt = 0.001f;
        lastMs = now;

        // 1. Read sensors
        float f, l, r;
        Ultrasonic::readAll(f, l, r);

        uint16_t floor_mm = 0;
        DropSensor::read(floor_mm);

        IMU::State imu_state;
        IMU::update(dt, imu_state);

        // 2. If head orientation invalid, mark ultrasonics as invalid
        if (!imu_state.orientation_valid) {
            f = l = r = -1.0f;
        }

        // 3. Normalize and push to sliding window buffer
        SensorBuffer::Sample sample;
        Normalize::normalize(
            f, l, r,
            (float)floor_mm,
            imu_state.gyro_x, imu_state.gyro_y, imu_state.gyro_z,
            imu_state.accel_x, imu_state.accel_y,
            sample
        );
        SensorBuffer::push(sample);

        // 4. Update shared state
        if (xSemaphoreTake(g_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            g_state.front_cm = f;
            g_state.left_cm  = l;
            g_state.right_cm = r;
            g_state.floor_mm = floor_mm;
            g_state.dropoff  = DropSensor::isDropoff(floor_mm);
            g_state.imu      = imu_state;
            g_state.ts       = now;
            xSemaphoreGive(g_mutex);
        }

        vTaskDelayUntil(&lastWake, period);
    }
}

// ─── Decision Task (Core 1) ─────────────────────────────────────────────────
static void decisionTask(void* /*param*/) {
    const TickType_t period  = pdMS_TO_TICKS(DECISION_TASK_PERIOD_MS);
    TickType_t       lastWake = xTaskGetTickCount();

    for (;;) {
        // Snapshot shared state
        SharedState local;
        if (xSemaphoreTake(g_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            local = g_state;
            xSemaphoreGive(g_mutex);
        }

        // ── FAST PATH: Drop-off (design rule #1) ───────────────────────────
        // Immediate haptic — does NOT wait on ML inference or BLE
        if (local.dropoff) {
            playDropoffAlert();
        }

        // ── Classification ──────────────────────────────────────────────────
        int   classIdx = NUM_SENSOR_CLASSES - 1;  // default: unknown
        float conf     = 0.0f;

#if USE_TINYML
        SensorBuffer::Window win;
        if (TFLiteRunner::isReady() && SensorBuffer::getWindow(win)) {
            auto result = TFLiteRunner::infer(win);
            if (result.valid) {
                classIdx = result.classIndex;
                conf     = result.confidence;
            }
        }
#else
        // Rule-based fallback (pre-ML mode)
        // Uses IMU stationary flag to disambiguate user motion from external changes
        AlertZone zF = classifyDist(local.front_cm);
        AlertZone zL = classifyDist(local.left_cm);
        AlertZone zR = classifyDist(local.right_cm);

        if (local.imu.stationary) {
            // Distance changes can't be the user → external object
            if (zF == NEAR || zL == NEAR || zR == NEAR) {
                classIdx = 0;   // static_obstacle (near)
                conf     = 0.9f;
            } else if (zF == WARN || zL == WARN || zR == WARN) {
                classIdx = 0;   // static_obstacle (warn)
                conf     = 0.7f;
            } else {
                classIdx = 2;   // open_space
                conf     = 0.9f;
            }
        } else {
            // User is moving — distance changes may be due to user motion
            classIdx = 7;  // user_motion
            conf     = 0.8f;
        }

        // Override: drop-off takes priority regardless
        if (local.dropoff) {
            classIdx = 3;  // dropoff_edge
            conf     = 1.0f;
        }
#endif

        // ── Haptic feedback (directional) ───────────────────────────────────
        if (!local.dropoff) {  // dropoff already handled in fast path above
            setHaptic(CH_HAPTIC_FRONT, classifyDist(local.front_cm));
            setHaptic(CH_HAPTIC_LEFT,  classifyDist(local.left_cm));
            setHaptic(CH_HAPTIC_RIGHT, classifyDist(local.right_cm));
        }

        // ── BLE send ─────────────────────────────────────────────────────────
        BLEServer::sendEvent(
            classIdx, conf,
            local.front_cm, local.left_cm, local.right_cm,
            local.floor_mm, local.imu.yaw_rate_dps,
            local.imu.stationary
        );

        // Update shared class output
        if (xSemaphoreTake(g_mutex, pdMS_TO_TICKS(5)) == pdTRUE) {
            g_state.classIndex  = classIdx;
            g_state.confidence  = conf;
            xSemaphoreGive(g_mutex);
        }

        vTaskDelayUntil(&lastWake, period);
    }
}

// ─── Setup ──────────────────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("[Main] BlindNav Sensor Node booting...");

    // I2C bus (shared by VL53L0X + MPU6050)
    Wire.begin(I2C_SDA, I2C_SCL);

    // Sensor init
    Ultrasonic::begin();

    if (!DropSensor::begin()) {
        Serial.println("[Main] WARNING: Drop sensor not available");
    } else {
        DropSensor::calibrate();  // baseline floor reading
    }

    if (!IMU::begin()) {
        Serial.println("[Main] WARNING: IMU not available");
    }

    // Preprocessing
    SensorBuffer::begin();

    // TFLite (no-op when USE_TINYML=0)
#if USE_TINYML
    if (!TFLiteRunner::begin()) {
        Serial.println("[Main] WARNING: TFLite init failed — falling back to rules");
    }
#endif

    // PWM / haptics
    hapticSetup();

    // BLE
    BLEServer::begin();

    // FreeRTOS shared state
    g_mutex = xSemaphoreCreateMutex();
    memset(&g_state, 0, sizeof(g_state));

    // Launch tasks
    xTaskCreatePinnedToCore(sensorTask,   "sensorTask",   SENSOR_TASK_STACK,   nullptr, SENSOR_TASK_PRIORITY,   nullptr, SENSOR_TASK_CORE);
    xTaskCreatePinnedToCore(decisionTask, "decisionTask", DECISION_TASK_STACK, nullptr, DECISION_TASK_PRIORITY, nullptr, DECISION_TASK_CORE);

    Serial.println("[Main] Tasks launched. Running.");
}

void loop() {
    // All work happens in FreeRTOS tasks
    vTaskDelay(pdMS_TO_TICKS(1000));
}
