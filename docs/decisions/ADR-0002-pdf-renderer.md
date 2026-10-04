# ADR-0002: Use PDFium for local PDF rendering

## Context

Feature 2 needs a local PDF renderer. Bruz OCR is intended for customer machines and may be distributed as proprietary software. PyMuPDF is technically suitable, but its open-source license is AGPL with a separate commercial route. See [PyMuPDF licensing](https://pymupdf.io/licensing).

## Decision

Use pypdfium2 for PDF loading and rasterization. Its project documents Apache-2.0/BSD-3-Clause terms for the Python package, with PDFium and bundled third-party license notices that must accompany binary distribution. See [pypdfium2 licensing](https://github.com/pypdfium2-team/pypdfium2#licensing).

## Reason

PDFium satisfies the local rendering requirement while keeping the initial distribution path simpler. The ingestion service owns the renderer call; document models do not depend on it.

## Alternatives

PyMuPDF would require AGPL compliance or a commercial license for applicable customer distributions. Calling a system-installed command-line renderer would add platform-specific setup.

## Consequences

Before shipping an installer, include the applicable pypdfium2, PDFium, and bundled third-party notices. The PDF renderer remains replaceable within `capture/` if product licensing or rendering needs change.
