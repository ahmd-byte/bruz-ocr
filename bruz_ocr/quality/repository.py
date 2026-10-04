"""Latest quality assessment per document in local SQLite."""

from contextlib import closing
from pathlib import Path

from bruz_ocr.database import connect_database, initialize_database
from bruz_ocr.quality.models import DocumentQualityResult


class QualityRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        initialize_database(database_path)

    def save(self, result: DocumentQualityResult) -> None:
        with closing(connect_database(self.database_path)) as connection:
            with connection:
                connection.execute(
                    "INSERT INTO quality_assessments "
                    "(document_id, result_json, assessed_at, algorithm_version) "
                    "VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(document_id) DO UPDATE SET "
                    "result_json=excluded.result_json, assessed_at=excluded.assessed_at, "
                    "algorithm_version=excluded.algorithm_version",
                    (
                        result.document_id,
                        result.model_dump_json(),
                        result.assessed_at.isoformat(),
                        result.algorithm_version,
                    ),
                )

    def get(self, document_id: str) -> DocumentQualityResult | None:
        with closing(connect_database(self.database_path)) as connection:
            row = connection.execute(
                "SELECT result_json FROM quality_assessments WHERE document_id = ?", (document_id,)
            ).fetchone()
        return DocumentQualityResult.model_validate_json(row[0]) if row else None
