"""Brightness and contrast signals from grayscale pixels."""

import numpy as np

from bruz_ocr.config import Settings
from bruz_ocr.quality.models import QualityCheckResult, QualityStatus


def assess_brightness(gray: np.ndarray, settings: Settings) -> QualityCheckResult:
    mean = float(gray.mean())
    if mean < settings.quality_brightness_fail_low:
        status, reason = QualityStatus.FAIL, "Page is extremely dark."
    elif mean < settings.quality_brightness_low:
        status, reason = QualityStatus.WARNING, "Page may be too dark for reliable OCR."
    elif mean > settings.quality_brightness_fail_high:
        status, reason = QualityStatus.FAIL, "Page is almost entirely bright or washed out."
    elif mean > settings.quality_brightness_high:
        status, reason = QualityStatus.WARNING, "Page may be too bright or washed out."
    else:
        status, reason = QualityStatus.PASS, "Average brightness is within the configured range."
    return QualityCheckResult(
        name="brightness",
        status=status,
        score=mean,
        value=mean,
        threshold={
            "fail_below": settings.quality_brightness_fail_low,
            "warn_below": settings.quality_brightness_low,
            "warn_above": settings.quality_brightness_high,
            "fail_above": settings.quality_brightness_fail_high,
        },
        reason=reason,
        metadata={"method": "mean_grayscale"},
    )


def assess_contrast(gray: np.ndarray, settings: Settings) -> QualityCheckResult:
    deviation = float(gray.std())
    if deviation < settings.quality_contrast_fail:
        status, reason = QualityStatus.FAIL, "Page has extremely low contrast."
    elif deviation < settings.quality_contrast_min:
        status, reason = QualityStatus.WARNING, "Page has low contrast; text may be faint."
    else:
        status, reason = QualityStatus.PASS, "Contrast is above the configured minimum."
    return QualityCheckResult(
        name="contrast",
        status=status,
        score=deviation,
        value=deviation,
        threshold={
            "fail_below": settings.quality_contrast_fail,
            "warn_below": settings.quality_contrast_min,
        },
        reason=reason,
        metadata={"method": "grayscale_standard_deviation"},
    )
