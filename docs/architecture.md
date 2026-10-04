# Architecture

Feature 1 establishes one installable Python package. `bruz_ocr.cli` is the operator entry point; `bruz_ocr.api` exposes a local health route. Both use `Settings` and `database` modules. SQLite is initialized when the API starts or `doctor` runs. No document processing is implemented.

Future OCR engines will be adapters behind a provider interface. Pipeline stages will exchange provider-independent data models so validation and review never import an OCR library. SQLite persistence will be kept behind repositories when processing data is added. This boundary is not introduced before there is data to persist.

The server binds to loopback by default. `BRUZ_HOST` permits an explicit LAN binding in a trusted environment; authentication and deployment security must be designed before broader access.
