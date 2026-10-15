/**
 * tflite_runner.cpp — TensorFlow Lite Micro Inference Implementation
 *
 * When USE_TINYML=0: all public functions are no-ops / return false.
 * When USE_TINYML=1: loads model_data.h, allocates tensor arena, runs inference.
 *
 * The tensor arena is statically allocated (TFLITE_ARENA_SIZE from config.h).
 * If you see "Arena too small" errors, increase TFLITE_ARENA_SIZE.
 */
#include "tflite_runner.h"

namespace TFLiteRunner {

#if USE_TINYML

static tflite::MicroErrorReporter  _error_reporter;
static tflite::AllOpsResolver      _resolver;
static const tflite::Model*        _model   = nullptr;
static tflite::MicroInterpreter*   _interp  = nullptr;
static uint8_t _arena[TFLITE_ARENA_SIZE];
static bool    _ready = false;

bool begin() {
    _model = tflite::GetModel(g_model_data);  // g_model_data from model_data.h
    if (_model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.println("[TFLite] Model schema version mismatch!");
        return false;
    }

    static tflite::MicroInterpreter static_interp(
        _model, _resolver, _arena, TFLITE_ARENA_SIZE, &_error_reporter
    );
    _interp = &static_interp;

    if (_interp->AllocateTensors() != kTfLiteOk) {
        Serial.println("[TFLite] AllocateTensors failed — increase TFLITE_ARENA_SIZE");
        return false;
    }

    Serial.printf("[TFLite] Model loaded. Input tensor: [1, %d, %d]\n",
        SENSOR_WINDOW_SIZE, SENSOR_CHANNELS);
    _ready = true;
    return true;
}

bool isReady() { return _ready; }

Result infer(const SensorBuffer::Window& win) {
    Result r = {NUM_SENSOR_CLASSES - 1, 0.0f, false};  // default: unknown
    if (!_ready) return r;

    // Copy window into input tensor
    TfLiteTensor* input = _interp->input(0);
    // Input shape expected: [1, SENSOR_WINDOW_SIZE, SENSOR_CHANNELS]
    const int expected_size = SENSOR_WINDOW_SIZE * SENSOR_CHANNELS;
    if (input->bytes != expected_size * sizeof(float)) {
        Serial.println("[TFLite] Input tensor size mismatch!");
        return r;
    }
    memcpy(input->data.f, win.data, expected_size * sizeof(float));

    // Run inference
    if (_interp->Invoke() != kTfLiteOk) {
        Serial.println("[TFLite] Invoke() failed");
        return r;
    }

    // Parse output: softmax probabilities over NUM_SENSOR_CLASSES
    TfLiteTensor* output = _interp->output(0);
    float max_conf = -1.0f;
    int   max_idx  = NUM_SENSOR_CLASSES - 1;  // default to unknown

    for (int i = 0; i < NUM_SENSOR_CLASSES; i++) {
        float prob = output->data.f[i];
        if (prob > max_conf) {
            max_conf = prob;
            max_idx  = i;
        }
    }

    // Confidence gate: below threshold → report "unknown" (class 8)
    if (max_conf < CONFIDENCE_THRESHOLD) {
        r.classIndex  = NUM_SENSOR_CLASSES - 1;  // unknown
        r.confidence  = max_conf;
        r.valid       = true;
    } else {
        r.classIndex  = max_idx;
        r.confidence  = max_conf;
        r.valid       = true;
    }

    return r;
}

#else  // USE_TINYML == 0 — stub implementations

bool begin()              { return false; }
bool isReady()            { return false; }
Result infer(const SensorBuffer::Window&) {
    return {NUM_SENSOR_CLASSES - 1, 0.0f, false};
}

#endif

} // namespace TFLiteRunner
