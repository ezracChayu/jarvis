"""
Speech-to-Text via faster-whisper (runs fully local, no API cost).
Model is loaded once at startup and reused for every transcription.
"""
import io
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from config.settings import settings


_model: WhisperModel | None = None


def load_model():
    global _model
    print(f"[STT] Loading Whisper model '{settings.whisper_model}'...")
    _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    print("[STT] Model ready.")


def record_until_silence(
    sample_rate: int = 16000,
    silence_threshold: float = 0.01,
    silence_duration: float = 1.5,
    max_duration: float = 15.0,
) -> np.ndarray:
    """Record microphone input until silence is detected."""
    chunk_size = int(sample_rate * 0.1)
    silence_chunks = int(silence_duration / 0.1)
    max_chunks = int(max_duration / 0.1)

    frames = []
    silent_count = 0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            frames.append(chunk)
            rms = np.sqrt(np.mean(chunk**2))
            if rms < silence_threshold:
                silent_count += 1
                if silent_count >= silence_chunks and len(frames) > silence_chunks * 2:
                    break
            else:
                silent_count = 0

    return np.concatenate(frames, axis=0).flatten()


def transcribe(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe a numpy audio array to text."""
    if _model is None:
        load_model()
    segments, _ = _model.transcribe(audio, language="en", beam_size=5)
    return " ".join(s.text.strip() for s in segments).strip()


def listen_and_transcribe() -> str:
    """One-shot: record until silence, then transcribe."""
    print("[STT] Listening...")
    audio = record_until_silence()
    text = transcribe(audio)
    print(f"[STT] Heard: {text!r}")
    return text
