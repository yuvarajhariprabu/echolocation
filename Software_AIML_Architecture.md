# Echolocation-Inspired Indoor Navigation — Software & AI/ML Architecture

## 1. High-Level System Split

The project splits into 4 software domains:

1. **Firmware — ESP32-S3 (Sensor Mesh Node)**
2. **Firmware — ESP32-CAM (Vision Node)**
3. **AI/ML Pipeline (offline training + on-device inference runtime)** ← primary focus
4. **Edge/Companion Layer (fusion, mapping, path planning, guidance, 2D map rendering)**

The Edge/Companion layer can live in one of two places depending on your compute budget:
- **On-device (ESP32-S3 does fusion + mapping too)** — leaner, fully embedded, harder to debug
- **Companion app/edge gateway (phone or Raspberry Pi over BLE/Wi-Fi)** — recommended for prototype stage, since fusion + A* + map rendering + audio TTS is heavy for a microcontroller alone. Easiest for a working demo.

Below assumes the **companion-layer approach** (ESP32 nodes = sensing + inference only, phone/gateway = fusion + mapping + guidance + map UI), since that's the most realistic prototype path.

---

## 2. Repository Structure (Top Level)

```
indoor-nav-prototype/
├── firmware/
│   ├── esp32_sensor_node/
│   └── esp32_cam_node/
├── aiml/
│   ├── sensor_model/
│   ├── vision_model/
│   └── shared/
├── edge_gateway/
│   ├── fusion/
│   ├── mapping/
│   ├── planning/
│   ├── guidance/
│   └── comms/
├── app_ui/
│   └── map_viewer/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
└── README.md
```

---

## 3. `firmware/esp32_sensor_node/` — ESP32-S3 Sensor Mesh

```
esp32_sensor_node/
├── platformio.ini
├── src/
│   ├── main.cpp                  # Setup + main loop, task scheduler
│   ├── sensors/
│   │   ├── ultrasonic.cpp/.h     # Reads 3x ultrasonic sensors (trigger/echo timing)
│   │   ├── drop_sensor.cpp/.h    # Reads drop/edge sensor (digital or IR-based)
│   │   ├── imu.cpp/.h            # Gyroscope + accelerometer read (I2C driver, e.g. MPU6050/9250)
│   ├── preprocessing/
│   │   ├── sensor_buffer.cpp/.h  # Sliding window buffer (time-series stacking for 1D CNN input)
│   │   ├── normalize.cpp/.h      # Scaling/normalization to match training preprocessing
│   ├── inference/
│   │   ├── model_data.h          # Auto-generated: TFLite Micro model as a C byte array
│   │   ├── tflite_runner.cpp/.h  # Loads model, runs inference, returns class + confidence
│   ├── comms/
│   │   ├── ble_server.cpp/.h     # Sends classified obstacle events to gateway
│   │   OR
│   │   ├── wifi_client.cpp/.h    # Sends via Wi-Fi (MQTT/HTTP) if BLE range insufficient
│   └── config.h                  # Pin mappings, window size, thresholds, sensor arrangement
└── test/
    └── sensor_unit_tests.cpp     # Bench tests for individual sensor drivers
```

**What each key file actually does:**
- `sensor_buffer.h` — maintains the rolling time-window (e.g., last N samples across all 6 channels: 3 ultrasonic + drop + gyro(x,y,z) + accel(x,y,z)) that gets fed into the 1D CNN each inference cycle.
- `tflite_runner.cpp` — wraps TensorFlow Lite Micro's interpreter: allocates tensor arena, copies buffered window in, runs `Invoke()`, reads output class probabilities.
- `ble_server.cpp` — packages `{class, confidence, distance, direction, timestamp}` into a compact payload sent to the gateway.

---

## 4. `firmware/esp32_cam_node/` — ESP32-CAM Vision Node

```
esp32_cam_node/
├── platformio.ini
├── src/
│   ├── main.cpp                  # Trigger-gated capture loop
│   ├── camera/
│   │   ├── camera_init.cpp/.h    # OV2640/OV5640 config (resolution, format = grayscale/RGB565)
│   │   ├── frame_capture.cpp/.h  # Captures + preprocesses frame (resize, crop, normalize)
│   ├── inference/
│   │   ├── fomo_model_data.h     # FOMO model as C byte array (Edge Impulse export)
│   │   ├── fomo_runner.cpp/.h    # Runs FOMO inference → grid-cell class map output
│   │   ├── mobilenet_model_data.h # Optional secondary confirmation model
│   │   ├── mobilenet_runner.cpp/.h
│   ├── trigger/
│   │   ├── trigger_listener.cpp/.h # Listens for "obstacle detected" signal from ESP32 node
│   ├── comms/
│   │   ├── ble_client.cpp/.h     # Sends {object_class, grid_position, confidence} to gateway
│   └── config.h                  # Camera pins, capture resolution, trigger threshold
└── test/
    └── capture_bench_tests.cpp
```

**Key logic:** `trigger_listener.cpp` keeps the camera idle (power-saving + privacy) until it receives a "something is here" event from the sensor node over BLE — then `frame_capture` grabs one frame, `fomo_runner` classifies it, optionally `mobilenet_runner` confirms low-confidence results.

---

## 5. `aiml/` — This Is Where the Real Engineering Weight Goes

```
aiml/
├── sensor_model/
│   ├── data_collection/
│   │   ├── collect_sensor_data.py     # Serial/BLE logger → timestamped CSV per session
│   │   ├── label_tool.py              # GUI/CLI to label windows (static/moving/drop/etc.)
│   ├── preprocessing/
│   │   ├── windowing.py               # Slices continuous logs into fixed-length windows
│   │   ├── normalize.py               # Per-channel scaling, saved as normalization params
│   │   ├── augment.py                 # Noise injection, time-warping, sensor dropout simulation
│   ├── model/
│   │   ├── model_1dcnn.py             # 1D CNN architecture definition (Keras/PyTorch)
│   │   ├── train.py                   # Training loop, class-weighted loss (handle imbalance)
│   │   ├── evaluate.py                # Confusion matrix, per-class precision/recall
│   ├── export/
│   │   ├── quantize_int8.py           # Post-training INT8 quantization → .tflite
│   │   ├── convert_to_c_array.py      # xxd-style conversion → model_data.h for firmware
│   ├── notebooks/
│   │   └── eda_sensor_patterns.ipynb  # Exploratory analysis: what does "human approaching" look like across 3 ultrasonic + IMU?
│   └── configs/
│       └── train_config.yaml          # Window size, batch size, LR, class list
│
├── vision_model/
│   ├── data_collection/
│   │   ├── capture_indoor_images.py   # Script to pull labeled frames from ESP32-CAM during data-gathering walks
│   │   ├── dataset_curation.py        # Filters/merges public datasets (COCO/Open Images subsets) + your own captures
│   ├── labeling/
│   │   └── edge_impulse_export/       # Labeled dataset in Edge Impulse-compatible format (bounding-box-free, grid-cell labels for FOMO)
│   ├── model/
│   │   ├── fomo_train_config.json     # Edge Impulse project config (or local FOMO impl if not using EI)
│   │   ├── mobilenet_finetune.py      # Transfer learning script for secondary confirmation model
│   ├── export/
│   │   ├── fomo_export.py             # Pulls trained FOMO model, quantizes, converts to C array
│   │   ├── mobilenet_export.py
│   └── evaluation/
│       └── confusion_matrix_vision.py # Per-class accuracy: person/chair/table/door/stairs/wall
│
└── shared/
    ├── metrics.py                     # Shared eval utilities (F1, latency benchmarking on-device)
    ├── model_registry.md              # Version log: which model version is deployed where, accuracy, size, latency
    └── class_definitions.yaml         # Single source of truth for class labels (used by both firmware + training to stay in sync)
```

**Why this AI/ML structure is "extreme":**
- **Separate data collection pipelines** per model — sensor data collection is a walking/logging exercise, vision data collection is a labeled-image exercise; keeping them independent avoids pipeline confusion.
- **`class_definitions.yaml` as single source of truth** — prevents drift between what firmware expects and what the model was trained on (a very common real-world bug: firmware hardcodes class index 3 = "chair" but retrained model reorders classes).
- **`model_registry.md`** — tracks every trained model version, its accuracy/size/latency trade-off, and which firmware build it's flashed to — critical once you start iterating on model versions across two separate hardware nodes.
- **Augmentation step for sensor data** (`augment.py`) — sensor time-series data is much harder to collect at scale than images, so synthetic augmentation (noise, time-warp, simulated sensor dropout) matters more here than people usually expect.

---

## 6. `edge_gateway/` — Fusion, Mapping, Planning, Guidance

```
edge_gateway/
├── main.py                            # Orchestrates the full pipeline loop
├── fusion/
│   ├── ble_receiver.py                # Listens for events from both ESP32 nodes
│   ├── fusion_engine.py               # Combines sensor-node class + cam-node class + IMU heading → unified obstacle object
│   ├── event_schema.py                # Defines the fused object data structure
├── mapping/
│   ├── tile_grid.py                   # Grid data structure: occupied/free/unknown per tile
│   ├── localization.py                # Dead-reckoning position update from IMU between sensor updates
│   ├── grid_updater.py                # Applies fused obstacle events onto the tile grid
│   ├── dynamic_object_tracker.py      # Separate overlay layer for humans/moving objects, with decay (temporary occupancy fades over time)
├── planning/
│   ├── astar.py                       # A* pathfinding over the tile grid
│   ├── replanning_trigger.py          # Detects when replanning is needed (new obstacle, deviation)
├── guidance/
│   ├── decision_engine.py             # Converts path + fused obstacle data → guidance cues
│   ├── audio_feedback.py              # TTS/tone generation → sent to Bluetooth headphone
│   ├── haptic_feedback.py             # Vibration pattern generator → sent to 3 motors (direction encoding)
├── comms/
│   ├── ble_gateway.py                 # BLE central role, talks to both ESP32 nodes
│   ├── audio_output.py                # Bluetooth audio sink handling
│   └── map_stream.py                  # Pushes live map state to app_ui/ over WebSocket
└── config/
    └── gateway_config.yaml            # Tile size (cm per tile), motor mapping, audio voice settings
```

---

## 7. `app_ui/map_viewer/` — Live 2D Map Display (for sighted assistant/debugging/demo)

```
map_viewer/
├── index.html
├── src/
│   ├── grid_renderer.js               # Draws tile grid (occupied/free)
│   ├── user_marker.js                 # Renders user position + direction-of-vision arrow/cone
│   ├── dynamic_overlay.js             # Renders moving objects distinct from static obstacles
│   ├── path_overlay.js                # Draws current A* route
│   └── ws_client.js                   # Connects to gateway's map_stream.py over WebSocket
└── style.css
```

---

## 8. `data/` and `docs/`

```
data/
├── raw/            # Untouched logged sensor sessions + captured images
└── processed/       # Windowed/labeled/normalized datasets ready for training

docs/
├── architecture_diagram.png
├── class_definitions.md
├── hardware_wiring.md
└── model_training_log.md
```

---

## 9. Suggested Build Order

1. `firmware/esp32_sensor_node` (raw sensor read + BLE send, no ML yet) → validate hardware
2. `aiml/sensor_model` data collection → label → train v1 1D CNN → deploy to node
3. `firmware/esp32_cam_node` (raw capture + BLE send, no ML yet)
4. `aiml/vision_model` data collection → train FOMO → deploy to cam node
5. `edge_gateway/fusion` + `mapping` — get the tile grid updating live from both nodes
6. `edge_gateway/planning` — A* on top of working grid
7. `edge_gateway/guidance` — audio + haptic output
8. `app_ui/map_viewer` — for demoing/debugging (not for the end user, but essential for showing judges/evaluators the live map)

This order front-loads the AI/ML work (steps 2 and 4) right after basic hardware validation, since those models are the highest-risk, highest-effort components and everything downstream (fusion, mapping, guidance) depends on their output quality.
