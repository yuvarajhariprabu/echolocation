# Build Prompt (Simplified)

Copy-paste this into your coding assistant in VS Code to start building.

---

**PROMPT:**

I'm building a software/AI-focused prototype: an **echolocation-inspired indoor navigation system for visually impaired people**. Help me build it in VS Code, following this architecture. Work step by step, confirm before assuming anything not specified.

**Hardware:**
- ESP32-S3: 3x ultrasonic sensors, drop sensor, gyroscope, accelerometer
- ESP32-CAM: camera, triggered only (not continuous)
- Output: Bluetooth headphone (audio) + 3 vibration motors (haptic)
- Comms: BLE between nodes and gateway

**AI Models:**
- **Sensor node (ESP32-S3):** 1D CNN, INT8-quantized. Input = windowed ultrasonic + drop sensor + IMU data. Classes: static obstacle, moving object, open space, drop-off, approaching/receding, unknown. Must use IMU to tell apart "user moved" vs "object moved." Output includes confidence.
- **Cam node (ESP32-CAM):** FOMO (via Edge Impulse), INT8-quantized. Trigger-gated by sensor node. Classes: person, chair, table, door, stairs, wall, unknown. Outputs grid-cell position + confidence. Never store/transmit raw images — only results leave the device.
- **Fusion (gateway):** Combine both model outputs + IMU heading into one obstacle object. If confidence is low or models disagree → fall back to generic caution alert, never guess.

**Folder structure:**
```
indoor-nav-prototype/
├── firmware/
│   ├── esp32_sensor_node/   (PlatformIO, ESP32-S3)
│   └── esp32_cam_node/      (PlatformIO, ESP32-CAM)
├── aiml/
│   ├── sensor_model/        (data, preprocessing, model, export)
│   ├── vision_model/        (data, labeling, model, export)
│   └── shared/               (class_definitions.yaml = single source of truth)
├── edge_gateway/             (Python: fusion, mapping, planning, guidance, comms)
├── app_ui/map_viewer/        (HTML/JS live 2D map)
├── data/
└── docs/
```

**Rules:**
1. Fast path (haptic alerts from ultrasonic+IMU) must never wait on the camera.
2. No specific guidance from low-confidence single-source data — default to caution.
3. No raw camera images ever stored or transmitted.
4. All class labels sourced from `class_definitions.yaml`, not hardcoded.
5. Ultrasonic sensors fire sequentially (avoid cross-talk).
6. Tile grid tracks 3 layers: static occupancy, dynamic objects (with decay), user position/heading.

**Tooling:** VS Code + PlatformIO extension for firmware, Python extension for `aiml/`/`edge_gateway/`, Live Server for `app_ui/`.

**Build order:**
1. Sensor node — raw sensor reads + BLE send (no ML yet)
2. Train + deploy 1D CNN to sensor node
3. Cam node — raw capture + BLE send (no ML yet)
4. Train + deploy FOMO to cam node, wire up real triggering
5. Gateway fusion + tile-grid mapping
6. A* path planning
7. Guidance (audio + haptic + confidence fallback)
8. Map viewer UI

Start with step 1: generate `platformio.ini` and starter `main.cpp` for the sensor node, and ask me for exact sensor models/pins before finalizing driver code.
