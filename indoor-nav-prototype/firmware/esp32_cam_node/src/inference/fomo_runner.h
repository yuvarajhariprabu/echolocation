/**
 * fomo_runner.h — FOMO Inference Runner (ESP32-CAM)
 *
 * Runs a FOMO (Faster Objects, More Objects) TFLite Micro model on a
 * captured camera frame. FOMO outputs a grid-cell activation map rather
 * than bounding boxes, which maps naturally onto our tile grid.
 *
 * Raw frames NEVER leave this device. Only the inference result
 * (class + grid position + confidence) is transmitted over BLE.
 */
#pragma once
#include <Arduino.h>
#include "esp_camera.h"

namespace FOMORunner {

struct Detection {
    int   classIndex;   // vision class index (0–6, see class_definitions.yaml)
    float confidence;   // peak activation strength [0,1]
    int   grid_x;       // column in FOMO output grid
    int   grid_y;       // row in FOMO output grid
    bool  valid;        // false if no detection above threshold
};

/**
 * Initialize TFLite Micro interpreter for the FOMO model.
 * @return true on success.
 */
bool begin();

/**
 * Run inference on a captured frame.
 * The frame buffer is read, preprocessed (normalize pixel values),
 * fed into the model, and the highest-activation cell is returned.
 *
 * The frame buffer itself is NOT stored or transmitted.
 *
 * @param fb     Camera frame buffer from CameraInit::captureFrame()
 * @return       Top detection result
 */
Detection infer(camera_fb_t* fb);

} // namespace FOMORunner
