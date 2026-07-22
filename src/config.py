from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень проекта (папка с run.py, .env, data/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr = SecretStr("")
    database_path: Path = Path("./data/seednox.db")
    # SQLCipher: ключ шифрования файла БД (опционально, Linux/Docker + sqlcipher3)
    db_encryption_key: SecretStr | None = None
    allowed_user_ids: list[int] | None = None

    # Настройки обхода блокировок Telegram (для РФ)
    telegram_proxy: str | None = None  # например: socks5://127.0.0.1:1080 или http://proxy:8080
    telegram_api_url: str | None = None  # кастомный зеркало-сервер Telegram API

    session_timeout: int = Field(default=900, ge=60, le=3600)
    max_password_attempts: int = Field(default=5, ge=3, le=10)
    lockout_duration: int = Field(default=900, ge=300, le=3600)

    argon2_time_cost: int = Field(default=3, ge=2, le=10)
    argon2_memory_cost: int = Field(default=65536, ge=16384, le=262144)
    argon2_parallelism: int = Field(default=4, ge=1, le=8)

    min_password_length: int = 12
    max_wallet_name_length: int = 64
    max_wallets_per_user: int = 100

    @field_validator("database_path", mode="before")
    @classmethod
    def resolve_database_path(cls, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def parse_allowed_user_ids(cls, value: any) -> list[int] | None:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return [int(value)]
        if isinstance(value, list):
            return [int(x) for x in value if str(x).strip().lstrip('-').isdigit()]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            if value.startswith("[") and value.endswith("]"):
                import json
                try:
                    parsed = json.loads(value)
                    return [int(x) for x in parsed]
                except Exception:
                    pass
            return [int(x.strip()) for x in value.split(",") if x.strip().lstrip('-').isdigit()]
        try:
            return [int(value)]
        except (ValueError, TypeError):
            return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
