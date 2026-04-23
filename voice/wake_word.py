"""
Wake word detection — "Hey JARVIS"
Uses Picovoice Porcupine (free tier, runs locally, very accurate).
Falls back to a simple keyword-in-speech fallback if no API key is set.
"""
import struct
import threading
import pyaudio
from config.settings import settings


class WakeWordDetector:
    def __init__(self, on_detected: callable):
        self._on_detected = on_detected
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        if settings.picovoice_access_key:
            self._thread = threading.Thread(target=self._porcupine_loop, daemon=True)
        else:
            print("[Wake] No Picovoice key — using fallback STT detection.")
            self._thread = threading.Thread(target=self._fallback_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── Porcupine (production) ──────────────────────────────────────────────

    def _porcupine_loop(self):
        import pvporcupine
        porcupine = pvporcupine.create(
            access_key=settings.picovoice_access_key,
            keywords=["jarvis"],
        )
        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )
        print("[Wake] Listening for 'Hey JARVIS'...")
        try:
            while self._running:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    print("[Wake] 'Hey JARVIS' detected!")
                    self._on_detected()
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()
            porcupine.delete()

    # ── Fallback (no API key) ───────────────────────────────────────────────

    def _fallback_loop(self):
        """Simple fallback: transcribe short audio clips and look for 'jarvis'."""
        from voice.stt import record_until_silence, transcribe
        import time
        print("[Wake] Fallback mode: say 'jarvis' to activate.")
        while self._running:
            audio = record_until_silence(silence_duration=0.8, max_duration=3.0)
            text = transcribe(audio).lower()
            if "jarvis" in text:
                print("[Wake] Activated via fallback STT!")
                self._on_detected()
            time.sleep(0.1)
