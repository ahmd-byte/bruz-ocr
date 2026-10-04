"""Actionable ingestion errors for CLI and future API callers."""


class DocumentIngestionError(Exception):
    """Base class for input and storage failures."""


class UnsupportedDocumentError(DocumentIngestionError):
    """The extension or decoded media type is unsupported."""


class DocumentReadError(DocumentIngestionError):
    """The source or local storage could not be read or written."""


class CorruptDocumentError(DocumentIngestionError):
    """The bytes could not be decoded as the declared format."""
