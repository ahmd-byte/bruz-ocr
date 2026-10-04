"""Settings shared by the CLI and local API."""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BRUZ_", env_file=".env", extra="ignore")

    database_path: Path = Field(default_factory=lambda: Path.home() / ".bruz-ocr" / "bruz.db")
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".bruz-ocr" / "data")
    max_document_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    max_pages: int = Field(default=100, gt=0)
    max_page_pixels: int = Field(default=50_000_000, gt=0)
    quality_sample_max_side: int = Field(default=1600, ge=256)
    quality_blur_fail: float = Field(default=10.0, ge=0)
    quality_blur_warn: float = Field(default=60.0, gt=0)
    quality_fail_width: int = Field(default=400, gt=0)
    quality_fail_height: int = Field(default=400, gt=0)
    quality_min_width: int = Field(default=1000, gt=0)
    quality_min_height: int = Field(default=1000, gt=0)
    quality_brightness_fail_low: float = Field(default=30.0, ge=0, le=255)
    quality_brightness_low: float = Field(default=70.0, ge=0, le=255)
    quality_brightness_high: float = Field(default=250.0, ge=0, le=255)
    quality_brightness_fail_high: float = Field(default=254.0, ge=0, le=255)
    quality_contrast_fail: float = Field(default=8.0, ge=0)
    quality_contrast_min: float = Field(default=25.0, gt=0)
    quality_edge_margin_ratio: float = Field(default=0.02, gt=0, lt=0.25)
    quality_edge_density_warn: float = Field(default=0.12, gt=0, le=1)
    quality_foreground_cutoff: int = Field(default=180, ge=0, le=255)
    host: str = "127.0.0.1"
    port: int = Field(default=8787, ge=1, le=65535)
    debug: bool = False

    @model_validator(mode="after")
    def validate_quality_thresholds(self) -> "Settings":
        if not self.quality_blur_fail < self.quality_blur_warn:
            raise ValueError("BRUZ_QUALITY_BLUR_FAIL must be below BRUZ_QUALITY_BLUR_WARN")
        if not (
            self.quality_fail_width < self.quality_min_width
            and self.quality_fail_height < self.quality_min_height
        ):
            raise ValueError("Quality failure dimensions must be below warning dimensions")
        if not (
            self.quality_brightness_fail_low
            < self.quality_brightness_low
            < self.quality_brightness_high
            < self.quality_brightness_fail_high
        ):
            raise ValueError("Quality brightness thresholds must be strictly ordered")
        if not self.quality_contrast_fail < self.quality_contrast_min:
            raise ValueError("BRUZ_QUALITY_CONTRAST_FAIL must be below BRUZ_QUALITY_CONTRAST_MIN")
        return self
