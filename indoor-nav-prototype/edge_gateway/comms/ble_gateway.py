"""
ble_gateway.py — BLE Central: Connects to Both ESP32 Nodes

Uses bleak (cross-platform BLE library) to act as the central device.
Scans for and connects to:
  1. BlindNav-Sensor (ESP32-S3)
  2. BlindNav-CAM    (ESP32-CAM)

On notification from either device, parses the JSON payload and dispatches
to the appropriate callback (on_sensor_event / on_vision_event).
"""

import asyncio
import json
import logging
from typing import Optional, Callable

log = logging.getLogger(__name__)

try:
    from bleak import BleakClient, BleakScanner
    _BLEAK_AVAILABLE = True
except ImportError:
    _BLEAK_AVAILABLE = False
    log.warning("[BLEGateway] bleak not installed. pip install bleak")

from ..fusion.event_schema import SensorEvent, VisionEvent

# UUIDs must match firmware config.h
SENSOR_SERVICE_UUID = "4A98C7D2-1E3F-4B6A-8D5C-2F9E0A7B3C1D"
SENSOR_CHAR_UUID    = "5B09D8E3-2F40-5C7B-9E6D-3A0F1B8C4D2E"
CAM_SERVICE_UUID    = "6C10E9F4-3B51-6D8C-AF7E-4A1B2C9D5E3F"
CAM_CHAR_UUID       = "7D21FA25-4B62-7E9D-BE8F-5C2A3D0E6F4B"

SENSOR_DEVICE_NAME  = "BlindNav-Sensor"
CAM_DEVICE_NAME     = "BlindNav-CAM"


class BLEGateway:

    def __init__(
        self,
        on_sensor_event: Optional[Callable[[SensorEvent], None]] = None,
        on_vision_event: Optional[Callable[[VisionEvent], None]] = None,
    ):
        self._on_sensor = on_sensor_event
        self._on_vision = on_vision_event
        self._sensor_client: Optional[BleakClient] = None
        self._cam_client:    Optional[BleakClient] = None

    async def run(self):
        """Continuously scan and maintain connections to both nodes."""
        if not _BLEAK_AVAILABLE:
            log.error("[BLEGateway] bleak not available — BLE gateway disabled")
            return
        while True:
            await asyncio.gather(
                self._connect_sensor(),
                self._connect_cam(),
            )
            await asyncio.sleep(5)  # retry delay if disconnected

    async def _find_device(self, name: str, timeout: float = 15.0):
        log.info(f"[BLEGateway] Scanning for '{name}'...")
        device = await BleakScanner.find_device_by_name(name, timeout=timeout)
        if device:
            log.info(f"[BLEGateway] Found {name}: {device.address}")
        else:
            log.warning(f"[BLEGateway] {name} not found")
        return device

    async def _connect_sensor(self):
        device = await self._find_device(SENSOR_DEVICE_NAME)
        if not device:
            return
        try:
            async with BleakClient(device) as client:
                self._sensor_client = client
                log.info(f"[BLEGateway] Connected to sensor node")
                await client.start_notify(SENSOR_CHAR_UUID, self._on_sensor_notify)
                while client.is_connected:
                    await asyncio.sleep(1)
        except Exception as e:
            log.error(f"[BLEGateway] Sensor node error: {e}")
        finally:
            self._sensor_client = None

    async def _connect_cam(self):
        device = await self._find_device(CAM_DEVICE_NAME)
        if not device:
            return
        try:
            async with BleakClient(device) as client:
                self._cam_client = client
                log.info(f"[BLEGateway] Connected to CAM node")
                await client.start_notify(CAM_CHAR_UUID, self._on_cam_notify)
                while client.is_connected:
                    await asyncio.sleep(1)
        except Exception as e:
            log.error(f"[BLEGateway] CAM node error: {e}")
        finally:
            self._cam_client = None

    def _on_sensor_notify(self, sender, data: bytearray):
        try:
            p = json.loads(data.decode("utf-8"))
            ev = SensorEvent(
                ts            = p.get("ts", 0),
                class_index   = p.get("cls", 8),
                confidence    = float(p.get("cf", 0)),
                front_cm      = float(p.get("df", -1)),
                left_cm       = float(p.get("dl", -1)),
                right_cm      = float(p.get("dr", -1)),
                floor_mm      = int(p.get("flr", 0)),
                yaw_rate_dps  = float(p.get("yr", 0)),
                stationary    = bool(p.get("sta", 0)),
            )
            if self._on_sensor:
                self._on_sensor(ev)
        except Exception as e:
            log.error(f"[BLEGateway] Sensor parse error: {e}")

    def _on_cam_notify(self, sender, data: bytearray):
        try:
            p = json.loads(data.decode("utf-8"))
            ev = VisionEvent(
                ts           = p.get("ts", 0),
                class_index  = p.get("vcls", 6),
                confidence   = float(p.get("vcf", 0)),
                grid_x       = int(p.get("gx", 0)),
                grid_y       = int(p.get("gy", 0)),
            )
            if self._on_vision:
                self._on_vision(ev)
        except Exception as e:
            log.error(f"[BLEGateway] CAM parse error: {e}")
