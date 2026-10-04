import hashlib
import sqlite3
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from bruz_ocr.capture.errors import (
    CorruptDocumentError,
    DocumentReadError,
    UnsupportedDocumentError,
)
from bruz_ocr.capture.repository import DocumentRepository
from bruz_ocr.capture.service import DocumentIngestionService
from bruz_ocr.cli import app
from bruz_ocr.config import Settings
from bruz_ocr.database import initialize_database


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "state.db", data_dir=tmp_path / "private-data")


def make_image(path: Path, image_format: str) -> None:
    Image.new("RGB", (36, 24), "red").save(path, format=image_format)


def make_pdf(path: Path) -> None:
    first = Image.new("RGB", (200, 100), "red")
    second = Image.new("RGB", (100, 200), "blue")
    first.save(path, format="PDF", save_all=True, append_images=[second], resolution=72.0)


@pytest.mark.parametrize(
    ("extension", "image_format"),
    [("png", "PNG"), ("jpg", "JPEG"), ("jpeg", "JPEG")],
)
def test_image_ingestion_preserves_original_and_creates_page(
    settings: Settings, tmp_path: Path, extension: str, image_format: str
) -> None:
    source = tmp_path / f"image with spaces.{extension}"
    make_image(source, image_format)
    original_bytes = source.read_bytes()

    result = DocumentIngestionService(settings).ingest(source)

    document = result.document
    assert document.page_count == 1
    assert document.pages[0].page_number == 1
    assert (document.pages[0].width, document.pages[0].height) == (36, 24)
    assert (settings.data_dir / document.storage_path).read_bytes() == original_bytes
    assert (settings.data_dir / document.pages[0].image_path).is_file()
    assert source.read_bytes() == original_bytes
    assert document.original_filename == source.name
    assert document.file_type == extension.upper()
    assert document.mime_type == ("image/png" if extension == "png" else "image/jpeg")


def test_multipage_pdf_rendering_preserves_order(settings: Settings, tmp_path: Path) -> None:
    source = tmp_path / "two pages.pdf"
    make_pdf(source)

    result = DocumentIngestionService(settings).ingest(source)

    pages = result.document.pages
    assert result.document.page_count == 2
    assert [page.page_number for page in pages] == [1, 2]
    assert pages[0].width > pages[0].height
    assert pages[1].height > pages[1].width
    assert [Path(page.image_path).name for page in pages] == ["page-0001.png", "page-0002.png"]
    assert all((settings.data_dir / page.image_path).is_file() for page in pages)
    assert (settings.data_dir / result.document.storage_path).read_bytes() == source.read_bytes()


def test_rejects_unsupported_type(settings: Settings, tmp_path: Path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("not a document")
    with pytest.raises(UnsupportedDocumentError, match="Supported formats"):
        DocumentIngestionService(settings).ingest(source)


def test_rejects_mislabeled_image(settings: Settings, tmp_path: Path) -> None:
    source = tmp_path / "renamed.png"
    make_image(source, "JPEG")
    with pytest.raises(CorruptDocumentError, match="declared format"):
        DocumentIngestionService(settings).ingest(source)


def test_enforces_configured_size_limit(settings: Settings, tmp_path: Path) -> None:
    source = tmp_path / "too-large.png"
    make_image(source, "PNG")
    limited = settings.model_copy(update={"max_document_bytes": 10})
    with pytest.raises(DocumentReadError, match="BRUZ_MAX_DOCUMENT_BYTES"):
        DocumentIngestionService(limited).ingest(source)


@pytest.mark.parametrize("extension", ["png", "pdf"])
def test_rejects_corrupt_document(settings: Settings, tmp_path: Path, extension: str) -> None:
    source = tmp_path / f"broken.{extension}"
    if extension == "pdf":
        source.write_bytes(b"%PDF-broken-content")
    else:
        source.write_bytes(b"\x89PNG\r\n\x1a\nnot-an-image")
    with pytest.raises(CorruptDocumentError):
        DocumentIngestionService(settings).ingest(source)
    assert not list((settings.data_dir / "documents").iterdir())


def test_hash_and_duplicate_candidate(settings: Settings, tmp_path: Path) -> None:
    first_source = tmp_path / "first.png"
    second_source = tmp_path / "second.png"
    make_image(first_source, "PNG")
    second_source.write_bytes(first_source.read_bytes())
    service = DocumentIngestionService(settings)

    first = service.ingest(first_source)
    second = DocumentIngestionService(settings).ingest(second_source)

    expected_hash = hashlib.sha256(first_source.read_bytes()).hexdigest()
    assert first.document.sha256 == expected_hash
    assert not first.duplicate_candidate
    assert second.document.sha256 == expected_hash
    assert second.duplicate_candidate
    assert second.matching_document_id == first.document.document_id
    assert second.document.document_id != first.document.document_id
    assert (
        DocumentRepository(settings.database_path).find_by_sha256(expected_hash)
        == first.document.document_id
    )


def test_suspicious_filename_is_sanitized_and_cannot_choose_storage_path(
    settings: Settings, tmp_path: Path
) -> None:
    source = tmp_path / "odd;[name] _.png"
    make_image(source, "PNG")

    document = DocumentIngestionService(settings).ingest(source).document

    assert document.original_filename == "odd__name_ _.png"
    assert document.storage_path.startswith(f"documents/{document.document_id}/")
    assert "odd" not in document.storage_path
    assert (settings.data_dir / document.storage_path).is_file()


def test_configured_data_directory_and_cli(settings: Settings, tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "cli test.png"
    make_image(source, "PNG")
    monkeypatch.setenv("BRUZ_DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("BRUZ_DATA_DIR", str(settings.data_dir))

    result = CliRunner().invoke(app, ["ingest", str(source)])

    assert result.exit_code == 0, result.output
    assert "Document ingested successfully" in result.output
    assert "Duplicate candidate: No" in result.output
    assert len(list((settings.data_dir / "documents").iterdir())) == 1


def test_cli_reports_corrupt_pdf_without_traceback(
    settings: Settings, tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "bad.pdf"
    source.write_bytes(b"%PDF-invalid")
    monkeypatch.setenv("BRUZ_DATABASE_PATH", str(settings.database_path))
    monkeypatch.setenv("BRUZ_DATA_DIR", str(settings.data_dir))

    result = CliRunner().invoke(app, ["ingest", str(source)])

    assert result.exit_code == 1
    assert "Ingestion failed: PDF cannot be decoded" in result.output
    assert "Traceback" not in result.output


def test_existing_foundation_database_is_migrated(settings: Settings) -> None:
    with sqlite3.connect(settings.database_path) as connection:
        connection.execute(
            "CREATE TABLE application_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO application_metadata VALUES ('installation', 'existing')")
        connection.execute("PRAGMA user_version=1")

    initialize_database(settings.database_path)

    with sqlite3.connect(settings.database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert (
            connection.execute("SELECT value FROM application_metadata").fetchone()[0] == "existing"
        )
