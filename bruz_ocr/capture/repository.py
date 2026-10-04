"""SQLite persistence for document metadata; document bytes stay on disk."""

from contextlib import closing
from pathlib import Path

from bruz_ocr.capture.models import Document
from bruz_ocr.database import connect_database, initialize_database


class DocumentRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        initialize_database(database_path)

    def find_by_sha256(self, sha256: str) -> str | None:
        with closing(connect_database(self.database_path)) as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE sha256 = ? ORDER BY created_at LIMIT 1",
                (sha256,),
            ).fetchone()
        return str(row[0]) if row else None

    def save(self, document: Document) -> None:
        with closing(connect_database(self.database_path)) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO documents (id, original_filename, file_type, mime_type, "
                    "sha256, file_size_bytes, page_count, storage_path, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        document.document_id,
                        document.original_filename,
                        document.file_type,
                        document.mime_type,
                        document.sha256,
                        document.file_size_bytes,
                        document.page_count,
                        document.storage_path,
                        document.created_at.isoformat(),
                    ),
                )
                connection.executemany(
                    "INSERT INTO document_pages "
                    "(document_id, page_number, width, height, image_path) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (
                            document.document_id,
                            page.page_number,
                            page.width,
                            page.height,
                            page.image_path,
                        )
                        for page in document.pages
                    ],
                )
