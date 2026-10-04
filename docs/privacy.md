# Local processing and privacy

The current application has no code path for external OCR, telemetry, analytics, or document upload. The API binds to `127.0.0.1` by default. Runtime data is stored in SQLite at the configured local path. `.env`, databases, model files, exports, debug artifacts, and customer data directories are ignored by Git.

Installing dependencies can contact package registries. Future optional model installation can download model weights; document processing must remain local. Before adding a provider, audit its defaults for remote requests and disable them. A LAN deployment requires separate access controls and network protections.
