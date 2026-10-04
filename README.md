# Bruz OCR

## What Bruz OCR Is

Bruz OCR is a local document OCR and document intelligence application. This repository currently contains **Feature 1: the application foundation**. It does not yet process documents.

## Why It Exists

The intended workflow turns scans and photos into reviewed, structured data for Excel. Uncertain values will require review instead of being silently accepted.

## Privacy / Local-Only Principle

Document processing must remain on the customer's machine or local network. The current foundation makes no external OCR, analytics, or telemetry calls. Installation may download Python packages; future model setup may download open-source model files. See [privacy architecture](docs/privacy.md).

## Current Features

- [x] Installable Python package and `bruz-ocr` CLI
- [x] Local API with `/health`
- [x] Environment and `.env` configuration
- [x] JSON application logging
- [x] Local SQLite schema bootstrap and doctor check
- [ ] Document ingestion and quality assessment
- [ ] OCR provider adapters, templates, validation, and review
- [ ] Excel export and local dashboard

## Architecture

The CLI and API share settings and SQLite setup. Processing stages and OCR adapters will be added as separate modules when implemented. See [architecture](docs/architecture.md).

## OCR Pipeline

Planned: ingest → quality → preprocess → classify/template → OCR → extract → validate → confidence → review → export. No pipeline stage is implemented yet.

## Directory Structure

`bruz_ocr/` holds application code, `tests/` holds tests, and `docs/` holds architecture and development notes.

## Installation

Use Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

For a runtime-only installation, use `python -m pip install .`.

## Running Bruz OCR

```powershell
bruz-ocr doctor
bruz-ocr serve
```

The API binds to `127.0.0.1:8787` by default. Open `http://127.0.0.1:8787/health` to check it. There is no web dashboard yet.

## CLI Commands

`bruz-ocr --help`, `bruz-ocr version`, `bruz-ocr doctor`, and `bruz-ocr serve` are available.

## Configuration

Settings use `BRUZ_` environment variables or a `.env` file in the working directory. Copy `.env.example` to `.env` to customize `BRUZ_DATABASE_PATH`, `BRUZ_HOST`, `BRUZ_PORT`, and `BRUZ_DEBUG`. The default database is `~/.bruz-ocr/bruz.db`. The default host is loopback; set a LAN binding only in a trusted network environment.

## OCR Engines

No OCR engine is installed or integrated yet. Model packages are not part of the foundation install.

## Quality Engine

Planned for Feature 3.

## Template Engine

Planned for Feature 6.

## Validation Engine

Planned for Feature 8.

## Human Review

Planned for Feature 10.

## Excel Export

Planned for Feature 11.

## Logs / Debugging

The `serve` command emits JSON logs to stderr. `BRUZ_DEBUG=true` enables debug-level logs. Logs do not intentionally contain document content. See [debugging](docs/debugging.md).

## Testing

```powershell
python -m ruff check .
python -m mypy
python -m pytest
```

Tests require the `dev` extra. They do not require OCR models.

## Hardware Requirements

Python 3.11+ and enough disk space for the local SQLite database. OCR hardware requirements will be documented after an engine is integrated.

## Development Guide

See [development guide](docs/development.md).

## Troubleshooting

Run `bruz-ocr doctor` to check database access and local configuration. If installation fails, confirm that the active Python is version 3.11 or newer. If the API cannot bind, check `BRUZ_HOST` and `BRUZ_PORT`.

## Current Limitations

The foundation does not ingest files, run OCR, provide a review UI, or export data. The database has only a schema marker and metadata table.

## Roadmap

Next: document ingestion, image quality, preprocessing, and an interchangeable local OCR provider. Then templates, validation, confidence, review, and export. Advanced OCR and operations follow the basic workflow.
