# Wiring Reference — Blind Navigation Aid (ESP32 DevKit)

## Bus / Power summary
- 3× HC-SR04 run on **5V** logic (VCC=5V). Their ECHO pin outputs 5V — this WILL
  damage an ESP32 GPIO if wired directly. Each ECHO must go through a
  voltage divider before reaching the ESP32.
- VL53L0X (ToF drop-off sensor) and MPU6050 (IMU) both run on **3.3V** and share
  the same I2C bus (different addresses, no conflict — no XSHUT wiring needed).
- Common GND across ESP32, 5V rail, and 3.3V rail is mandatory. If any module
  floats on a separate ground, readings will be noisy/wrong.

## Voltage divider (build 3× — one per HC-SR04 ECHO pin)
```
HC-SR04 ECHO ---[ R1: 1kΩ ]---+---[ R2: 2kΩ ]--- GND
                               |
                               +--- ESP32 GPIO (echo in)
```
This gives ESP32 ≈ 5V × 2k/(1k+2k) = **3.33V** — safe for the GPIO input.
Do NOT skip this. Trig pins do not need a divider — 3.3V from the ESP32 is
enough to trigger the sensor.

## Pin map

| Component              | Signal        | ESP32 GPIO | Notes                          |
|-------------------------|---------------|------------|----------------------------------|
| HC-SR04 #1 (FRONT, 0°)  | TRIG          | 5          | direct                          |
|                          | ECHO          | 18         | through divider                 |
| HC-SR04 #2 (LEFT, -60°) | TRIG          | 17         | direct                          |
|                          | ECHO          | 16         | through divider                 |
| HC-SR04 #3 (RIGHT, +60°)| TRIG          | 19         | direct                          |
|                          | ECHO          | 23         | through divider                 |
| VL53L0X (stair/drop-off)| SDA           | 21         | shared I2C bus                  |
|                          | SCL           | 22         | shared I2C bus                  |
|                          | addr          | 0x29       | default, unchanged               |
| MPU6050 (IMU)           | SDA           | 21         | shared I2C bus                  |
|                          | SCL           | 22         | shared I2C bus                  |
|                          | addr          | 0x68       | default, unchanged               |
| Haptic motor — FRONT    | PWM           | 25         | via NPN/MOSFET driver, not direct|
| Haptic motor — LEFT     | PWM           | 26         | via NPN/MOSFET driver           |
| Haptic motor — RIGHT    | PWM           | 27         | via NPN/MOSFET driver           |
| Audio (piezo/speaker)   | PWM           | 32         | swap for I2S amp (MAX98357A) later|

**Avoided on purpose:** GPIO 0, 2, 12, 15 (boot-strapping pins — using them for
sensors/outputs can prevent the board from booting or flashing if pulled the
wrong way at power-on). Also avoided GPIO 1/3 (used by Serial/USB debug).

## Haptic motors — do not drive directly from GPIO
A vibration motor draws more current than a GPIO can safely source. Use a
transistor (2N2222/NPN) or a small MOSFET as a switch:
```
GPIO(PWM) --[1kΩ]--- Base
Motor(+) --- 5V/3.3V rail
Motor(-) --- Collector
Emitter   --- GND
Flyback diode (1N4148/1N4007) across motor +/- , cathode to +
```

## Power budget note
3× HC-SR04 + VL53L0X + MPU6050 + 3 motors + ESP32 can pull more current than
the onboard 5V/3.3V regulator on some DevKits comfortably supplies,
especially motor stall current. If you see brownout resets, power the motors
from a separate 5V supply (common GND still required) rather than the ESP32's
onboard regulator.
