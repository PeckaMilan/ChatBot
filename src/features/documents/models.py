"""Pydantic models for documents feature."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    """Base document model."""

    filename: str
    content_type: str


class DocumentCreate(DocumentBase):
    """Document creation model."""

    pass


class DocumentResponse(DocumentBase):
    """Document response model."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    storage_path: str
    status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """List of documents response."""

    documents: list[DocumentResponse]
    total: int


class DocumentUploadResponse(BaseModel):
    """Document upload response."""

    id: str
    filename: str
    status: str
    message: str


class ChunkResponse(BaseModel):
    """Document chunk response."""

    id: str
    text: str
    chunk_index: int
    page_number: int | None = None
    score: float | None = None
