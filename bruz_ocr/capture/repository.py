"""SQLite persistence for document metadata; document bytes stay on disk."""

import json
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
                    "sha256, file_size_bytes, page_count, storage_path, created_at, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                        json.dumps(document.metadata),
                    ),
                )
                connection.executemany(
                    "INSERT INTO document_pages "
                    "(document_id, page_number, width, height, image_path, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (
                            document.document_id,
                            page.page_number,
                            page.width,
                            page.height,
                            page.image_path,
                            json.dumps(page.metadata),
                        )
                        for page in document.pages
                    ],
                )

    def get(self, document_id: str) -> Document | None:
        with closing(connect_database(self.database_path)) as connection:
            row = connection.execute(
                "SELECT id, original_filename, file_type, mime_type, sha256, "
                "file_size_bytes, page_count, storage_path, created_at, metadata_json "
                "FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            page_rows = connection.execute(
                "SELECT page_number, width, height, image_path, metadata_json "
                "FROM document_pages WHERE document_id = ? ORDER BY page_number",
                (document_id,),
            ).fetchall()
        return Document.model_validate(
            {
                "document_id": row[0],
                "original_filename": row[1],
                "file_type": row[2],
                "mime_type": row[3],
                "sha256": row[4],
                "file_size_bytes": row[5],
                "page_count": row[6],
                "storage_path": row[7],
                "created_at": row[8],
                "metadata": json.loads(row[9]),
                "pages": [
                    {
                        "page_number": page[0],
                        "width": page[1],
                        "height": page[2],
                        "image_path": page[3],
                        "metadata": json.loads(page[4]),
                    }
                    for page in page_rows
                ],
            }
        )
