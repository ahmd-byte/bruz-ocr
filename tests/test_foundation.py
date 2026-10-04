import sqlite3

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from bruz_ocr.api import create_app
from bruz_ocr.cli import app
from bruz_ocr.config import Settings
from bruz_ocr.database import initialize_database


def test_database_bootstrap_is_idempotent(tmp_path):
    database_path = tmp_path / "nested" / "bruz.db"
    initialize_database(database_path)
    initialize_database(database_path)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_health_reports_local_database(tmp_path):
    settings = Settings(database_path=tmp_path / "bruz.db")
    with TestClient(create_app(settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mode"] == "local"


def test_cli_version_and_help():
    runner = CliRunner()
    assert runner.invoke(app, ["version"]).exit_code == 0
    help_result = runner.invoke(app, ["--help"])
    assert help_result.exit_code == 0
    assert "doctor" in help_result.stdout
