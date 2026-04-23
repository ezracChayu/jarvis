from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Claude API
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")

    # Picovoice wake word
    picovoice_access_key: str = Field("", env="PICOVOICE_ACCESS_KEY")

    # Server
    jarvis_host: str = Field("0.0.0.0", env="JARVIS_HOST")
    jarvis_port: int = Field(7799, env="JARVIS_PORT")

    # Voice
    tts_voice: str = Field("en-GB-RyanNeural", env="TTS_VOICE")
    whisper_model: str = Field("base", env="WHISPER_MODEL")

    # Database
    db_path: str = Field("jarvis_memory.db", env="DB_PATH")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
