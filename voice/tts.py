import asyncio
import tempfile
import os
import edge_tts
import pygame
from config.settings import settings


pygame.mixer.init()


async def speak(text: str):
    """Convert text to speech and play through speakers."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        communicate = edge_tts.Communicate(text, settings.tts_voice)
        await communicate.save(tmp_path)
        _play_mp3(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _play_mp3(path: str):
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)


def speak_sync(text: str):
    asyncio.run(speak(text))
