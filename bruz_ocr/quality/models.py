"""Serializable quality results independent of OCR providers."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class QualityStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class QualityCheckResult(BaseModel):
    name: str
    status: QualityStatus
    score: float | None = None
    value: float | int | str | None = None
    threshold: dict[str, float | int] = Field(default_factory=dict)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageQualityResult(BaseModel):
    document_id: str
    page_number: int
    overall_status: QualityStatus
    checks: list[QualityCheckResult]
    assessed_at: datetime
    duration_ms: float
    error: str | None = None


class DocumentQualityResult(BaseModel):
    document_id: str
    overall_status: QualityStatus
    pages: list[PageQualityResult]
    summary: dict[str, int]
    assessed_at: datetime
    duration_ms: float
    algorithm_version: int = 1


def aggregate_status(statuses: list[QualityStatus]) -> QualityStatus:
    if not statuses or QualityStatus.FAIL in statuses:
        return QualityStatus.FAIL
    if QualityStatus.WARNING in statuses:
        return QualityStatus.WARNING
    return QualityStatus.PASS
