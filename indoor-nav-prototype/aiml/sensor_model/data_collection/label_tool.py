#!/usr/bin/env python3
"""
label_tool.py — Interactive CLI Labeling Tool for Sensor Sessions

Loads an unlabeled or partially-labeled CSV session and lets you
relabel windows interactively. Useful when a recording session contains
mixed scenarios (e.g. you walked past both a wall and an open corridor).

Usage:
    python label_tool.py --file data/raw/sensor/unknown/20260829_120000.csv
    python label_tool.py --dir  data/raw/sensor/unknown/   # batch all files

Controls (at each window prompt):
    0–8  → assign class index (see class_definitions.yaml)
    s    → skip window
    q    → quit and save progress
"""

import argparse
import csv
import yaml
import os
import sys
from pathlib import Path

CLASS_DEF_PATH = Path(__file__).parent.parent.parent / "shared" / "class_definitions.yaml"
with open(CLASS_DEF_PATH) as f:
    defs = yaml.safe_load(f)
CLASSES = [(c["index"], c["name"]) for c in defs["sensor_classes"]]

WINDOW_SIZE = 20   # must match train_config.yaml


def print_class_menu():
    print("\nClasses:")
    for idx, name in CLASSES:
        print(f"  {idx}: {name}")
    print("  s : skip")
    print("  q : quit + save")


def label_file(csv_path: Path):
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"[Label] Empty file: {csv_path}")
        return

    print(f"\n[Label] File: {csv_path.name}  ({len(rows)} rows)")
    print_class_menu()

    # Show windows
    modified = False
    for start in range(0, len(rows) - WINDOW_SIZE + 1, WINDOW_SIZE):
        window = rows[start : start + WINDOW_SIZE]
        current_label = window[0].get("label", "unknown")

        # Summarize window
        fronts = [float(r.get("front_cm", -1)) for r in window]
        valid_fronts = [v for v in fronts if v > 0]
        avg_front = sum(valid_fronts) / len(valid_fronts) if valid_fronts else -1

        print(f"\n  Window {start//WINDOW_SIZE + 1}  "
              f"front={avg_front:.1f}cm  "
              f"current_label='{current_label}'")

        user_input = input("  Label [0-8/s/q]: ").strip().lower()

        if user_input == "q":
            print("[Label] Quit — saving progress...")
            break
        elif user_input == "s":
            continue
        else:
            try:
                new_idx = int(user_input)
                new_label = dict(CLASSES).get(new_idx)
                if new_label is None:
                    print(f"  Invalid index {new_idx} — skipping")
                    continue
                for i in range(start, min(start + WINDOW_SIZE, len(rows))):
                    rows[i]["label"] = new_label
                modified = True
            except ValueError:
                print("  Invalid input — skipping")

    if modified:
        # Save back to same file
        with open(csv_path, "w", newline="") as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        print(f"[Label] Saved: {csv_path}")
    else:
        print("[Label] No changes made.")


def main():
    parser = argparse.ArgumentParser(description="Sensor Data Interactive Labeler")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Label a single CSV file")
    group.add_argument("--dir",  type=Path, help="Label all CSV files in a directory")
    args = parser.parse_args()

    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}")
            sys.exit(1)
        label_file(args.file)
    elif args.dir:
        csv_files = sorted(args.dir.glob("**/*.csv"))
        if not csv_files:
            print(f"No CSV files found in {args.dir}")
            sys.exit(1)
        for csv_file in csv_files:
            label_file(csv_file)


if __name__ == "__main__":
    main()
