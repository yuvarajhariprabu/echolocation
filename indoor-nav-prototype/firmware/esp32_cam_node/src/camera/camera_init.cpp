/**
 * camera_init.cpp — OV2640 Camera Initialization Implementation
 *
 * Uses AI-Thinker fixed pinout (from config.h).
 * Sets up 96×96 grayscale capture to match FOMO model input.
 *
 * PSRAM: AI-Thinker board has 4MB PSRAM (enabled via -DBOARD_HAS_PSRAM
 *        build flag in platformio.ini). The frame buffer lives in PSRAM.
 */
#include "camera_init.h"
#include "../config.h"

namespace CameraInit {

bool begin() {
    camera_config_t config = {};

    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer   = LEDC_TIMER_0;
    config.pin_d0       = CAM_PIN_D0;
    config.pin_d1       = CAM_PIN_D1;
    config.pin_d2       = CAM_PIN_D2;
    config.pin_d3       = CAM_PIN_D3;
    config.pin_d4       = CAM_PIN_D4;
    config.pin_d5       = CAM_PIN_D5;
    config.pin_d6       = CAM_PIN_D6;
    config.pin_d7       = CAM_PIN_D7;
    config.pin_xclk     = CAM_PIN_XCLK;
    config.pin_pclk     = CAM_PIN_PCLK;
    config.pin_vsync    = CAM_PIN_VSYNC;
    config.pin_href     = CAM_PIN_HREF;
    config.pin_sscb_sda = CAM_PIN_SIOD;
    config.pin_sscb_scl = CAM_PIN_SIOC;
    config.pin_pwdn     = CAM_PIN_PWDN;
    config.pin_reset    = CAM_PIN_RESET;

    config.xclk_freq_hz = 20000000;      // 20MHz XCLK
    config.pixel_format = CAM_PIXEL_FORMAT;
    config.frame_size   = CAM_FRAMESIZE;
    config.jpeg_quality = 12;            // unused for grayscale, kept for compat
    config.fb_count     = 1;             // single frame buffer (PSRAM)
    config.fb_location  = CAMERA_FB_IN_PSRAM;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("[Camera] Init failed: 0x%x\n", err);
        return false;
    }

    // Optimize sensor settings for indoor navigation
    sensor_t* s = esp_camera_sensor_get();
    s->set_brightness(s, 1);    // slightly brighter for indoor
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);    // grayscale — saturation irrelevant but safe

    Serial.printf("[Camera] OV2640 initialized: %dx%d grayscale\n",
        FOMO_INPUT_WIDTH, FOMO_INPUT_HEIGHT);
    return true;
}

camera_fb_t* captureFrame() {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("[Camera] Frame capture failed");
    }
    return fb;
}

void returnFrameBuffer(camera_fb_t* fb) {
    if (fb) {
        esp_camera_fb_return(fb);
    }
}

} // namespace CameraInit
