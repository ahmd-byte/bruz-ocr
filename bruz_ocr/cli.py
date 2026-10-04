"""Local command line entry point."""

import shutil
import sqlite3
import sys
from pathlib import Path

import typer

from bruz_ocr import __version__
from bruz_ocr.capture.errors import DocumentIngestionError
from bruz_ocr.capture.service import DocumentIngestionService
from bruz_ocr.config import Settings
from bruz_ocr.database import initialize_database
from bruz_ocr.logging import configure_logging

app = typer.Typer(help="Bruz OCR: local document intelligence.", no_args_is_help=True)


@app.command()
def version() -> None:
    """Show the installed Bruz OCR version."""
    typer.echo(f"Bruz OCR {__version__}")


@app.command()
def doctor() -> None:
    """Check the local foundation installation."""
    settings = Settings()
    typer.echo("Bruz OCR")
    typer.echo(f"Version             {__version__}")
    typer.echo(f"Python              {sys.version_info.major}.{sys.version_info.minor}")
    try:
        initialize_database(settings.database_path)
    except (OSError, sqlite3.Error, RuntimeError) as error:
        typer.echo(f"Database            ERROR: {error}")
        raise typer.Exit(code=1) from error
    typer.echo(f"Database            READY ({settings.database_path.expanduser().resolve()})")
    typer.echo("OCR models          Not configured yet")
    typer.echo("GPU                 Not checked yet")
    database_directory = settings.database_path.expanduser().resolve().parent
    free_gib = shutil.disk_usage(database_directory).free / (1024**3)
    typer.echo(f"Disk free           {free_gib:.1f} GiB")
    typer.echo("Local mode          Enabled")
    typer.echo("External API usage  NONE")
    typer.echo("Telemetry           Disabled")


@app.command()
def ingest(path: Path) -> None:
    """Ingest a local PDF, PNG, JPG, or JPEG."""
    settings = Settings()
    configure_logging(settings.debug)
    try:
        result = DocumentIngestionService(settings).ingest(path)
    except DocumentIngestionError as error:
        typer.echo(f"Ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    document = result.document
    typer.echo("Bruz OCR")
    typer.echo("Document ingested successfully")
    typer.echo(f"ID: {document.document_id}")
    typer.echo(f"File: {document.original_filename}")
    typer.echo(f"Type: {document.file_type}")
    typer.echo(f"Pages: {document.page_count}")
    typer.echo(f"Size: {document.file_size_bytes} bytes")
    typer.echo(f"SHA-256: {document.sha256}")
    typer.echo(f"Duplicate candidate: {'Yes' if result.duplicate_candidate else 'No'}")


@app.command()
def serve() -> None:
    """Start the local HTTP API."""
    import uvicorn

    settings = Settings()
    configure_logging(settings.debug)
    uvicorn.run("bruz_ocr.api:app", host=settings.host, port=settings.port, reload=False)
