from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )
    database_url: str = f"sqlite+aiosqlite:///{(BASE_DIR / 'books.db').as_posix()}"
    jwt_secret_key: str = Field(min_length=32)


settings = Settings()
