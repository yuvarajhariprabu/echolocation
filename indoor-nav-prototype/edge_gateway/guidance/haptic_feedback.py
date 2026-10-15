"""
haptic_feedback.py — Vibration Motor Controller

Encodes guidance cues as PWM duty cycles for 3 vibration motors:
  Motor 0 = FRONT (direction: ahead)
  Motor 1 = LEFT
  Motor 2 = RIGHT

On RPi: uses RPi.GPIO PWM.
On laptop/simulation: logs intensity values only (for testing without hardware).

Intensity encoding:
  0   = OFF (no obstacle)
  90  = WARN (obstacle in warning zone ~40–90cm)
  255 = NEAR (obstacle in danger zone <40cm)

Pattern encoding (for special alerts):
  "dropoff" = rapid triple-pulse on all 3 motors simultaneously
  "caution" = slow single pulse on front motor
"""

import time
import logging
import threading

log = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    _GPIO_AVAILABLE = True
except ImportError:
    _GPIO_AVAILABLE = False
    log.info("[Haptic] RPi.GPIO not available — running in simulation mode")


class HapticFeedback:

    # Pin configuration — update to match your RPi GPIO wiring
    # These are BCM pin numbers on Raspberry Pi
    MOTOR_PINS = {
        "front": 17,
        "left":  27,
        "right": 22,
    }
    PWM_FREQ = 100  # Hz

    def __init__(self, simulate: bool = False):
        self._simulate = simulate or not _GPIO_AVAILABLE
        self._pwm = {}

        if not self._simulate:
            GPIO.setmode(GPIO.BCM)
            for name, pin in self.MOTOR_PINS.items():
                GPIO.setup(pin, GPIO.OUT)
                pwm = GPIO.PWM(pin, self.PWM_FREQ)
                pwm.start(0)
                self._pwm[name] = pwm

    def set(self, front: int = 0, left: int = 0, right: int = 0):
        """Set motor intensities (0–255)."""
        values = {"front": front, "left": left, "right": right}
        for name, intensity in values.items():
            duty = (intensity / 255.0) * 100.0  # convert to duty cycle %
            if self._simulate:
                log.debug(f"[Haptic] {name}={intensity}")
            else:
                self._pwm[name].ChangeDutyCycle(duty)

    def pattern_dropoff(self):
        """Triple rapid pulse on all motors — run in background thread (non-blocking)."""
        threading.Thread(target=self._pattern_dropoff_blocking, daemon=True).start()

    def _pattern_dropoff_blocking(self):
        for _ in range(3):
            self.set(255, 255, 255)
            time.sleep(0.08)
            self.set(0, 0, 0)
            time.sleep(0.08)
        if self._simulate:
            print("[Haptic] *** DROP-OFF ALERT ***")

    def pattern_caution(self):
        """Single slow pulse — run in background thread (non-blocking)."""
        threading.Thread(target=self._pattern_caution_blocking, daemon=True).start()

    def _pattern_caution_blocking(self):
        self.set(90, 0, 0)
        time.sleep(0.3)
        self.set(0, 0, 0)
        if self._simulate:
            print("[Haptic] * caution *")

    def all_off(self):
        self.set(0, 0, 0)

    def cleanup(self):
        self.all_off()
        if not self._simulate:
            GPIO.cleanup()
