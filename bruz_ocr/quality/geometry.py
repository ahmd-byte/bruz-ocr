"""Dimension and honest orientation geometry checks."""

from bruz_ocr.capture.models import DocumentPage
from bruz_ocr.config import Settings
from bruz_ocr.quality.models import QualityCheckResult, QualityStatus


def assess_resolution(page: DocumentPage, settings: Settings) -> QualityCheckResult:
    if page.width < settings.quality_fail_width or page.height < settings.quality_fail_height:
        status = QualityStatus.FAIL
        reason = "Page dimensions are too small for reliable OCR."
    elif page.width < settings.quality_min_width or page.height < settings.quality_min_height:
        status = QualityStatus.WARNING
        reason = "Page dimensions are below the recommended OCR size."
    else:
        status = QualityStatus.PASS
        reason = "Page dimensions meet the configured minimum."
    return QualityCheckResult(
        name="resolution",
        status=status,
        value=f"{page.width}x{page.height}",
        threshold={
            "fail_width_below": settings.quality_fail_width,
            "fail_height_below": settings.quality_fail_height,
            "warn_width_below": settings.quality_min_width,
            "warn_height_below": settings.quality_min_height,
        },
        reason=reason,
        metadata={
            "width": page.width,
            "height": page.height,
            "total_pixels": page.width * page.height,
            "render_dpi": page.metadata.get("render_dpi"),
            "reported_dpi": page.metadata.get("reported_dpi"),
        },
    )


def assess_orientation(page: DocumentPage) -> QualityCheckResult:
    geometry = "portrait" if page.height > page.width else "landscape"
    if page.height == page.width:
        geometry = "square"
    return QualityCheckResult(
        name="orientation",
        status=QualityStatus.PASS,
        value="UNKNOWN",
        reason=f"Page geometry is {geometry}; reading orientation cannot be inferred without OCR.",
        metadata={
            "geometry": geometry,
            "reading_orientation": "UNKNOWN",
            "reading_orientation_assessed": False,
        },
    )
