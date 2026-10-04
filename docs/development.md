# Development

Install with `python -m pip install -e '.[dev]'`. Run `python -m ruff check .`, `python -m mypy`, and `python -m pytest` before committing. The CLI entry point is `bruz-ocr`.

Keep each feature in a separate commit with its tests and README update. Model-dependent tests should use the `model` pytest marker and remain out of the fast core suite. Customer documents and local databases must not enter Git.
