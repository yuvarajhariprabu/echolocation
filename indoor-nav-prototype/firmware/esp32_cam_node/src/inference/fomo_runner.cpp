/**
 * fomo_runner.cpp — FOMO Inference Runner Implementation
 *
 * FOMO model I/O:
 *   Input:  [1, H, W, 1]  float32 normalized grayscale (0.0–1.0)
 *   Output: [1, H/8, W/8, NUM_VISION_CLASSES]  activation grid
 *           Each cell (r,c,cls) = confidence that class `cls` is at grid cell (r,c)
 *
 * We scan the output grid for the peak activation across all classes,
 * then return its class, position, and confidence.
 *
 * Critical privacy rule: the frame buffer is read ONCE into the input tensor,
 * then immediately returned to the camera driver. It is never written to
 * flash or a network socket.
 */
#include "fomo_runner.h"
#include "../config.h"
#include "fomo_model_data.h"

#include <TensorFlowLite_ESP32.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace FOMORunner {

static tflite::MicroErrorReporter  _error_reporter;
static tflite::AllOpsResolver      _resolver;
static const tflite::Model*        _model  = nullptr;
static tflite::MicroInterpreter*   _interp = nullptr;
static uint8_t _arena[FOMO_TFLITE_ARENA_SIZE];
static bool    _ready = false;

bool begin() {
    _model = tflite::GetModel(g_fomo_model_data);
    if (_model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("[FOMO] Schema mismatch!");
        return false;
    }
    static tflite::MicroInterpreter interp(
        _model, _resolver, _arena, FOMO_TFLITE_ARENA_SIZE, &_error_reporter
    );
    _interp = &interp;
    if (_interp->AllocateTensors() != kTfLiteOk) {
        Serial.println("[FOMO] AllocateTensors failed");
        return false;
    }
    _ready = true;
    Serial.println("[FOMO] Model loaded OK");
    return true;
}

Detection infer(camera_fb_t* fb) {
    Detection result = {NUM_VISION_CLASSES - 1, 0.0f, 0, 0, false};
    if (!_ready || !fb) return result;

    // ── Populate input tensor from frame buffer ─────────────────────────────
    // Frame is FRAMESIZE_96X96 grayscale: fb->buf[0..96*96-1] = 0..255 uint8
    TfLiteTensor* input = _interp->input(0);
    const int pixels = FOMO_INPUT_WIDTH * FOMO_INPUT_HEIGHT;

    if (input->type == kTfLiteFloat32) {
        for (int i = 0; i < pixels; i++) {
            input->data.f[i] = (float)fb->buf[i] / 255.0f;
        }
    } else if (input->type == kTfLiteInt8) {
        // INT8 quantized: scale = 1/128, zero_point = -128
        for (int i = 0; i < pixels; i++) {
            // Normalize [0,255] → [-128, 127] for INT8 input
            input->data.int8[i] = (int8_t)((int)fb->buf[i] - 128);
        }
    }
    // Frame buffer contents are no longer needed — return it immediately
    // (caller still owns fb, but we've finished reading it)

    // ── Run inference ────────────────────────────────────────────────────────
    if (_interp->Invoke() != kTfLiteOk) {
        Serial.println("[FOMO] Invoke failed");
        return result;
    }

    // ── Scan output grid for peak activation ─────────────────────────────────
    // Output: [1, GRID_H, GRID_W, NUM_VISION_CLASSES]
    // GRID = input_size / 8 for FOMO (96/8 = 12×12 grid)
    TfLiteTensor* output = _interp->output(0);
    const int grid_h   = output->dims->data[1];
    const int grid_w   = output->dims->data[2];
    const int n_cls    = output->dims->data[3];

    float peak_conf = VISION_CONFIDENCE_MIN;
    int   peak_cls  = -1;
    int   peak_r    = 0;
    int   peak_c    = 0;

    for (int r = 0; r < grid_h; r++) {
        for (int c = 0; c < grid_w; c++) {
            for (int cls = 0; cls < n_cls && cls < NUM_VISION_CLASSES; cls++) {
                float val;
                int idx = (r * grid_w + c) * n_cls + cls;
                if (output->type == kTfLiteFloat32) {
                    val = output->data.f[idx];
                } else {
                    // Dequantize INT8: val = (int8 - zero_point) * scale
                    val = ((float)(output->data.int8[idx] - output->params.zero_point))
                          * output->params.scale;
                }
                if (val > peak_conf) {
                    peak_conf = val;
                    peak_cls  = cls;
                    peak_r    = r;
                    peak_c    = c;
                }
            }
        }
    }

    if (peak_cls >= 0) {
        result.classIndex  = peak_cls;
        result.confidence  = peak_conf;
        result.grid_x      = peak_c;
        result.grid_y      = peak_r;
        result.valid       = true;
    }
    return result;
}

} // namespace FOMORunner
