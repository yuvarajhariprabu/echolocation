# Judges Presentation Script (~4 Minutes)
### Echolocation-Inspired Indoor Navigation for Visually Impaired People

---

## 1. The Problem (30 sec)

Visually impaired individuals face a major gap in indoor navigation. GPS works outdoors, but indoors — malls, hospitals, offices, unfamiliar buildings — there is no reliable, real-time way to understand the surrounding space: where the walls are, what obstacles exist, whether people are moving nearby, and how to safely walk from point A to point B.

Most existing solutions rely on canes or basic obstacle-beeping devices — they tell you *something is close*, but not *what it is*, *where exactly*, or *what to do about it*. Camera-only smart-glasses solutions exist, but they raise privacy concerns since they continuously capture and process video of everything around the user, including bystanders.

Our project solves this with an **echolocation-inspired sensor mesh combined with a triggered, privacy-conscious camera**, powered entirely by on-device AI.

---

## 2. The Core Idea (30 sec)

We built a system that works the way bats and dolphins navigate — using distance and spatial awareness rather than vision alone — but we enhance it with a camera that only activates when needed, and two dedicated AI models that work together: one understands *space*, the other understands *objects*.

The output isn't just a beep. It's a **continuously updating 2D tile-grid map** of the user's surroundings, combined with **real-time audio and haptic guidance** — so the user always knows what's around them and where it's safe to walk.

---

## 3. The Hardware (30 sec)

Two coordinated modules:

- **ESP32-S3 Sensor Node** — 3 ultrasonic distance sensors, a drop/edge sensor for stairs and ledges, a gyroscope, and an accelerometer. This node handles all spatial and motion sensing.
- **ESP32-CAM Vision Node** — a camera module that stays idle by default and only wakes up when the sensor node flags something worth identifying — saving power and, importantly, protecting the privacy of people around the user, since it isn't continuously recording.

Feedback is delivered through a **Bluetooth headphone for audio cues** and **3 vibration motors for directional haptic feedback** — so guidance works even in noisy environments or for users who prefer non-audio cues.

---

## 4. Where the Real Engineering Is: The AI/ML Layer (60 sec — the core of the pitch)

This is the heart of the project, and we deliberately made it AI-first rather than hardware-first.

**Model 1 — Spatial/Motion TinyML Model (1D CNN, INT8-quantized):**
Running on the ESP32-S3, this model doesn't just threshold distance readings. It analyzes *time-series patterns* across all three ultrasonic sensors together with gyroscope and accelerometer data, to classify what's actually happening — a static obstacle, a moving object, an approaching person, an open path, or a drop-off. Critically, we use IMU data to solve a subtle but important problem: distinguishing whether a distance reading changed because *the environment moved* or because *the user themselves turned or moved*. Without this, the system would constantly misread the user's own motion as an approaching obstacle.

**Model 2 — Object Classification Model (FOMO, INT8-quantized):**
Running on the ESP32-CAM, we use FOMO — Faster Objects, More Objects — a detection architecture purpose-built for microcontrollers. Instead of full bounding boxes like YOLO, FOMO predicts *which grid cell* contains *which object*. This is a perfect match for our system because our map is already tile-based — the camera's output slots directly into our grid without extra translation logic. It tells us not just that an obstacle exists, but what it is: a chair, a table, a door, stairs, or a person — turning a generic "obstacle ahead" alert into a specific, actionable one like "chair ahead, two steps to your left."

Both models are quantized to INT8 specifically so they can run entirely on-device, in real time, without needing cloud connectivity — which matters for reliability, latency, and privacy.

---

## 5. From Sensing to Guidance (45 sec)

The outputs of both models are fused together with the user's live orientation from the IMU. This fused data updates a **2D tile-grid map** in real time — each tile marked occupied or free, with static obstacles and moving humans tracked as separate layers, and the user's position and direction of vision rendered live on the map.

On top of this grid, we run **A\* path planning** to continuously calculate the safest route to the destination, replanning instantly whenever a new obstacle appears or a person crosses the path.

Finally, a guidance engine translates all of this into two channels of feedback: **haptic vibration for immediate, reflexive alerts** — like a sudden drop-off or a very close obstacle — and **audio cues for descriptive guidance** — telling the user what's ahead and which way to move.

---

## 6. Why This Approach Is Different (30 sec)

We're not claiming ultrasonic sensing beats cameras — cameras are genuinely better at recognizing objects. Our advantage is that we combine both intelligently: the sensor mesh gives fast, lightweight, always-on spatial awareness with no privacy cost, and the camera activates only when needed to add semantic meaning. The result is a system that's privacy-preserving, lightweight enough for real embedded hardware, works regardless of lighting conditions, and — most importantly — is guided end-to-end by two purpose-built, on-device AI models rather than simple sensor thresholds.

---

## 7. Closing (15 sec)

In short: we've built a working prototype where a visually impaired user can walk through an unfamiliar indoor space, and the system continuously builds a live map, understands both static and moving obstacles, identifies what they are, plans the safest route, and guides the user there — through sound and touch — powered entirely by AI running on low-cost embedded hardware.

---

### Quick Reference — Key Numbers/Terms to Remember on Stage
- 2 microcontrollers: **ESP32-S3** (sensors) + **ESP32-CAM** (vision)
- 2 AI models: **1D CNN** (spatial/motion) + **FOMO** (object detection), both **INT8-quantized**
- Sensors: **3 ultrasonic + drop sensor + gyroscope + accelerometer**
- Output: **tile-grid 2D map + A\* path planning + audio (Bluetooth) + haptic (3 vibration motors)**
- Differentiator: **privacy-preserving, triggered camera use, on-device AI, no cloud dependency**
