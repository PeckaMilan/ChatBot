"""Chat API endpoints."""

from fastapi import APIRouter, HTTPException

from .models import ChatRequest, ChatResponse
from .service import get_chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get a response.

    Uses RAG to retrieve relevant context from uploaded documents.
    Maintains conversation history via session_id.
    """
    try:
        service = get_chat_service()
        response = await service.chat(
            message=request.message,
            session_id=request.session_id,
            document_ids=request.document_ids,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/widget/{widget_id}", response_model=ChatResponse)
async def widget_chat(widget_id: str, request: ChatRequest):
    """
    Widget-specific chat endpoint.

    Uses widget configuration for system prompt and document selection.
    """
    try:
        # For MVP, widget_id maps to default settings
        # In production, fetch widget config from database
        from src.core.firestore import get_firestore_client

        firestore = get_firestore_client()
        settings = await firestore.get_settings(widget_id)

        service = get_chat_service()
        response = await service.chat(
            message=request.message,
            session_id=request.session_id,
            document_ids=request.document_ids,
            system_prompt=settings.get("system_prompt"),
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")
