# Build Prompt: Echolocation-Inspired Indoor Navigation Prototype

Use this prompt as-is with a coding assistant (e.g., Claude Code) in VS Code to start building the project. It consolidates the full architecture, requirements, and constraints from planning.

---

## PROMPT START

I'm building a software/AI-dominant prototype for an **echolocation-inspired indoor navigation system for visually impaired people**. I want you to help me build this out in VS Code, following the exact architecture below. Work folder by folder, starting with the build order at the end. Ask me before making assumptions on anything not specified here.

### Project Goal
A wearable prototype that helps a visually impaired user navigate indoor spaces by continuously building a live 2D tile-grid map (occupied/free tiles), identifying static obstacles and moving humans, planning a safe route, and guiding the user via audio and haptic feedback. The system must NOT rely on continuous camera capture — it must be privacy-conscious, using the camera only when triggered.

### Hardware
- **ESP32-S3 (Sensor Node):** 3x ultrasonic distance sensors, 1x drop/edge sensor, 1x gyroscope, 1x accelerometer (IMU)
- **ESP32-CAM (Vision Node):** camera module (OV2640/OV5640), triggered by the sensor node, not continuously active
- **Output:** Bluetooth headphone (audio feedback) + 3 vibration motors (directional haptic feedback)
- Communication between nodes and gateway: BLE (fallback: Wi-Fi if BLE range is insufficient)

### AI/ML Models (this is the core focus — build with care)

**Model 1 — Sensor/Spatial Model (runs on ESP32-S3):**
- Architecture: lightweight 1D CNN
- Input: sliding time-window of 3x ultrasonic + drop sensor + gyroscope (x,y,z) + accelerometer (x,y,z) readings
- Output classes: static obstacle, moving object/possible human, open space, drop-off/edge, approaching/receding/crossing object, user-motion (not environment change), unknown/uncertain
- Critical requirement: must use IMU data to disambiguate "user turned/moved" vs. "an external object actually moved" — do not treat raw ultrasonic distance changes as ground truth for object motion without checking IMU state first
- Quantization: INT8, exported as a TFLite Micro C byte array for embedding in firmware
- Must include a confidence output per prediction, not just a class label

**Model 2 — Vision/Semantic Model (runs on ESP32-CAM):**
- Architecture: FOMO (Faster Objects, More Objects), trained via Edge Impulse — chosen because its grid-cell output maps directly onto our tile-grid map (not full bounding boxes, which would be too heavy for this hardware)
- Trigger-gated: camera stays idle and only captures/runs inference when signaled by the sensor node's obstacle detection — this is both a power-saving and privacy design choice
- Output classes (indoor-navigation relevant, not general-purpose): person, chair, table, door/doorway, stairs, wall/obstruction, unknown object
- Output includes grid-cell position within frame + confidence
- Quantization: INT8, exported as a TFLite Micro C byte array
- Critical requirement: raw camera frames must NEVER be stored or transmitted off the ESP32-CAM — only the classification result (label + grid position + confidence) leaves the device

**Fusion rule (in the gateway, not on either ESP32 node):**
- Combine sensor-node classification + camera-node classification + IMU heading into one fused obstacle object: `{distance, direction, class, semantic_label, confidence}`
- If either model's confidence is below a defined threshold, OR if the two models disagree, do NOT assert a specific instruction — fall back to a generic caution alert instead. Safety over specificity, always.

### Software Architecture — Follow This Exact Folder Structure

```
indoor-nav-prototype/
├── firmware/
│   ├── esp32_sensor_node/        # PlatformIO project, ESP32-S3
│   │   ├── platformio.ini
│   │   └── src/
│   │       ├── main.cpp
│   │       ├── sensors/          # ultrasonic.cpp/.h, drop_sensor.cpp/.h, imu.cpp/.h
│   │       ├── preprocessing/    # sensor_buffer.cpp/.h, normalize.cpp/.h
│   │       ├── inference/        # model_data.h, tflite_runner.cpp/.h
│   │       ├── comms/            # ble_server.cpp/.h (or wifi_client.cpp/.h)
│   │       └── config.h
│   └── esp32_cam_node/           # PlatformIO project, ESP32-CAM
│       ├── platformio.ini
│       └── src/
│           ├── main.cpp
│           ├── camera/           # camera_init.cpp/.h, frame_capture.cpp/.h
│           ├── inference/        # fomo_model_data.h, fomo_runner.cpp/.h
│           ├── trigger/          # trigger_listener.cpp/.h
│           ├── comms/            # ble_client.cpp/.h
│           └── config.h
├── aiml/
│   ├── sensor_model/
│   │   ├── data_collection/      # collect_sensor_data.py, label_tool.py
│   │   ├── preprocessing/        # windowing.py, normalize.py, augment.py
│   │   ├── model/                # model_1dcnn.py, train.py, evaluate.py
│   │   ├── export/               # quantize_int8.py, convert_to_c_array.py
│   │   └── configs/              # train_config.yaml
│   ├── vision_model/
│   │   ├── data_collection/      # capture_indoor_images.py, dataset_curation.py
│   │   ├── labeling/             # edge_impulse_export/
│   │   ├── model/                # fomo_train_config.json, mobilenet_finetune.py (optional confirmation model)
│   │   ├── export/                # fomo_export.py
│   │   └── evaluation/           # confusion_matrix_vision.py
│   └── shared/
│       ├── metrics.py
│       ├── model_registry.md
│       └── class_definitions.yaml   # single source of truth for class labels used by BOTH firmware and training
├── edge_gateway/                 # Python; runs on companion device (phone/RPi) for prototype stage
│   ├── main.py
│   ├── fusion/                   # ble_receiver.py, fusion_engine.py, event_schema.py
│   ├── mapping/                  # tile_grid.py, localization.py, grid_updater.py, dynamic_object_tracker.py
│   ├── planning/                 # astar.py, replanning_trigger.py
│   ├── guidance/                 # decision_engine.py, audio_feedback.py, haptic_feedback.py
│   ├── comms/                    # ble_gateway.py, audio_output.py, map_stream.py
│   └── config/                   # gateway_config.yaml
├── app_ui/
│   └── map_viewer/                # HTML/JS/CSS: live tile-grid map + user heading arrow + dynamic object overlay + path overlay, via WebSocket from map_stream.py
├── data/
│   ├── raw/
│   └── processed/
└── docs/
```

### Non-Negotiable Design Rules
1. **Fast path vs. slow path:** Immediate hazard alerts (close obstacle, drop-off) must come directly from the ultrasonic+IMU path and trigger haptic feedback WITHOUT waiting on the camera/FOMO pipeline. The camera only enriches guidance with semantic detail afterward — it must never be on the critical safety-latency path.
2. **Confidence-gated guidance:** Never issue a specific/confident instruction from a single low-confidence source. Default to a generic caution alert when uncertain.
3. **No raw image persistence:** The ESP32-CAM node must not write captured frames to storage or transmit them anywhere — only inference output leaves that node.
4. **Class label consistency:** `class_definitions.yaml` in `aiml/shared/` is the single source of truth for class names/indices — firmware, training scripts, and gateway fusion logic must all reference it, not hardcode class indices separately.
5. **Ultrasonic sensors must be time-multiplexed** (fired sequentially, not simultaneously) to avoid cross-talk interference.
6. **Tile grid must track three separate layers:** static occupancy, dynamic (human/moving object, with decay over time), and the user's live position + heading (direction of vision).

### Tooling
- Build everything in **VS Code**, using the **PlatformIO extension** for both firmware projects (not Arduino IDE — the modular multi-file structure above needs PlatformIO).
- Python side (`aiml/`, `edge_gateway/`) uses the VS Code Python extension; Jupyter extension for any exploratory notebooks.
- `app_ui/map_viewer/` is plain HTML/JS/CSS, previewed with Live Server.

### Build Order (follow this sequence, confirm each stage works before moving to the next)
1. `firmware/esp32_sensor_node` — raw sensor reads (ultrasonic, drop sensor, IMU) + BLE send, no ML yet. Validate hardware wiring and readings first.
2. `aiml/sensor_model` — data collection → labeling → train 1D CNN v1 → quantize INT8 → export → deploy to sensor node.
3. `firmware/esp32_cam_node` — raw camera capture + BLE send, no ML yet, triggered by a manual/test signal initially.
4. `aiml/vision_model` — data collection → train FOMO via Edge Impulse → quantize INT8 → export → deploy to cam node, wire up real trigger-gating from the sensor node.
5. `edge_gateway/fusion` + `edge_gateway/mapping` — get the tile grid updating live from both nodes' BLE output.
6. `edge_gateway/planning` — implement A* on top of the working grid.
7. `edge_gateway/guidance` — implement audio (Bluetooth TTS) + haptic (vibration pattern) output, including the confidence-gated fallback rule.
8. `app_ui/map_viewer` — live map visualization for demo/debugging purposes.

Start with step 1. Generate the `platformio.ini` and starter `main.cpp`/sensor driver files for `esp32_sensor_node`, and ask me for my exact sensor models/pin assignments before finalizing the driver code.

## PROMPT END

---

### How to use this
- Paste the entire block between "PROMPT START" and "PROMPT END" into Claude Code (or your coding assistant of choice) as your opening message in VS Code.
- Keep this file in your `docs/` folder as the canonical reference — if the assistant starts drifting from the architecture, paste the relevant section back in to re-anchor it.
- Update `class_definitions.yaml` details and exact sensor part numbers/pins as you finalize hardware — the assistant will ask for these in step 1 as noted at the end of the prompt.
