"""Local SQLite connection and schema bootstrap."""

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 1


def connect_database(path: Path) -> sqlite3.Connection:
    """Open a local database, creating its parent directory if necessary."""
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
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
                connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def database_is_ready(path: Path) -> bool:
    if not path.expanduser().exists():
        return False
    try:
        with closing(sqlite3.connect(path)) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            return bool(version == SCHEMA_VERSION)
    except sqlite3.Error:
        return False
