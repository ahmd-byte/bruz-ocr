"""Local SQLite connection and schema bootstrap."""

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 2


def connect_database(path: Path) -> sqlite3.Connection:
    """Open a local database, creating its parent directory if necessary."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def initialize_database(path: Path) -> None:
    """Create the foundation schema. Later features add explicit migrations."""
    with closing(connect_database(path)) as connection:
        with connection:
            current_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema {current_version} is newer than this application "
                    f"(schema {SCHEMA_VERSION})."
                )
            if current_version == 0:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS application_metadata "
                    "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                connection.execute("PRAGMA user_version=1")
                current_version = 1
            if current_version == 1:
                connection.execute(
                    "CREATE TABLE documents ("
                    "id TEXT PRIMARY KEY, original_filename TEXT NOT NULL, "
                    "file_type TEXT NOT NULL, mime_type TEXT NOT NULL, "
                    "sha256 TEXT NOT NULL, file_size_bytes INTEGER NOT NULL, "
                    "page_count INTEGER NOT NULL, storage_path TEXT NOT NULL, "
                    "created_at TEXT NOT NULL)"
                )
                connection.execute("CREATE INDEX documents_sha256_idx ON documents(sha256)")
                connection.execute(
                    "CREATE TABLE document_pages ("
                    "document_id TEXT NOT NULL REFERENCES documents(id), "
                    "page_number INTEGER NOT NULL, width INTEGER NOT NULL, "
                    "height INTEGER NOT NULL, image_path TEXT NOT NULL, "
                    "PRIMARY KEY (document_id, page_number))"
                )
                connection.execute("PRAGMA user_version=2")


def database_is_ready(path: Path) -> bool:
    if not path.expanduser().exists():
        return False
    try:
        with closing(sqlite3.connect(path)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            return bool(version == SCHEMA_VERSION)
    except sqlite3.Error:
        return False
