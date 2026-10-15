#!/usr/bin/env python3
"""
collect_sensor_data.py — BLE/Serial Sensor Data Logger

Connects to the ESP32 sensor node over BLE and logs all sensor events
to timestamped CSV files for training data collection.

Usage:
    python collect_sensor_data.py --device "BlindNav-Sensor" --label open_space
    python collect_sensor_data.py --device "BlindNav-Sensor" --label static_obstacle

Each run creates one CSV in data/raw/sensor/<label>/<timestamp>.csv

Requirements:
    pip install bleak asyncio
"""

import asyncio
import argparse
import csv
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from bleak import BleakClient, BleakScanner

# UUIDs must match firmware config.h
SERVICE_UUID = "4A98C7D2-1E3F-4B6A-8D5C-2F9E0A7B3C1D"
CHAR_UUID    = "5B09D8E3-2F40-5C7B-9E6D-3G0F1B8C4D2E"

OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "data" / "raw" / "sensor"

CSV_FIELDS = [
    "timestamp_ms", "label",
    "front_cm", "left_cm", "right_cm", "floor_mm",
    "yaw_rate_dps", "stationary",
    "cls_raw", "conf_raw"
]

class DataLogger:
    def __init__(self, label: str, device_name: str):
        self.label = label
        self.device_name = device_name
        self.rows = []
        self.running = False

        # Create output directory
        out_dir = OUTPUT_BASE / label
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.out_path = out_dir / f"{ts}.csv"
        print(f"[Logger] Output: {self.out_path}")

    def on_notify(self, sender, data: bytearray):
        try:
            payload = json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        row = {
            "timestamp_ms": payload.get("ts", int(time.time() * 1000)),
            "label":        self.label,
            "front_cm":     payload.get("df", -1),
            "left_cm":      payload.get("dl", -1),
            "right_cm":     payload.get("dr", -1),
            "floor_mm":     payload.get("flr", 0),
            "yaw_rate_dps": payload.get("yr", 0),
            "stationary":   payload.get("sta", 0),
            "cls_raw":      payload.get("cls", -1),
            "conf_raw":     payload.get("cf", 0),
        }
        self.rows.append(row)

        # Live feedback
        print(f"  front={row['front_cm']:6.1f}cm  "
              f"left={row['left_cm']:6.1f}cm  "
              f"right={row['right_cm']:6.1f}cm  "
              f"floor={row['floor_mm']:4d}mm  "
              f"stat={row['stationary']}", end="\r")

    def save(self):
        with open(self.out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)
        print(f"\n[Logger] Saved {len(self.rows)} samples → {self.out_path}")


async def find_device(name: str):
    print(f"[Scan] Looking for '{name}'...")
    device = await BleakScanner.find_device_by_name(name, timeout=15.0)
    if device is None:
        print(f"[Scan] Device '{name}' not found. Is it powered on and advertising?")
        sys.exit(1)
    print(f"[Scan] Found: {device.address}")
    return device


async def run(args):
    logger = DataLogger(args.label, args.device)
    device = await find_device(args.device)

    async with BleakClient(device) as client:
        print(f"[BLE] Connected. Logging label='{args.label}' for {args.duration}s ...")
        print("      Press Ctrl+C to stop early.\n")
        await client.start_notify(CHAR_UUID, logger.on_notify)
        try:
            await asyncio.sleep(args.duration)
        except KeyboardInterrupt:
            print("\n[Logger] Stopped by user")
        finally:
            await client.stop_notify(CHAR_UUID)

    logger.save()


def main():
    parser = argparse.ArgumentParser(description="Blind Nav Sensor Data Logger")
    parser.add_argument("--device",   default="BlindNav-Sensor",
                        help="BLE device name to connect to")
    parser.add_argument("--label",    required=True,
                        choices=["static_obstacle","moving_object","open_space",
                                 "dropoff_edge","approaching","receding",
                                 "crossing","user_motion","unknown"],
                        help="Ground truth label for this recording session")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Recording duration in seconds (default: 60)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
