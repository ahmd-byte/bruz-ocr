"""Conservative border-content signal; never proves a page was cropped."""

import numpy as np

from bruz_ocr.config import Settings
from bruz_ocr.quality.models import QualityCheckResult, QualityStatus


def assess_crop(gray: np.ndarray, settings: Settings) -> QualityCheckResult:
    band = max(1, round(min(gray.shape) * settings.quality_edge_margin_ratio))
    foreground = gray < settings.quality_foreground_cutoff
    densities = {
        "top": float(np.mean(foreground[:band, :])),
        "bottom": float(np.mean(foreground[-band:, :])),
        "left": float(np.mean(foreground[:, :band])),
        "right": float(np.mean(foreground[:, -band:])),
    }
    edge = max(densities, key=densities.__getitem__)
    score = densities[edge]
    if score >= settings.quality_edge_density_warn:
        status = QualityStatus.WARNING
        reason = f"Content is unusually close to the {edge} edge; page may be cropped."
    else:
        status = QualityStatus.PASS
        reason = "No unusually dense content was detected along the page edges."
    return QualityCheckResult(
        name="crop",
        status=status,
        score=score,
        value=edge,
        threshold={"warn_at_or_above": settings.quality_edge_density_warn},
        reason=reason,
        metadata={
            "edge_density": densities,
            "margin_pixels": band,
            "margin_ratio": settings.quality_edge_margin_ratio,
            "foreground_cutoff": settings.quality_foreground_cutoff,
        },
    )
