"""Settings shared by the CLI and local API."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRUZ_", env_file=".env", extra="ignore")

    database_path: Path = Field(default_factory=lambda: Path.home() / ".bruz-ocr" / "bruz.db")
    host: str = "127.0.0.1"
    port: int = Field(default=8787, ge=1, le=65535)
    debug: bool = False
