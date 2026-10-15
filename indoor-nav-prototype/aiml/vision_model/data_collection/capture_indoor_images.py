#!/usr/bin/env python3
"""
capture_indoor_images.py — Pull labeled frames from ESP32-CAM over HTTP

Temporarily enables HTTP snapshot mode on the ESP32-CAM (not the inference
mode — this is only for data collection walks) and saves labeled images.

The CAM node must be in DATA_COLLECTION mode (not INFERENCE mode):
  - Flash esp32_cam_node with DATA_COLLECTION_MODE=1 build flag
  - The cam then serves a /capture endpoint over Wi-Fi

Usage:
    python capture_indoor_images.py --ip 192.168.1.42 --label chair --count 100
"""

import argparse
import os
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_BASE = Path(__file__).parent.parent.parent.parent / "data" / "raw" / "vision"


def capture(ip: str, label: str, count: int, delay_s: float):
    out_dir = OUTPUT_BASE / label
    out_dir.mkdir(parents=True, exist_ok=True)

    url = f"http://{ip}/capture"
    print(f"[Capture] Connecting to {url}")
    print(f"[Capture] Label='{label}', saving {count} frames to {out_dir}")
    print("          Press Ctrl+C to stop early.\n")

    saved = 0
    try:
        while saved < count:
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("image"):
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    fname = out_dir / f"{ts}.jpg"
                    fname.write_bytes(resp.content)
                    saved += 1
                    print(f"  Saved {saved}/{count}: {fname.name}", end="\r")
                else:
                    print(f"\n  Unexpected response: {resp.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"\n  Request failed: {e}")
            time.sleep(delay_s)
    except KeyboardInterrupt:
        print(f"\n[Capture] Stopped. Saved {saved} frames.")
    print(f"\n[Capture] Done. Total saved: {saved}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",    required=True, help="ESP32-CAM IP address")
    parser.add_argument("--label", required=True,
                        choices=["person","chair","table","door","stairs","wall","unknown_object"],
                        help="Class label for captured frames")
    parser.add_argument("--count", type=int, default=200, help="Number of frames to capture")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Delay between captures in seconds")
    args = parser.parse_args()
    capture(args.ip, args.label, args.count, args.delay)


if __name__ == "__main__":
    main()
