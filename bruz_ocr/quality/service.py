"""Orchestrate local page checks and aggregate document quality."""

import logging
import sqlite3
import time
import warnings
from datetime import UTC, datetime

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from bruz_ocr.capture.models import Document, DocumentPage
from bruz_ocr.config import Settings
from bruz_ocr.quality.blur import assess_blur
from bruz_ocr.quality.crop import assess_crop
from bruz_ocr.quality.errors import PageImageUnavailableError, QualityAssessmentError
from bruz_ocr.quality.geometry import assess_orientation, assess_resolution
from bruz_ocr.quality.models import (
    DocumentQualityResult,
    PageQualityResult,
    QualityCheckResult,
    QualityStatus,
    aggregate_status,
)
from bruz_ocr.quality.repository import QualityRepository
from bruz_ocr.quality.tone import assess_brightness, assess_contrast

LOGGER = logging.getLogger(__name__)


class QualityService:
    def __init__(self, settings: Settings, repository: QualityRepository | None = None) -> None:
        self.settings = settings
        self.repository = repository

    def assess_page(self, page: DocumentPage, document_id: str) -> PageQualityResult:
        started = time.perf_counter()
        LOGGER.info(
            "quality_page_started",
            extra={"document_id": document_id, "page_number": page.page_number},
        )
        try:
            gray = self._read_sample(page)
            checks = [
                assess_resolution(page, self.settings),
                assess_orientation(page),
                assess_blur(gray, self.settings),
                assess_brightness(gray, self.settings),
                assess_contrast(gray, self.settings),
                assess_crop(gray, self.settings),
            ]
        except cv2.error as error:
            raise QualityAssessmentError(
                f"Page {page.page_number} image analysis failed."
            ) from error
        for check in checks:
            self._log_check(document_id, page.page_number, check)
        duration_ms = (time.perf_counter() - started) * 1000
        result = PageQualityResult(
            document_id=document_id,
            page_number=page.page_number,
            overall_status=aggregate_status([check.status for check in checks]),
            checks=checks,
            assessed_at=datetime.now(UTC),
            duration_ms=duration_ms,
        )
        LOGGER.info(
            "quality_page_completed",
            extra={
                "document_id": document_id,
                "page_number": page.page_number,
                "status": result.overall_status.value,
                "duration_ms": round(duration_ms),
            },
        )
        return result

    def assess_document(self, document: Document) -> DocumentQualityResult:
        started = time.perf_counter()
        LOGGER.info("quality_assessment_started", extra={"document_id": document.document_id})
        pages: list[PageQualityResult] = []
        for page in document.pages:
            page_started = time.perf_counter()
            try:
                pages.append(self.assess_page(page, document.document_id))
            except QualityAssessmentError as error:
                LOGGER.error(
                    "quality_assessment_failed",
                    extra={
                        "document_id": document.document_id,
                        "page_number": page.page_number,
                        "error_type": type(error).__name__,
                    },
                )
                pages.append(
                    PageQualityResult(
                        document_id=document.document_id,
                        page_number=page.page_number,
                        overall_status=QualityStatus.FAIL,
                        checks=[],
                        assessed_at=datetime.now(UTC),
                        duration_ms=(time.perf_counter() - page_started) * 1000,
                        error=str(error),
                    )
                )
        statuses = [page.overall_status for page in pages]
        result = DocumentQualityResult(
            document_id=document.document_id,
            overall_status=aggregate_status(statuses),
            pages=pages,
            summary={status.value: statuses.count(status) for status in QualityStatus},
            assessed_at=datetime.now(UTC),
            duration_ms=(time.perf_counter() - started) * 1000,
        )
        try:
            repository = self.repository or QualityRepository(self.settings.database_path)
            repository.save(result)
        except (OSError, sqlite3.Error, RuntimeError) as error:
            LOGGER.error(
                "quality_assessment_failed",
                extra={"document_id": document.document_id, "error_type": type(error).__name__},
            )
            raise QualityAssessmentError(
                "Could not save the quality assessment locally."
            ) from error
        LOGGER.info(
            "quality_assessment_completed",
            extra={
                "document_id": document.document_id,
                "status": result.overall_status.value,
                "duration_ms": round(result.duration_ms),
            },
        )
        return result

    def _read_sample(self, page: DocumentPage) -> np.ndarray:
        data_dir = self.settings.data_dir.expanduser().resolve()
        path = (data_dir / page.image_path).resolve()
        if not path.is_relative_to(data_dir):
            raise PageImageUnavailableError(
                f"Page {page.page_number} has an invalid image reference."
            )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    if image.size != (page.width, page.height):
                        raise QualityAssessmentError(
                            f"Page {page.page_number} dimensions differ from ingestion metadata."
                        )
                    if image.width * image.height > self.settings.max_page_pixels:
                        raise QualityAssessmentError(
                            f"Page {page.page_number} exceeds the configured pixel limit."
                        )
                    image.load()
                    gray = np.asarray(image.convert("L"))
        except (
            OSError,
            UnidentifiedImageError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ) as error:
            raise PageImageUnavailableError(
                f"Page {page.page_number} image is missing or unreadable."
            ) from error
        max_side = self.settings.quality_sample_max_side
        if max(gray.shape) > max_side:
            factor = max_side / max(gray.shape)
            width = max(1, round(gray.shape[1] * factor))
            height = max(1, round(gray.shape[0] * factor))
            gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_AREA)
        return gray

    @staticmethod
    def _log_check(document_id: str, page_number: int, check: QualityCheckResult) -> None:
        LOGGER.info(
            "quality_check_completed",
            extra={
                "document_id": document_id,
                "page_number": page_number,
                "check": check.name,
                "status": check.status.value,
            },
        )
