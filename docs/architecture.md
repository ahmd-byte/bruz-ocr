# Architecture

Feature 1 establishes one installable Python package. `bruz_ocr.cli` is the operator entry point; `bruz_ocr.api` exposes a local health route. Both use `Settings` and `database` modules. SQLite is initialized when the API starts or `doctor` runs.

Feature 2 adds `capture/`: a service validates and stages a local file, renders ordered page images, and returns provider-independent `Document` and `DocumentPage` models. The repository stores metadata in SQLite. Original bytes and page images remain on disk under generated IDs; database paths are relative to `BRUZ_DATA_DIR`. The ingestion boundary imports no OCR engine. Duplicate detection is a hash lookup, not automatic deduplication. See [ingestion](ingestion.md).

Feature 3 adds `quality/`: independent image checks consume stored `DocumentPage` images and return serializable page/document results. The quality repository stores the latest assessment per document as versioned JSON in SQLite. One unreadable page produces a failed page result while other pages are assessed. The CLI loads documents through the capture repository; neither capture nor quality imports OCR models. See [quality](quality.md).

Future OCR engines will be adapters behind a provider interface. Pipeline stages will exchange provider-independent data models so validation and review never import an OCR library. SQLite persistence now has a document repository; later domains should follow the same boundary.

The server binds to loopback by default. `BRUZ_HOST` permits an explicit LAN binding in a trusted environment; authentication and deployment security must be designed before broader access.
