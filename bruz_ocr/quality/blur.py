"""Variance-of-Laplacian blur signal on a bounded grayscale sample."""

import cv2
import numpy as np

from bruz_ocr.config import Settings
from bruz_ocr.quality.models import QualityCheckResult, QualityStatus


def assess_blur(gray: np.ndarray, settings: Settings) -> QualityCheckResult:
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    if variance < settings.quality_blur_fail:
        status = QualityStatus.FAIL
        reason = "Page appears severely blurred or lacks detectable edges."
    elif variance < settings.quality_blur_warn:
        status = QualityStatus.WARNING
        reason = "Page appears moderately blurred; text may be difficult to read."
    else:
        status = QualityStatus.PASS
        reason = "No strong blur signal detected."
    return QualityCheckResult(
        name="blur",
        status=status,
        score=variance,
        value=variance,
        threshold={
            "fail_below": settings.quality_blur_fail,
            "warn_below": settings.quality_blur_warn,
        },
        reason=reason,
        metadata={"method": "laplacian_variance", "sample_size": [gray.shape[1], gray.shape[0]]},
    )
