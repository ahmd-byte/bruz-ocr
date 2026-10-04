import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from bruz_ocr.capture.models import Document, DocumentPage
from bruz_ocr.capture.repository import DocumentRepository
from bruz_ocr.capture.service import DocumentIngestionService
from bruz_ocr.cli import app
from bruz_ocr.config import Settings
from bruz_ocr.quality.blur import assess_blur
from bruz_ocr.quality.crop import assess_crop
from bruz_ocr.quality.errors import PageImageUnavailableError
from bruz_ocr.quality.geometry import assess_orientation, assess_resolution
from bruz_ocr.quality.models import QualityStatus, aggregate_status
from bruz_ocr.quality.repository import QualityRepository
from bruz_ocr.quality.service import QualityService
from bruz_ocr.quality.tone import assess_brightness, assess_contrast


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "state.db",
        data_dir=tmp_path / "data",
        quality_fail_width=100,
        quality_fail_height=100,
        quality_min_width=200,
        quality_min_height=200,
    )


def checkerboard(size: int = 256) -> np.ndarray:
    y, x = np.indices((size, size))
    return np.where((x // 8 + y // 8) % 2 == 0, 255, 0).astype(np.uint8)


def create_document(settings: Settings, images: list[np.ndarray]) -> Document:
    document_id = "quality-test-document"
    pages: list[DocumentPage] = []
    for index, pixels in enumerate(images, start=1):
        relative_path = f"documents/{document_id}/pages/page-{index:04d}.png"
        image_path = settings.data_dir / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(pixels).save(image_path)
        pages.append(
            DocumentPage(
                page_number=index,
                width=pixels.shape[1],
                height=pixels.shape[0],
                image_path=relative_path,
            )
        )
    document = Document(
        document_id=document_id,
        original_filename="synthetic.png",
        storage_path=f"documents/{document_id}/original.png",
        file_type="PNG",
        mime_type="image/png",
        sha256="0" * 64,
        file_size_bytes=1,
        page_count=len(pages),
        created_at=datetime.now(UTC),
        pages=pages,
    )
    DocumentRepository(settings.database_path).save(document)
    return document


def check(result, name: str):
    return next(item for item in result.checks if item.name == name)


def test_sharp_and_heavily_blurred_pages(settings: Settings) -> None:
    sharp = checkerboard()
    blurred = cv2.GaussianBlur(sharp, (0, 0), 8)
    sharp_result = assess_blur(sharp, settings)
    blurred_result = assess_blur(blurred, settings)
    assert sharp_result.status == QualityStatus.PASS
    assert blurred_result.status in (QualityStatus.WARNING, QualityStatus.FAIL)
    assert blurred_result.score is not None and sharp_result.score is not None
    assert blurred_result.score < sharp_result.score


def test_very_dark_and_bright_pages(settings: Settings) -> None:
    dark = assess_brightness(np.zeros((256, 256), dtype=np.uint8), settings)
    bright = assess_brightness(np.full((256, 256), 255, dtype=np.uint8), settings)
    assert dark.status == QualityStatus.FAIL
    assert bright.status == QualityStatus.FAIL
    assert dark.score is not None and bright.score is not None
    assert dark.score < bright.score


def test_low_contrast_page(settings: Settings) -> None:
    result = assess_contrast(np.full((256, 256), 128, dtype=np.uint8), settings)
    assert result.status == QualityStatus.FAIL
    assert result.score == 0


def test_resolution_dimensions_and_render_dpi(settings: Settings) -> None:
    adequate = DocumentPage(
        page_number=1,
        width=1200,
        height=1500,
        image_path="unused.png",
        metadata={"render_dpi": 150},
    )
    small = adequate.model_copy(update={"width": 50, "height": 50})
    good_result = assess_resolution(adequate, settings)
    small_result = assess_resolution(small, settings)
    assert good_result.status == QualityStatus.PASS
    assert good_result.metadata["total_pixels"] == 1_800_000
    assert good_result.metadata["render_dpi"] == 150
    assert small_result.status == QualityStatus.FAIL


def test_crop_warns_without_claiming_proof(settings: Settings) -> None:
    pixels = np.full((256, 256), 255, dtype=np.uint8)
    pixels[-8:, :] = 0
    result = assess_crop(pixels, settings)
    assert result.status == QualityStatus.WARNING
    assert result.value == "bottom"
    assert "may be cropped" in result.reason
    assert result.metadata["edge_density"]["bottom"] > result.threshold["warn_at_or_above"]


def test_orientation_does_not_invent_reading_direction() -> None:
    page = DocumentPage(page_number=1, width=1200, height=800, image_path="unused.png")
    result = assess_orientation(page)
    assert result.value == "UNKNOWN"
    assert result.metadata["geometry"] == "landscape"
    assert result.metadata["reading_orientation"] == "UNKNOWN"


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([QualityStatus.PASS, QualityStatus.PASS], QualityStatus.PASS),
        ([QualityStatus.PASS, QualityStatus.WARNING], QualityStatus.WARNING),
        ([QualityStatus.WARNING, QualityStatus.FAIL], QualityStatus.FAIL),
    ],
)
def test_deterministic_aggregation(statuses, expected) -> None:
    assert aggregate_status(statuses) == expected


def test_threshold_override_changes_result(settings: Settings) -> None:
    sharp = checkerboard()
    baseline = assess_blur(sharp, settings)
    overridden = settings.model_copy(update={"quality_blur_warn": 1_000_000_000.0})
    adjusted = assess_blur(sharp, overridden)
    assert baseline.status == QualityStatus.PASS
    assert adjusted.status == QualityStatus.WARNING


def test_document_aggregation_and_persistence(settings: Settings) -> None:
    document = create_document(settings, [checkerboard(), checkerboard()])
    second_image = settings.data_dir / document.pages[1].image_path
    second_image.unlink()

    result = QualityService(settings).assess_document(document)

    assert result.overall_status == QualityStatus.FAIL
    assert result.pages[1].overall_status == QualityStatus.FAIL
    assert result.pages[1].checks == []
    assert "Page 2" in (result.pages[1].error or "")
    assert result.pages[0].checks
    assert result.summary["FAIL"] >= 1
    persisted = QualityRepository(settings.database_path).get(document.document_id)
    assert persisted == result
    assert result.duration_ms >= 0


def test_missing_image_raises_on_single_page(settings: Settings) -> None:
    missing = DocumentPage(page_number=3, width=256, height=256, image_path="missing.png")
    with pytest.raises(PageImageUnavailableError, match="Page 3"):
        QualityService(settings).assess_page(missing, "missing-document")


def test_cli_human_and_json_output(settings: Settings, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "synthetic.png"
    Image.fromarray(checkerboard()).save(source)
    monkeypatch.setenv("BRUZ_DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("BRUZ_DATA_DIR", str(settings.data_dir))
    ingested = DocumentIngestionService(settings).ingest(source).document

    human = CliRunner().invoke(app, ["quality", ingested.document_id])
    machine = CliRunner().invoke(app, ["quality", ingested.document_id, "--json"])

    assert human.exit_code == 0, human.output
    assert "Bruz OCR Quality Assessment" in human.stdout
    assert "Overall:" in human.stdout
    assert "Page 1:" in human.stdout
    assert machine.exit_code == 0, machine.output
    payload = json.loads(machine.stdout)
    assert payload["document_id"] == ingested.document_id
    assert payload["pages"][0]["checks"]
    assert QualityRepository(settings.database_path).get(ingested.document_id) is not None
