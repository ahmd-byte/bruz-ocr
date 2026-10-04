"""Provider-independent normalized document records."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

DocumentType = Literal["PDF", "PNG", "JPG", "JPEG"]


class DocumentPage(BaseModel):
    page_number: int = Field(ge=1)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    image_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    document_id: str
    original_filename: str
    storage_path: str
    file_type: DocumentType
    mime_type: str
    sha256: str
    file_size_bytes: int = Field(gt=0)
    page_count: int = Field(gt=0)
    created_at: datetime
    pages: list[DocumentPage]
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionResult(BaseModel):
    document: Document
    duplicate_candidate: bool
    matching_document_id: str | None = None
