# Project: Echolocation-Inspired Indoor Navigation for Visually Impaired People

Build a software-dominated prototype that helps visually impaired users navigate indoor environments using an echolocation-inspired sensor mesh.

## Core Idea
Use multiple ultrasonic/ToF distance sensors connected to an ESP32/ESP32-S3 to detect the surrounding environment. The system should detect static obstacles and moving objects/humans, estimate their distance and direction, and continuously construct a clear 2D indoor map.

The goal is NOT simply obstacle detection. The main output must be a live 2D spatial map showing:
- User's current position and orientation
- Walls and static obstacles
- Humans/moving objects
- Approximate distance and direction
- Safe/recommended navigation path
- Destination

## AI / TinyML
Use TinyML as a sensor-perception layer rather than making AI directly generate the map.

Possible TinyML model: lightweight 1D CNN trained on sequences of sensor readings + IMU data.

Example classifications:
- Static obstacle
- Moving object
- Possible human
- Open space
- Wall
- Doorway/corner
- Approaching/receding/crossing object
- Unknown/uncertain

Use INT8 quantization so inference can run efficiently on ESP32-S3.

## Human Detection
Do not assume "moving = human". Use temporal patterns from multiple sensors and, if necessary, PIR as an optional supporting sensor. The system should estimate whether an object is moving independently of the user's own movement using IMU data.

Camera-based detection is an optional future enhancement, not the primary sensing method.

## Hardware
Preferred prototype:
- ESP32-S3
- 2–4 ultrasonic or ToF distance sensors
- IMU
- Optional PIR sensor
- Vibration motors/buzzer for feedback
- Wi-Fi/BLE for communication

Keep hardware relatively simple and make the project primarily software/AI focused.

## Mapping
Use sensor fusion + localization + occupancy-grid mapping/simplified SLAM to create a dynamic 2D indoor map.

The map should have separate concepts for:
- Static environment
- Dynamic objects/humans
- User position
- Navigation route

Use A* or another suitable path-planning algorithm to calculate a safe route.

## Software Architecture

Sensors
→ ESP32-S3
→ Sensor preprocessing
→ TinyML perception
→ Sensor fusion
→ Localization
→ 2D occupancy mapping
→ Dynamic human/object tracking
→ A* path planning
→ Live 2D map
→ Audio/haptic navigation feedback

## Why Sensor Mesh Instead of Only Camera + AI?
Do NOT claim ultrasonic/ToF is universally better than cameras.

The project's advantage is that it is:
- Echolocation-inspired
- Privacy-preserving because it does not require continuous image capture
- Independent of visible lighting
- Lightweight for edge processing
- Directly based on distance/spatial measurements
- Suitable for real-time spatial mapping

A camera is generally better for semantic object recognition, but this project prioritizes spatial awareness, privacy, low computational requirements, and operation in different lighting conditions.

## Main Objective
Create a working prototype where a visually impaired user moves through an indoor environment and the system continuously builds/updates a 2D map, identifies static and dynamic obstacles, tracks nearby humans when possible, calculates a safe route, and provides understandable navigation feedback.

Important: If "UV sensor" is mentioned in the original problem statement, verify whether it actually means ultrasonic sensor. UV sensors detect ultraviolet light and are not suitable for echolocation.