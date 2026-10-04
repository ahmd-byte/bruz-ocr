"""Validate and normalize local documents without invoking OCR."""

import hashlib
import logging
import math
import re
import shutil
import sqlite3
import tempfile
import time
import warnings
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import pypdfium2 as pdfium  # type: ignore[import-untyped]
from PIL import Image, ImageOps, UnidentifiedImageError

from bruz_ocr.capture.errors import (
    CorruptDocumentError,
    DocumentIngestionError,
    DocumentReadError,
    UnsupportedDocumentError,
)
from bruz_ocr.capture.models import Document, DocumentPage, DocumentType, IngestionResult
from bruz_ocr.capture.repository import DocumentRepository
from bruz_ocr.config import Settings

LOGGER = logging.getLogger(__name__)
MIME_TYPES = {
    "PDF": "application/pdf",
    "PNG": "image/png",
    "JPG": "image/jpeg",
    "JPEG": "image/jpeg",
}
SIGNATURES = {
    "PDF": b"%PDF-",
    "PNG": b"\x89PNG\r\n\x1a\n",
    "JPG": b"\xff\xd8\xff",
    "JPEG": b"\xff\xd8\xff",
}
PDF_DPI = 150


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" ._")
    return cleaned[:200] or "document"


class DocumentIngestionService:
    def __init__(self, settings: Settings, repository: DocumentRepository | None = None) -> None:
        self.settings = settings
        try:
            self.repository = repository or DocumentRepository(settings.database_path)
        except (OSError, sqlite3.Error, RuntimeError) as error:
            raise DocumentReadError("Could not initialize the local document database.") from error

    def ingest(self, input_path: Path) -> IngestionResult:
        document_id = uuid4().hex
        started = time.perf_counter()
        LOGGER.info("document_ingest_started", extra={"document_id": document_id})
        try:
            result = self._ingest(input_path, document_id)
        except DocumentIngestionError as error:
            LOGGER.error(
                "document_ingest_failed",
                extra={"document_id": document_id, "error_type": type(error).__name__},
            )
            raise
        LOGGER.info(
            "document_ingest_completed",
            extra={
                "document_id": document_id,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        return result

    def _ingest(self, input_path: Path, document_id: str) -> IngestionResult:
        source, file_type = self._validate_source(input_path)
        data_dir = self.settings.data_dir.expanduser().resolve()
        temp_root = data_dir / "temp"
        documents_root = data_dir / "documents"
        try:
            temp_root.mkdir(parents=True, exist_ok=True)
            documents_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=f"{document_id}-", dir=temp_root) as temp_name:
                stage = Path(temp_name)
                original_name = f"original.{file_type.lower()}"
                staged_original = stage / original_name
                sha256, file_size = self._copy_and_hash(source, staged_original, file_type)
                LOGGER.info("document_hash_calculated", extra={"document_id": document_id})
                pages = self._render_pages(staged_original, stage, file_type, document_id)
                duplicate_id = self.repository.find_by_sha256(sha256)
                if duplicate_id:
                    LOGGER.info("duplicate_detected", extra={"document_id": document_id})
                relative_root = Path("documents") / document_id
                document = Document(
                    document_id=document_id,
                    original_filename=_safe_filename(source.name),
                    storage_path=(relative_root / original_name).as_posix(),
                    file_type=file_type,
                    mime_type=MIME_TYPES[file_type],
                    sha256=sha256,
                    file_size_bytes=file_size,
                    page_count=len(pages),
                    created_at=datetime.now(UTC),
                    pages=[
                        page.model_copy(
                            update={
                                "image_path": (
                                    relative_root / "pages" / f"page-{page.page_number:04d}.png"
                                ).as_posix()
                            }
                        )
                        for page in pages
                    ],
                )
                final_dir = documents_root / document_id
                stage.rename(final_dir)
                try:
                    self.repository.save(document)
                except (sqlite3.Error, OSError):
                    shutil.rmtree(final_dir)
                    raise
                LOGGER.info("document_saved", extra={"document_id": document_id})
                return IngestionResult(
                    document=document,
                    duplicate_candidate=duplicate_id is not None,
                    matching_document_id=duplicate_id,
                )
        except (OSError, sqlite3.Error) as error:
            raise DocumentReadError(
                "Could not store the document locally; check data and database access."
            ) from error

    def _validate_source(self, input_path: Path) -> tuple[Path, DocumentType]:
        try:
            source = input_path.expanduser().resolve(strict=True)
            if not source.is_file():
                raise DocumentReadError("Input path is not a regular file.")
            size = source.stat().st_size
        except (OSError, ValueError) as error:
            raise DocumentReadError(
                "Input file cannot be read; check the path and permissions."
            ) from error
        file_type = source.suffix.lstrip(".").upper()
        if file_type not in MIME_TYPES:
            raise UnsupportedDocumentError("Supported formats are PDF, PNG, JPG, and JPEG.")
        if size == 0:
            raise CorruptDocumentError("Input file is empty.")
        if size > self.settings.max_document_bytes:
            raise DocumentReadError(
                f"Input exceeds BRUZ_MAX_DOCUMENT_BYTES ({self.settings.max_document_bytes} bytes)."
            )
        return source, cast(DocumentType, file_type)

    def _copy_and_hash(
        self, source: Path, destination: Path, file_type: DocumentType
    ) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with source.open("rb") as input_file, destination.open("wb") as output_file:
            signature = input_file.read(8)
            if not signature.startswith(SIGNATURES[file_type]):
                raise CorruptDocumentError("File contents do not match the declared format.")
            input_file.seek(0)
            while chunk := input_file.read(1024 * 1024):
                size += len(chunk)
                if size > self.settings.max_document_bytes:
                    raise DocumentReadError(
                        "Input grew beyond BRUZ_MAX_DOCUMENT_BYTES during ingestion."
                    )
                digest.update(chunk)
                output_file.write(chunk)
        return digest.hexdigest(), size

    def _render_pages(
        self, source: Path, stage: Path, file_type: DocumentType, document_id: str
    ) -> list[DocumentPage]:
        pages_dir = stage / "pages"
        pages_dir.mkdir()
        if file_type == "PDF":
            return self._render_pdf(source, pages_dir, document_id)
        return [self._render_image(source, pages_dir, file_type, document_id)]

    def _render_pdf(self, source: Path, pages_dir: Path, document_id: str) -> list[DocumentPage]:
        LOGGER.info("pdf_render_started", extra={"document_id": document_id})
        try:
            with pdfium.PdfDocument(source.read_bytes()) as pdf:
                if len(pdf) == 0:
                    raise CorruptDocumentError("PDF has no pages.")
                if len(pdf) > self.settings.max_pages:
                    raise DocumentReadError(
                        f"PDF exceeds BRUZ_MAX_PAGES ({self.settings.max_pages})."
                    )
                pages: list[DocumentPage] = []
                for page_index in range(len(pdf)):
                    page_number = page_index + 1
                    with closing(pdf[page_index]) as page:
                        width, height = page.get_size()
                        predicted_pixels = math.ceil(width * PDF_DPI / 72) * math.ceil(
                            height * PDF_DPI / 72
                        )
                        if (
                            predicted_pixels <= 0
                            or predicted_pixels > self.settings.max_page_pixels
                        ):
                            raise DocumentReadError(
                                "PDF page dimensions exceed the configured pixel limit."
                            )
                        with closing(page.render(scale=PDF_DPI / 72)) as bitmap:
                            image = bitmap.to_pil()
                            image_path = pages_dir / f"page-{page_number:04d}.png"
                            image.save(image_path, format="PNG")
                            pages.append(
                                DocumentPage(
                                    page_number=page_number,
                                    width=image.width,
                                    height=image.height,
                                    image_path=image_path.name,
                                )
                            )
                    LOGGER.info(
                        "page_rendered",
                        extra={"document_id": document_id, "page_number": page_number},
                    )
                return pages
        except pdfium.PdfiumError as error:
            if error.err_code == pdfium.raw.FPDF_ERR_PASSWORD:
                raise DocumentReadError("Password-protected PDFs are not supported yet.") from error
            raise CorruptDocumentError("PDF cannot be decoded or rendered.") from error

    def _render_image(
        self, source: Path, pages_dir: Path, file_type: DocumentType, document_id: str
    ) -> DocumentPage:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(source) as image:
                    expected_format = "JPEG" if file_type in ("JPG", "JPEG") else "PNG"
                    if image.format != expected_format:
                        raise CorruptDocumentError(
                            "Image contents do not match the declared format."
                        )
                    if image.width * image.height > self.settings.max_page_pixels:
                        raise DocumentReadError(
                            "Image dimensions exceed the configured pixel limit."
                        )
                    image.load()
                    normalized = ImageOps.exif_transpose(image)
                    image_path = pages_dir / "page-0001.png"
                    normalized.save(image_path, format="PNG")
                    width, height = normalized.size
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ) as error:
            raise CorruptDocumentError("Image cannot be decoded.") from error
        LOGGER.info("page_rendered", extra={"document_id": document_id, "page_number": 1})
        return DocumentPage(page_number=1, width=width, height=height, image_path=image_path.name)
