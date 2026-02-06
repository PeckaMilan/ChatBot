"""Chat API endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.firestore import get_firestore_client
from src.core.gemini import get_gemini_client
from src.features.billing.service import get_usage_service, UsageLimitExceededError

from .models import ChatRequest, ChatResponse
from .service import get_chat_service
from .retrieval import get_retrieval_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a message."""
    message_id: str | None = None
    session_id: str
    feedback: str  # "positive" or "negative"
    comment: str | None = None


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


STATEOS_SYSTEM_PROMPT = """Jsi StateOS Asistent - AI pomocník pro informace o české vládě, politice a státní správě.

PRAVIDLA:
1. Odpovídej POUZE na otázky týkající se:
   - České vlády, ministerstev a státních institucí
   - Politiky, politických stran a politiků v ČR
   - Státního rozpočtu, daní a veřejných financí
   - Zákonů, legislativy a právního systému ČR
   - Voleb a volebního systému
   - EU a mezinárodních vztahů ČR
   - StateOS platformy a jejích funkcí

2. Na JAKÉKOLIV jiné otázky (sport, zábava, vtipy, osobní dotazy, programování, atd.) odpověz:
   "Omlouvám se, ale jako StateOS Asistent mohu odpovídat pouze na otázky týkající se vlády, politiky a státní správy v České republice. Zkuste se zeptat na něco z této oblasti."

3. Vždy odpovídej v češtině, pokud uživatel nepíše v jiném jazyce.

4. Buď stručný, věcný a objektivní. Neprezentuj politické názory.

5. Pokud nemáš jistotu, přiznej to a doporuč oficiální zdroje (gov.cz, psp.cz, atd.)."""


@router.post("/widget/{widget_id}", response_model=ChatResponse)
async def widget_chat(widget_id: str, request: ChatRequest):
    """
    Widget-specific chat endpoint.

    Uses widget configuration for system prompt and document selection.
    Tracks usage per customer for billing.
    """
    firestore = get_firestore_client()
    usage_service = get_usage_service()

    # Handle legacy "default" widget
    if widget_id == "default":
        try:
            service = get_chat_service()
            response = await service.chat(
                message=request.message,
                session_id=request.session_id,
                document_ids=request.document_ids,
                system_prompt=STATEOS_SYSTEM_PROMPT,
                widget_id=widget_id,
            )
            return response
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

    # Load widget configuration
    widget = await firestore.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    if not widget.get("is_active", True):
        raise HTTPException(status_code=403, detail="Widget is disabled")

    customer_id = widget.get("customer_id")

    # Check usage limits
    if customer_id:
        is_allowed, reason = await usage_service.check_usage_limit(customer_id, "message")
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=reason,
            )

    # Get system prompt and model from widget config
    system_prompt = widget.get("system_prompt") or "You are a helpful assistant."
    model_id = widget.get("model") or "gemini-2.0-flash-001"

    try:
        service = get_chat_service()
        response = await service.chat(
            message=request.message,
            session_id=request.session_id,
            document_ids=request.document_ids or widget.get("document_ids", []),
            system_prompt=system_prompt,
            widget_id=widget_id,
            customer_id=customer_id,
            model_id=model_id,
        )
        return response
    except UsageLimitExceededError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/widget/{widget_id}/stream")
async def widget_chat_stream(widget_id: str, request: ChatRequest):
    """
    Streaming chat endpoint for widgets.

    Returns Server-Sent Events (SSE) with chunks of the response.
    """
    import json

    firestore = get_firestore_client()
    usage_service = get_usage_service()

    # Load widget configuration
    widget = await firestore.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    if not widget.get("is_active", True):
        raise HTTPException(status_code=403, detail="Widget is disabled")

    customer_id = widget.get("customer_id")

    # Check usage limits
    if customer_id:
        is_allowed, reason = await usage_service.check_usage_limit(customer_id, "message")
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=reason,
            )

    # Get config
    system_prompt = widget.get("system_prompt") or "You are a helpful assistant."
    model_id = widget.get("model") or "gemini-2.0-flash-001"
    document_ids = request.document_ids or widget.get("document_ids", [])

    # Get retrieval service for RAG
    retrieval = get_retrieval_service()
    chunks = await retrieval.search(query=request.message, document_ids=document_ids, top_k=5)
    context = retrieval.build_context(chunks)

    async def generate():
        gemini = get_gemini_client()
        full_response = ""

        try:
            async for chunk in gemini.chat_stream(
                message=request.message,
                system_prompt=system_prompt,
                context=context if context else None,
                model_id=model_id,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Send done signal with sources
            sources = [
                {
                    "chunk_id": c["id"],
                    "text": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
                    "score": c["score"],
                }
                for c in chunks[:3]
            ]
            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

            # Record usage (fire and forget)
            if customer_id:
                try:
                    input_tokens = len(request.message) // 4 + len(context or "") // 4
                    output_tokens = len(full_response) // 4
                    await usage_service.record_chat_usage(
                        customer_id=customer_id,
                        widget_id=widget_id,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    )
                except Exception:
                    pass

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/widget/{widget_id}/feedback")
async def submit_feedback(widget_id: str, request: FeedbackRequest):
    """
    Submit feedback (thumbs up/down) for a chat response.
    """
    from datetime import datetime

    firestore = get_firestore_client()

    # Verify widget exists
    widget = await firestore.get_widget(widget_id)
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    # Store feedback
    feedback_data = {
        "widget_id": widget_id,
        "customer_id": widget.get("customer_id"),
        "session_id": request.session_id,
        "message_id": request.message_id,
        "feedback": request.feedback,  # "positive" or "negative"
        "comment": request.comment,
        "created_at": datetime.utcnow(),
    }

    ref = firestore.db.collection("feedback").document()
    feedback_data["id"] = ref.id
    ref.set(feedback_data)

    return {"status": "ok", "id": ref.id}
