/**
 * camera_init.h — OV2640 Camera Initialization (AI-Thinker ESP32-CAM)
 */
#pragma once
#include <Arduino.h>
#include "esp_camera.h"

namespace CameraInit {

/**
 * Initialize the OV2640 camera with the configuration from config.h.
 * Must be called before any frame capture.
 * @return true on success, false on hardware failure.
 */
bool begin();

/**
 * Return the current frame buffer (caller must call returnFrameBuffer after use).
 * @return Pointer to camera_fb_t, or nullptr if capture failed.
 */
camera_fb_t* captureFrame();

/** Return a frame buffer obtained from captureFrame() back to the driver. */
void returnFrameBuffer(camera_fb_t* fb);

} // namespace CameraInit
