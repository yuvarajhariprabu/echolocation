# BlindNav — Indoor Navigation Prototype

> AI-powered wearable navigation system for visually impaired users.  
> Combines ultrasonic sensors, a ToF drop detector, IMU, and a vision camera  
> into a real-time obstacle detection and haptic/audio guidance system.

---

## What You Need (Hardware)

| Component | Quantity | Role |
|-----------|----------|------|
| ESP32-S3 DevKit | 1 | Sensor Node (ultrasonic + IMU + haptics) |
| ESP32-CAM (AI-Thinker) | 1 | Vision Node (OV2640 + FOMO inference) |
| Raspberry Pi / Laptop | 1 | Edge Gateway (fusion, planning, guidance) |
| HC-SR04 Ultrasonic | 3 | Front / Left / Right obstacle detection |
| VL53L0X ToF Sensor | 1 | Floor drop-off detection |
| MPU6050 IMU | 1 | Orientation + stationary detection |
| Vibration Motors | 3 | Haptic feedback (front / left / right) |
| NPN Transistors / MOSFETs | 3 | Motor drivers (never drive motors direct from GPIO) |

See [`WIRING.md`](../WIRING.md) for exact pin connections.

---

## System Architecture

```
Wearable (ESP32)
  ├── ESP32-S3  — reads sensors, runs 1D CNN, sends BLE events
  └── ESP32-CAM — triggered by sensor, runs FOMO vision, advertises BLE results

Edge Gateway (RPi / Laptop)
  ├── Connects to both ESP32 nodes via BLE (bleak)
  ├── Fuses sensor + vision results
  ├── Runs A* path planning on occupancy grid
  ├── Drives TTS audio + haptic motors
  └── Streams live map to browser via WebSocket

Browser (any device on same network)
  └── app_ui/map_viewer/index.html — live 2D tile grid + path visualization
```

---

## Prerequisites

### 1 — Install PlatformIO (for firmware)

```powershell
pip install platformio
```

Or install the **PlatformIO IDE** extension in VS Code (recommended).

### 2 — Install Python dependencies (for gateway)

```powershell
pip install bleak websockets pyttsx3 numpy pyyaml
```

> **On Raspberry Pi** also install `RPi.GPIO` for physical haptic motors:
> ```bash
> pip install RPi.GPIO
> ```
> On a laptop, the gateway runs in `simulate_haptic: true` mode (motors simulated in console).

---

## Step 1 — Flash Sensor Node (ESP32-S3)

```powershell
cd "c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype\firmware\esp32_sensor_node"
pio run --target upload
pio device monitor --baud 115200
```

**Expected serial output:**
```
[Sensor] Ultrasonics OK
[IMU] MPU6050 OK
[BLE] Advertising as "BlindNav-Sensor"
[Sensor] Loop running at 20Hz
```

> **TinyML is OFF by default.** The firmware uses rule-based thresholds.  
> To enable the 1D CNN, complete the AI/ML pipeline (Step 5) first,  
> then set `USE_TINYML=1` in `platformio.ini` and reflash.

---

## Step 2 — Flash Vision Node (ESP32-CAM)

```powershell
cd "c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype\firmware\esp32_cam_node"
pio run --target upload
pio device monitor --baud 115200
```

**Expected serial output:**
```
[CAM] BlindNav Vision Node booting...
[Trigger] Scanning for BlindNav-Sensor...
[BLEResult] Advertising CAM service. Gateway connects to subscribe.
[Camera] OV2640 initialized: 96x96 grayscale
[CAM] Ready. Waiting for sensor trigger...
```

> **Note:** The FOMO model is a stub placeholder until you complete Step 6.  
> The camera still captures and returns frames; inference will produce no valid detections.

---

## Step 3 — Run the Edge Gateway

Open a terminal **in the project root** (not inside any sub-folder):

```powershell
cd "c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype"
python -m edge_gateway.main
```

**Expected console output:**
```
[Gateway] Starting BlindNav Edge Gateway...
[MapStream] WebSocket server running on ws://localhost:8765
[BLEGateway] Scanning for 'BlindNav-Sensor'...
[BLEGateway] Scanning for 'BlindNav-CAM'...
[Gateway] All systems running. Waiting for BLE connections...
[BLEGateway] Connected to sensor node
[BLEGateway] Connected to CAM node
```

> **Important:** Run from the project root with `python -m edge_gateway.main`,  
> NOT `python edge_gateway/main.py`. The `-m` flag ensures relative imports work.

---

## Step 4 — Open the Live Map Viewer

Open this file in any browser (no server needed — it's a local HTML file):

```
c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype\app_ui\map_viewer\index.html
```

- The map auto-connects to `ws://localhost:8765` (the gateway WebSocket).
- The **status dot** in the top-right turns green when connected.
- **Click on the map** to set a navigation goal — the gateway runs A* and draws the path.

---

## Step 5 — Collect Sensor Training Data (for 1D CNN)

Run one session per class label. Walk around with the device in each scenario:

```powershell
cd "c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype"

# Example: record 60 seconds of "walking in open corridor"
python aiml\sensor_model\data_collection\collect_sensor_data.py --label open_space --duration 60

# Repeat for each class:
# static_obstacle  moving_object  open_space  dropoff_edge
# approaching  receding  crossing  user_motion  unknown
```

---

## Step 6 — Train and Export the Sensor Model

Run these scripts **in order**:

```powershell
cd "c:\Users\yuvar\Documents\hack 2\indoor-nav-prototype"

# 1. Slice recordings into windows
python aiml\sensor_model\preprocessing\windowing.py

# 2. Fit normalization (also prints C array values for firmware)
python aiml\sensor_model\preprocessing\normalize.py --apply

# 3. Augment data (generates 3× more synthetic samples)
python aiml\sensor_model\preprocessing\augment.py

# 4. Train the 1D CNN
python aiml\sensor_model\model\train.py

# 5. Evaluate (confusion matrix saved to checkpoints/)
python aiml\sensor_model\model\evaluate.py

# 6. Quantize to INT8 TFLite
python aiml\sensor_model\export\quantize_int8.py

# 7. Convert to C header and copy into firmware
python aiml\sensor_model\export\convert_to_c_array.py
```

Then enable TinyML in the firmware:

```ini
# firmware/esp32_sensor_node/platformio.ini
build_flags = -DUSE_TINYML=1
```

Reflash: `pio run --target upload` (from the sensor node directory).

---

## Step 7 — Collect Vision Data and Train FOMO Model

### Capture images from the ESP32-CAM

The CAM must be on the same Wi-Fi network and flashed in data-collection mode:

```powershell
python aiml\vision_model\data_collection\capture_indoor_images.py ^
    --ip 192.168.1.42 ^
    --label chair ^
    --count 200
```

Repeat for each label: `person chair table door stairs wall unknown_object`

### Train on Edge Impulse (free, online)

1. Go to [edgeimpulse.com](https://edgeimpulse.com) → Create project
2. Upload images from `data/raw/vision/<label>/`
3. Create Impulse → Image (96×96, Grayscale) → FOMO object detection
4. Train → get >80% accuracy before exporting
5. Export as **Arduino library** (.zip)

### Export model to firmware

```powershell
python aiml\vision_model\export\fomo_export.py --project-id <YOUR_EI_PROJECT_ID>
```

This writes `firmware/esp32_cam_node/src/inference/fomo_model_data.h` automatically. Reflash the CAM node.

---

## Quick-Start Checklist

- [ ] PlatformIO installed
- [ ] `pip install bleak websockets pyttsx3 numpy pyyaml` done
- [ ] Sensor node flashed and showing serial output
- [ ] CAM node flashed and showing serial output
- [ ] Gateway running: `python -m edge_gateway.main` from project root
- [ ] Map viewer open in browser — green dot in top-right
- [ ] BLE connections shown in gateway console

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: edge_gateway` | Run from project root with `python -m edge_gateway.main` |
| BLE device not found | Check ESP32 is powered and serial shows "Advertising" |
| Camera init failed | Check AI-Thinker pin mapping in `config.h`. Use USB-TTL adapter for serial. |
| Map shows blank / no connection | Gateway must be running first; check port 8765 is free |
| `pyttsx3` no audio | Install system TTS: Windows has it built-in; Linux: `apt install espeak` |
| `RPi.GPIO` error on laptop | Set `simulate_haptic: true` in `edge_gateway/config/gateway_config.yaml` |

---

## UUID Reference (keep these consistent)

| UUID | Used by |
|------|---------|
| `4A98C7D2-1E3F-4B6A-8D5C-2F9E0A7B3C1D` | Sensor node service (sensor → gateway + CAM) |
| `5B09D8E3-2F40-5C7B-9E6D-3A0F1B8C4D2E` | Sensor event characteristic |
| `6C10E9F4-3B51-6D8C-AF7E-4A1B2C9D5E3F` | CAM node service (CAM → gateway) |
| `7D21FA25-4B62-7E9D-BE8F-5C2A3D0E6F4B` | FOMO result characteristic |

These are defined in `firmware/esp32_sensor_node/src/config.h` and must match `edge_gateway/comms/ble_gateway.py`.

---

## Privacy

- Camera frames are **never stored or transmitted** — only inference metadata leaves the device.
- Frame buffer is returned to the driver immediately after inference input is loaded.
- No cloud dependency — all inference runs fully on-device.
