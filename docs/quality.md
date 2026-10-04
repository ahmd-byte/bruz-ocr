# Document quality assessment

Quality gating exposes uncertain scan conditions before OCR runs. `QualityService` reads a `DocumentPage` image under `BRUZ_DATA_DIR`, checks that its dimensions match ingestion metadata, and returns a `PageQualityResult`. It aggregates pages into a `DocumentQualityResult` and stores the latest result per document in SQLite. A missing or unreadable page is recorded as `FAIL` with an error; other pages still run.

Checks are image-only:

| Check | Measurement | Initial warning/failure defaults |
| --- | --- | --- |
| Blur | Variance of the OpenCV Laplacian on a grayscale sample | Below 60 / below 10 |
| Resolution | Original width, height, total pixels; PDF render DPI or reported image DPI when available | Either dimension below 1000 / below 400 pixels |
| Brightness | Mean grayscale intensity, 0–255 | Outside 70–250 / outside 30–254 |
| Contrast | Grayscale standard deviation | Below 25 / below 8 |
| Crop possibility | Fraction of pixels darker than 180 in a 2% border band | Any edge at or above 0.12 warns; never fails |
| Orientation | Portrait, landscape, or square geometry | Reading orientation remains `UNKNOWN`; geometry does not trigger failure |

`FAIL` dominates `WARNING`, which dominates `PASS`. Each check retains a measured value, thresholds, and a plain-language reason. The crop heuristic signals possible missing margins, not proof of cropping. Reading orientation cannot be established reliably from geometry alone.

Pixels are downscaled to a maximum side of 1600 before blur, tone, and edge measurements; original dimensions remain the basis for resolution. This can change measured blur values. Every threshold is configurable through the matching `BRUZ_QUALITY_*` setting in `.env.example`. These defaults are starting points and must be calibrated on representative customer scans before using quality status as an operational acceptance rule. The assessment performs no OCR and does not change stored pages.

Use `bruz-ocr quality <document-id>` for a concise result or append `--json` for all metrics. Reassessment replaces the previous stored result and includes `algorithm_version=1` for future comparisons.
