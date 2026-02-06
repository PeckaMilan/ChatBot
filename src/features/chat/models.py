"""Pydantic models for chat feature."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None
    document_ids: list[str] | None = None
    system_prompt: str | None = None  # Override widget's system prompt
    model_id: str | None = None  # Override widget's model


class SourceReference(BaseModel):
    """Reference to source document chunk."""

    chunk_id: str
    text: str
    score: float
    page_number: int | None = None


class ChatResponse(BaseModel):
    """Chat response model."""

    message: str
    sources: list[SourceReference]
    session_id: str
    language: str


class ConversationMessage(BaseModel):
    """Conversation message model."""

    id: str
    role: str
    content: str
    created_at: str


class ConversationResponse(BaseModel):
    """Conversation with messages."""

    id: str
    session_id: str
    messages: list[ConversationMessage]
