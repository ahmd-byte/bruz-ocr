# Debugging

Run `bruz-ocr doctor` first. It checks Python, SQLite initialization, local disk space, and prints the configured database path. Set `BRUZ_DEBUG=true` in `.env` to enable debug-level JSON logs. The current health route reports `ok` when the schema is available and `degraded` otherwise.

The `ingest` command logs start, hash calculation, PDF rendering, each rendered page, duplicate detection, save, completion, and failure events with a generated document ID. Completion includes duration. It does not log document contents or source paths. Use the ID to locate stored files under `BRUZ_DATA_DIR/documents/` and metadata in SQLite. Future pipeline stages will use the same ID for timing and failures.
