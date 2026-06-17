from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "Spare-Time Companion"
    ENV: str = "development"
    DATABASE_URL: str = f"sqlite:///{ROOT / 'backend' / 'app.db'}"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str
    APP_TIMEZONE: str = "Asia/Shanghai"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MODEL_NAME: str = "qwen3.7-plus"
    LLM_API_KEY: str
    LLM_BASE_URL: str
    ALI_API_KEY: str
    ASR_MODEL: str = "fun-asr"
    VOICE_MODEL: str = "cosyvoice-v3-plus"
    TTS_VOICE: str = "longxiaochun"
    STARTUP_EXTERNAL_CHECKS: bool = True
    API_TIMEOUT_SECONDS: float = 20.0
    MAX_AUDIO_BYTES: int = 10 * 1024 * 1024

    @field_validator("MODEL_NAME", mode="before")
    @classmethod
    def force_qwen(cls, value: str | None) -> str:
        return value or "qwen3.7-plus"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def validate_public_demo_secrets(self) -> None:
        weak = {
            "admin",
            "admin123456",
            "password",
            "password123",
            "12345678",
            "changeme",
            "replacewith_strongpassword_2026!",
        }
        password = self.ADMIN_PASSWORD
        has_upper = any(ch.isupper() for ch in password)
        has_lower = any(ch.islower() for ch in password)
        has_digit = any(ch.isdigit() for ch in password)
        has_symbol = any(not ch.isalnum() for ch in password)
        if (
            len(password) < 14
            or password.lower() in weak
            or not (has_upper and has_lower and has_digit and has_symbol)
        ):
            raise ValueError(
                "ADMIN_PASSWORD must be a strong .env secret: at least 14 chars with upper, "
                "lower, digit, and symbol; public demo must not use defaults."
            )
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY == "change-me-before-public-demo":
            raise ValueError("SECRET_KEY must be set in .env and be at least 32 characters.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
