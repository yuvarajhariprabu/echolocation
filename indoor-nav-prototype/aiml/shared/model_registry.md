# Model Registry

Track every trained model version, its metrics, and which firmware build it is deployed to.

---

## Sensor Model (1D CNN — ESP32-S3)

| Version | Date | Accuracy | Size (KB) | Latency (ms) | Firmware Build | Notes |
|---------|------|----------|-----------|--------------|----------------|-------|
| v0      | —    | N/A       | N/A       | N/A          | rule-based stub | USE_TINYML=0, no model yet |

---

## Vision Model (FOMO — ESP32-CAM)

| Version | Date | mAP | Size (KB) | Latency (ms) | Firmware Build | Notes |
|---------|------|-----|-----------|--------------|----------------|-------|
| v0      | —    | N/A | N/A       | N/A          | stub            | Edge Impulse project not yet created |

---

## Deployment Matrix

| Firmware Node     | Sensor Model | Vision Model | Gateway Version |
|-------------------|-------------|--------------|-----------------|
| esp32_sensor_node | v0 (stub)   | —            | v0              |
| esp32_cam_node    | —           | v0 (stub)    | v0              |
