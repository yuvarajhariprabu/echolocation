/*
  Blind Navigation Aid — Integrated Firmware
  ESP32 DevKit (WROOM) | 3x HC-SR04 | VL53L0X (stair/drop-off) | MPU6050 (IMU)

  ARCHITECTURE
  ------------
  Core 0 -> sensorTask   : polls all sensors, filters IMU, updates shared state
  Core 1 -> decisionTask : reads shared state, runs obstacle logic (rule-based
                            by default, TinyML slot provided), drives haptics + audio

  Shared state is protected by a mutex so the two cores never read/write it
  at the same time.

  LIBRARIES NEEDED (Arduino Library Manager):
    - Adafruit_VL53L0X
    - Adafruit_MPU6050
    - Adafruit_Sensor
    - Adafruit_BusIO   (dependency, auto-installed)

  TINYML:
    This sketch runs standalone with a rule-based obstacle/drop-off policy
    (USE_TINYML 0) so you can test the full pipeline before your model is
    ready. Flip USE_TINYML to 1 once you have model_data.h exported from
    your trained TFLite Micro model — see the clearly marked slot below.
*/

#include <Wire.h>
#include <Adafruit_VL53L0X.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// ---------------- TinyML toggle ----------------
#define USE_TINYML 0   // set to 1 once your model is wired in (see bottom of file)

#if USE_TINYML
  #include <TensorFlowLite_ESP32.h>
  #include "tensorflow/lite/micro/all_ops_resolver.h"
  #include "tensorflow/lite/micro/micro_interpreter.h"
  #include "tensorflow/lite/micro/micro_error_reporter.h"
  #include "tensorflow/lite/schema/schema_generated.h"
  #include "model_data.h"   // <-- your exported model array goes here
#endif

// ---------------- Pin map (see WIRING.md) ----------------
#define TRIG_FRONT 5
#define ECHO_FRONT 18
#define TRIG_LEFT  17
#define ECHO_LEFT  16
#define TRIG_RIGHT 19
#define ECHO_RIGHT 23

#define I2C_SDA 21
#define I2C_SCL 22

#define HAPTIC_FRONT 25
#define HAPTIC_LEFT  26
#define HAPTIC_RIGHT 27
#define AUDIO_PIN    32

// PWM (LEDC) channels for haptics + buzzer
#define CH_HAPTIC_FRONT 0
#define CH_HAPTIC_LEFT  1
#define CH_HAPTIC_RIGHT 2
#define CH_AUDIO        3
#define PWM_FREQ        5000
#define PWM_RES_BITS    8

// Thresholds (cm) — tune to your environment
#define OBSTACLE_NEAR_CM   40
#define OBSTACLE_WARN_CM   90
#define DROPOFF_THRESHOLD_MM 150   // if floor reading jumps beyond this -> stairs/drop

// ---------------- Shared sensor state ----------------
struct SensorState {
  float distFront_cm;
  float distLeft_cm;
  float distRight_cm;
  uint16_t floorDist_mm;
  bool dropoffDetected;
  float pitch_deg;     // head tilt (used to reject false triggers, e.g. looking down)
  float roll_deg;
  float yaw_rate_dps;
  float accelX, accelY; // for 2D dead-reckoning
  float posX_m, posY_m; // integrated position estimate
  unsigned long lastUpdateMs;
};

SensorState g_state;
SemaphoreHandle_t g_stateMutex;

Adafruit_VL53L0X g_tof = Adafruit_VL53L0X();
Adafruit_MPU6050 g_mpu;

// complementary filter state
float g_pitch = 0, g_roll = 0;
// dead-reckoning velocity (very drift-prone; reset on stationary detection)
float g_velX = 0, g_velY = 0;
unsigned long g_lastImuMs = 0;

// ---------------- Ultrasonic read (blocking, but short + isolated to core 0) ----------------
float readUltrasonicCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // 25ms timeout ~= 4m range cap, keeps loop timing bounded
  long duration = pulseIn(echoPin, HIGH, 25000UL);
  if (duration == 0) return -1.0f; // no echo / out of range

  float distance = duration * 0.0343f / 2.0f;
  return distance;
}

// ---------------- Sensor Task (Core 0) ----------------
void sensorTask(void *param) {
  const TickType_t period = pdMS_TO_TICKS(50); // 20Hz
  TickType_t lastWake = xTaskGetTickCount();

  for (;;) {
    float f = readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);
    float l = readUltrasonicCM(TRIG_LEFT, ECHO_LEFT);
    float r = readUltrasonicCM(TRIG_RIGHT, ECHO_RIGHT);

    VL53L0X_RangingMeasurementData_t measure;
    g_tof.rangingTest(&measure, false);
    uint16_t floorMM = (measure.RangeStatus != 4) ? measure.RangeMillimeter : 0;

    sensors_event_t a, g, temp;
    g_mpu.getEvent(&a, &g, &temp);

    unsigned long now = millis();
    float dt = (g_lastImuMs == 0) ? 0.05f : (now - g_lastImuMs) / 1000.0f;
    g_lastImuMs = now;

    // --- complementary filter: fuse accel-derived angle with gyro rate ---
    float accPitch = atan2(a.acceleration.y, a.acceleration.z) * 180.0f / PI;
    float accRoll  = atan2(-a.acceleration.x, a.acceleration.z) * 180.0f / PI;
    float gyroPitchRate = g.gyro.x * 180.0f / PI;
    float gyroRollRate  = g.gyro.y * 180.0f / PI;

    const float ALPHA = 0.98f; // trust gyro short-term, accel long-term
    g_pitch = ALPHA * (g_pitch + gyroPitchRate * dt) + (1 - ALPHA) * accPitch;
    g_roll  = ALPHA * (g_roll  + gyroRollRate  * dt) + (1 - ALPHA) * accRoll;

    // --- crude 2D dead reckoning (drift-prone by nature) ---
    // Zero-velocity update: if accel magnitude ~= gravity and gyro is near
    // still, assume stationary and reset velocity to fight drift.
    float accelMag = sqrt(sq(a.acceleration.x) + sq(a.acceleration.y) + sq(a.acceleration.z));
    bool stationary = (fabs(accelMag - 9.81f) < 0.15f) && (fabs(g.gyro.x) < 0.03f) && (fabs(g.gyro.y) < 0.03f);

    if (stationary) {
      g_velX = 0; g_velY = 0;
    } else {
      g_velX += a.acceleration.x * dt;
      g_velY += a.acceleration.y * dt;
    }

    // --- head-orientation false-trigger rejection ---
    // if user's head/unit is tilted sharply down/up beyond this, ultrasonic
    // readings are likely floor/ceiling, not real obstacles -> flag caller
    bool orientationValid = (fabs(g_pitch) < 30.0f) && (fabs(g_roll) < 30.0f);

    if (xSemaphoreTake(g_stateMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
      g_state.distFront_cm = orientationValid ? f : -1;
      g_state.distLeft_cm  = orientationValid ? l : -1;
      g_state.distRight_cm = orientationValid ? r : -1;
      g_state.floorDist_mm = floorMM;
      g_state.dropoffDetected = (floorMM > 0) && (floorMM > DROPOFF_THRESHOLD_MM);
      g_state.pitch_deg = g_pitch;
      g_state.roll_deg = g_roll;
      g_state.yaw_rate_dps = g.gyro.z * 180.0f / PI;
      g_state.accelX = a.acceleration.x;
      g_state.accelY = a.acceleration.y;
      g_state.posX_m += g_velX * dt;
      g_state.posY_m += g_velY * dt;
      g_state.lastUpdateMs = now;
      xSemaphoreGive(g_stateMutex);
    }

    vTaskDelayUntil(&lastWake, period);
  }
}

// ---------------- Decision Task (Core 1) ----------------
enum AlertZone { NONE, WARN, NEAR };

AlertZone classify(float distCm) {
  if (distCm < 0) return NONE;          // no echo = clear / out of range
  if (distCm < OBSTACLE_NEAR_CM) return NEAR;
  if (distCm < OBSTACLE_WARN_CM) return WARN;
  return NONE;
}

void setHaptic(int channel, AlertZone zone) {
  // NEAR = strong steady buzz, WARN = light pulse, NONE = off
  switch (zone) {
    case NEAR: ledcWrite(channel, 255); break;
    case WARN: ledcWrite(channel, 90);  break;
    default:   ledcWrite(channel, 0);   break;
  }
}

void playDropoffAlert() {
  // distinct rapid-beep pattern for stairs/drop-off — different from
  // obstacle haptics so it's unambiguous
  for (int i = 0; i < 3; i++) {
    ledcWriteTone(CH_AUDIO, 2000);
    delay(80);
    ledcWriteTone(CH_AUDIO, 0);
    delay(80);
  }
}

#if USE_TINYML
// -----------------------------------------------------------------
// TINYML SLOT
// Replace this block once your model is trained & exported.
// Typical flow:
//   1. Export model as model_data.h (xxd -i model.tflite > model_data.h)
//   2. tflite::MicroInterpreter set up once in setup()
//   3. Fill input tensor from SensorState fields below
//   4. interpreter->Invoke()
//   5. Read output tensor -> zone decisions per direction
// This is left as a stub so the file compiles either way.
// -----------------------------------------------------------------
AlertZone runTinyMLInference(const SensorState &s, int direction) {
  // TODO: fill input tensor with s.distFront_cm / distLeft_cm / distRight_cm /
  // pitch_deg / roll_deg / accelX / accelY as your model expects, call
  // interpreter->Invoke(), map output back to AlertZone.
  return NONE;
}
#endif

void decisionTask(void *param) {
  const TickType_t period = pdMS_TO_TICKS(50);
  TickType_t lastWake = xTaskGetTickCount();

  for (;;) {
    SensorState local;
    if (xSemaphoreTake(g_stateMutex, pdMS_TO_TICKS(10)) == pdTRUE) {
      local = g_state;
      xSemaphoreGive(g_stateMutex);
    }

    AlertZone zFront, zLeft, zRight;

#if USE_TINYML
    zFront = runTinyMLInference(local, 0);
    zLeft  = runTinyMLInference(local, 1);
    zRight = runTinyMLInference(local, 2);
#else
    zFront = classify(local.distFront_cm);
    zLeft  = classify(local.distLeft_cm);
    zRight = classify(local.distRight_cm);
#endif

    setHaptic(CH_HAPTIC_FRONT, zFront);
    setHaptic(CH_HAPTIC_LEFT, zLeft);
    setHaptic(CH_HAPTIC_RIGHT, zRight);

    if (local.dropoffDetected) {
      playDropoffAlert();
    }

    vTaskDelayUntil(&lastWake, period);
  }
}

// ---------------- Setup ----------------
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_FRONT, OUTPUT); pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_LEFT, OUTPUT);  pinMode(ECHO_LEFT, INPUT);
  pinMode(TRIG_RIGHT, OUTPUT); pinMode(ECHO_RIGHT, INPUT);

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!g_tof.begin()) {
    Serial.println("VL53L0X not found - check wiring");
  }
  if (!g_mpu.begin()) {
    Serial.println("MPU6050 not found - check wiring");
  }
  g_mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  g_mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  g_mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  ledcSetup(CH_HAPTIC_FRONT, PWM_FREQ, PWM_RES_BITS);
  ledcAttachPin(HAPTIC_FRONT, CH_HAPTIC_FRONT);
  ledcSetup(CH_HAPTIC_LEFT, PWM_FREQ, PWM_RES_BITS);
  ledcAttachPin(HAPTIC_LEFT, CH_HAPTIC_LEFT);
  ledcSetup(CH_HAPTIC_RIGHT, PWM_FREQ, PWM_RES_BITS);
  ledcAttachPin(HAPTIC_RIGHT, CH_HAPTIC_RIGHT);
  ledcSetup(CH_AUDIO, 2000, 10);
  ledcAttachPin(AUDIO_PIN, CH_AUDIO);

  g_stateMutex = xSemaphoreCreateMutex();
  memset(&g_state, 0, sizeof(g_state));

  xTaskCreatePinnedToCore(sensorTask, "sensorTask", 4096, NULL, 2, NULL, 0);
  xTaskCreatePinnedToCore(decisionTask, "decisionTask", 4096, NULL, 2, NULL, 1);
}

void loop() {
  // Everything runs in the two FreeRTOS tasks above; nothing needed here.
  vTaskDelay(pdMS_TO_TICKS(1000));
}
