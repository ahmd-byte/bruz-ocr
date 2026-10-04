# Bruz OCR

## What Bruz OCR Is

Bruz OCR is a local document OCR and document intelligence application. It currently ingests and normalizes local documents for future OCR processing. It does not recognize text yet.

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
- [x] Local PDF, PNG, JPG, and JPEG ingestion
- [x] SHA-256 duplicate candidate detection and local metadata storage
- [ ] Document quality assessment
- [ ] OCR provider adapters, templates, validation, and review
- [ ] Excel export and local dashboard

## Architecture

The CLI and API share settings and SQLite setup. The ingestion service validates documents, stores originals and page images on local disk, and records metadata through a repository. Processing stages and OCR adapters will be added separately. See [architecture](docs/architecture.md).

## OCR Pipeline

Ingest is implemented: local input → signature and decoder validation → SHA-256 → original copy and page rendering → SQLite metadata → normalized `Document`. Planned stages: quality → preprocess → classify/template → OCR → extract → validate → confidence → review → export.

## Directory Structure

`bruz_ocr/` holds application code, including `capture/` for ingestion. `tests/` holds synthetic tests, and `docs/` holds architecture and development notes. Runtime documents are stored under `BRUZ_DATA_DIR`, outside the source tree by default.

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
bruz-ocr ingest ./path/to/your-document.pdf
bruz-ocr serve
```

Replace the ingestion path with a PDF or image on your machine. The API binds to `127.0.0.1:8787` by default. Open `http://127.0.0.1:8787/health` to check it. There is no web dashboard yet.

## CLI Commands

`bruz-ocr --help`, `bruz-ocr version`, `bruz-ocr doctor`, `bruz-ocr ingest <path>`, and `bruz-ocr serve` are available. Ingest accepts PDF, PNG, JPG, and JPEG files and prints the document ID, page count, SHA-256, and duplicate candidate status. A duplicate is still ingested as a separate record.

## Configuration

Settings use `BRUZ_` environment variables or a `.env` file in the working directory. Copy `.env.example` to `.env` to customize them. The default database is `~/.bruz-ocr/bruz.db`; `BRUZ_DATA_DIR` defaults to `~/.bruz-ocr/data`. `BRUZ_MAX_DOCUMENT_BYTES` defaults to 100 MiB, `BRUZ_MAX_PAGES` to 100, and `BRUZ_MAX_PAGE_PIXELS` to 50 million. The default API host is loopback; set a LAN binding only in a trusted network environment.

Originals and rendered page images live under `<BRUZ_DATA_DIR>/documents/<generated-id>/`. Temporary staging files live under `<BRUZ_DATA_DIR>/temp/` and are removed after ingestion. SQLite stores relative paths and metadata, not document bytes. Runtime data is ignored by Git when kept in the repository's `data/` directory; the default directory is outside the repository.

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

The `serve` and `ingest` commands emit JSON logs to stderr. `BRUZ_DEBUG=true` enables debug-level logs. Ingestion logs contain an internal document ID, event name, page number where relevant, and completion time. Logs do not intentionally contain document content. See [debugging](docs/debugging.md).

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

Ingestion does not run OCR, assess quality, provide a review UI, or export data. Password-protected PDFs are not supported. Duplicate hashes are flagged, not automatically rejected. The CLI is the ingestion entry point; an authenticated upload API is deferred until its access model is designed.

## Roadmap

Next: image quality assessment, preprocessing, and an interchangeable local OCR provider. Then templates, validation, confidence, review, and export. Advanced OCR and operations follow the basic workflow.
