"""
audio_feedback.py — TTS + Tone Audio Feedback

Sends spoken guidance cues to the Bluetooth headphone.
Uses pyttsx3 for offline TTS (no network required for audio guidance).
Falls back to a simple beep pattern if TTS is unavailable.

Priority: urgent cues interrupt any ongoing speech.
"""

import threading
import time
import queue
import logging

log = logging.getLogger(__name__)

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False
    log.warning("[Audio] pyttsx3 not installed — TTS disabled. Install: pip install pyttsx3")


class AudioFeedback:
    """Thread-safe TTS audio feedback queue."""

    def __init__(self, rate: int = 180, volume: float = 1.0):
        self._queue  = queue.PriorityQueue()  # (priority, text) — lower priority = higher urgency
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._running = False
        self._rate   = rate
        self._volume = volume

        if _TTS_AVAILABLE:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", rate)
            self._engine.setProperty("volume", volume)
        else:
            self._engine = None

    def start(self):
        self._running = True
        self._thread.start()

    def stop(self):
        self._running = False
        self._queue.put((0, None))  # sentinel

    def speak(self, text: str, urgent: bool = False):
        """Queue a speech utterance. Urgent cues get priority 1, normal get 5."""
        if not text:
            return
        priority = 1 if urgent else 5
        self._queue.put((priority, text))

    def _worker(self):
        while self._running:
            try:
                priority, text = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if text is None:
                break
            self._say(text)

    def _say(self, text: str):
        if self._engine:
            try:
                # Flush any pending speech if this is urgent
                self._engine.stop()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e:
                log.error(f"[Audio] TTS error: {e}")
        else:
            # Fallback: log to console (useful during headless testing)
            log.info(f"[Audio] >> {text}")
            print(f"[Audio] >> {text}")
