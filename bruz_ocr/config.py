"""Settings shared by the CLI and local API."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRUZ_", env_file=".env", extra="ignore")

    database_path: Path = Field(default_factory=lambda: Path.home() / ".bruz-ocr" / "bruz.db")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".bruz-ocr" / "data")
    max_document_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=100, gt=0)
    max_page_pixels: int = Field(default=50_000_000, gt=0)
    host: str = "127.0.0.1"
    port: int = Field(default=8787, ge=1, le=65535)
    debug: bool = False
