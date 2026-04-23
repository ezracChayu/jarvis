"""
JARVIS — Entry Point
====================
מריץ שלושה דברים במקביל:
  1. שרת WebSocket (לטלפון ומכשירים אחרים)
  2. זיהוי wake word ("Hey JARVIS") ברקע
  3. לולאת קול על ה-PC
"""
import asyncio
import threading
import uvicorn
from core.server import app
from core import memory as mem
from core.brain import think
from voice.wake_word import WakeWordDetector
from voice.stt import load_model, listen_and_transcribe
from voice.tts import speak


# ─── Voice loop ───────────────────────────────────────────────────────────────

async def handle_voice_query():
    """Called once after wake word is detected."""
    await speak("Yes?")
    user_input = listen_and_transcribe()
    if not user_input:
        await speak("I didn't catch that. Please try again.")
        return
    reply = await think(user_input, device_id="pc")
    await speak(reply)


def on_wake_word():
    """Called from the wake word detector thread."""
    asyncio.run(handle_voice_query())


# ─── Server thread ────────────────────────────────────────────────────────────

def run_server():
    from config.settings import settings
    uvicorn.run(
        app,
        host=settings.jarvis_host,
        port=settings.jarvis_port,
        log_level="warning",
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    # Init database
    await mem.init_db()

    # Load Whisper model in background (heavy first load)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, load_model)

    # Start WebSocket server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("[JARVIS] Hub running at http://localhost:7799")

    # Start wake word detector
    detector = WakeWordDetector(on_detected=on_wake_word)
    detector.start()
    print("[JARVIS] Ready. Say 'Hey JARVIS' to activate.")

    # Keep the main thread alive
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n[JARVIS] Shutting down...")
        detector.stop()
        await mem.close_db()


if __name__ == "__main__":
    asyncio.run(main())
