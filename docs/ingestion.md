# Local document ingestion

`bruz-ocr ingest <path>` accepts PDF, PNG, JPG, and JPEG. The service resolves a local file, checks its size and signature, copies it into temporary staging while calculating SHA-256, then uses pypdfium2 or Pillow to decode it. PDFs are rendered at 150 DPI in page order. Images become a single PNG page representation; the original bytes remain untouched.

On success, the staging directory moves to `BRUZ_DATA_DIR/documents/<generated-id>/`, and the repository writes document and page metadata to SQLite. Stored paths are relative to the data directory. The service returns a normalized `Document` plus a duplicate-candidate flag and a matching ID if the hash already exists. It does not skip or merge duplicates.

Input bytes and renderer failures are reported as typed ingestion errors. The size, page-count, and page-pixel limits reduce accidental resource exhaustion. Logs carry an internal document ID and event names without source paths or document text. A crash between moving staged files and writing SQLite metadata can leave an orphan directory; a later maintenance feature should reconcile these.
