/**
 * tflite_runner.h — TensorFlow Lite Micro Inference Wrapper
 *
 * Encapsulates all TFLite Micro setup: tensor arena allocation,
 * model loading, input tensor population, invoke, output parsing.
 *
 * Usage (in decision task):
 *   if (USE_TINYML && TFLiteRunner::isReady()) {
 *       TFLiteRunner::Result r = TFLiteRunner::infer(window);
 *       // r.classIndex, r.confidence
 *   }
 */
#pragma once
#include <Arduino.h>
#include "../config.h"
#include "../preprocessing/sensor_buffer.h"

// Only compile TFLite code when USE_TINYML is enabled
#if USE_TINYML
#include <TensorFlowLite_ESP32.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "model_data.h"
#endif

namespace TFLiteRunner {

struct Result {
    int   classIndex;   // index into sensor_classes in class_definitions.yaml
    float confidence;   // softmax probability of the top class [0,1]
    bool  valid;        // false if inference failed or confidence < threshold
};

/**
 * Initialize the TFLite Micro interpreter.
 * Call once in setup() AFTER SensorBuffer::begin().
 * @return true on success
 */
bool begin();

/** @return true if begin() succeeded and model is loaded. */
bool isReady();

/**
 * Run inference on a filled window.
 * @param win   The normalized sensor window (must be full)
 * @return      Inference result with class index, confidence, and validity flag
 */
Result infer(const SensorBuffer::Window& win);

} // namespace TFLiteRunner
