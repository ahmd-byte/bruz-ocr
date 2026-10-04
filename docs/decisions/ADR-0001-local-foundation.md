# ADR-0001: Small local Python foundation

## Context

Bruz OCR requires an offline processing application with a CLI, local API, configuration, and persistent state. The repository was empty.

## Decision

Use a single installable Python package with Typer and FastAPI entry points, Pydantic settings, and SQLite. Keep OCR engines outside the foundation dependencies. Initialize the schema explicitly from the API lifespan or CLI doctor command.

## Reason

One process and one local database are sufficient for the first milestone and make installation, testing, and debugging straightforward. Optional model setup prevents a large implicit download.

## Alternatives

A distributed service and PostgreSQL were deferred because the basic processing pipeline does not exist yet. A frontend was deferred until there is processing data to show.

## Consequences

The foundation can be installed and checked without OCR models. Later features must add database migrations and provider-independent processing contracts before storing document results.
