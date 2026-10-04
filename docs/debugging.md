# Debugging

Run `bruz-ocr doctor` first. It checks Python, SQLite initialization, local disk space, and prints the configured database path. `BRUZ_DEBUG=true bruz-ocr serve` enables debug-level JSON logs. The current health route reports `ok` when the schema is available and `degraded` otherwise.

Do not add document contents to routine logs. Future pipeline jobs will use job IDs and stage durations to trace failures without revealing private data.
