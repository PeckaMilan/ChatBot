"""Chat API endpoints."""

import json

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.core.firestore import get_firestore_client
from src.core.gemini import get_gemini_client
from src.core.rate_limiter import limiter
from src.features.billing.service import get_usage_service, UsageLimitExceededError

from .models import ChatRequest, ChatResponse
from .sanitizer import detect_pii, redact_pii
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
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest):
    """
    Send a message and get a response.

    Uses RAG to retrieve relevant context from uploaded documents.
    Maintains conversation history via session_id.
    """
    try:
        service = get_chat_service()
        response = await service.chat(
            message=body.message,
            session_id=body.session_id,
            document_ids=body.document_ids,
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
@limiter.limit("30/minute")
async def widget_chat(request: Request, widget_id: str, body: ChatRequest):
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
                message=body.message,
                session_id=body.session_id,
                document_ids=body.document_ids,
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

    # Get system prompt and model - request overrides widget config (playground)
    system_prompt = body.system_prompt or widget.get("system_prompt") or "You are a helpful assistant."
    model_id = body.model_id or widget.get("model") or "gemini-3-flash-preview"

    print(f"[CHAT] Widget={widget_id} Model={model_id} SystemPrompt={system_prompt[:80]}...")

    try:
        service = get_chat_service()
        response = await service.chat(
            message=body.message,
            session_id=body.session_id,
            document_ids=body.document_ids or widget.get("document_ids", []),
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
@limiter.limit("30/minute")
async def widget_chat_stream(request: Request, widget_id: str, body: ChatRequest):
    """
    Streaming chat endpoint for widgets.

    Returns Server-Sent Events (SSE) with chunks of the response.
    Includes source citations and PII redaction.
    """
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

    # Get config - request overrides widget config (playground)
    system_prompt = body.system_prompt or widget.get("system_prompt") or "You are a helpful assistant."
    model_id = body.model_id or widget.get("model") or "gemini-3-flash-preview"
    document_ids = body.document_ids or widget.get("document_ids", [])

    print(f"[STREAM] Widget={widget_id} Model={model_id} SystemPrompt={system_prompt[:80]}...")

    # PII detection and redaction
    pii_matches = detect_pii(body.message)
    sanitized_message = redact_pii(body.message) if pii_matches else body.message

    # Get retrieval service for RAG
    retrieval = get_retrieval_service()
    chunks = await retrieval.search(query=body.message, document_ids=document_ids, top_k=5)
    context = retrieval.build_context(chunks)

    # Look up document filenames for top sources
    top_chunks = chunks[:3]
    doc_ids = list({c["document_id"] for c in top_chunks if c.get("document_id")})
    doc_filenames: dict[str, str] = {}
    for doc_id in doc_ids:
        doc = await firestore.get_document(doc_id)
        if doc:
            doc_filenames[doc_id] = doc.get("filename", "Document")

    async def generate():
        gemini = get_gemini_client()
        full_response = ""

        try:
            async for chunk in gemini.chat_stream(
                message=sanitized_message,
                system_prompt=system_prompt,
                context=context if context else None,
                model_id=model_id,
            ):
                full_response += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Build enriched sources with filenames
            sources = [
                {
                    "chunk_id": c["id"],
                    "document_id": c.get("document_id"),
                    "filename": doc_filenames.get(c.get("document_id", ""), "Document"),
                    "text": c["text"][:200] + "..." if len(c["text"]) > 200 else c["text"],
                    "score": c["score"],
                    "page_number": c.get("page_number"),
                }
                for c in top_chunks
            ]

            # Send done signal with sources and PII warning
            done_data = {
                "done": True,
                "sources": sources,
            }
            if pii_matches:
                done_data["pii_warning"] = True

            yield f"data: {json.dumps(done_data)}\n\n"

            # Record usage (fire and forget)
            if customer_id:
                try:
                    input_tokens = len(body.message) // 4 + len(context or "") // 4
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


@router.get("/widget/{widget_id}/config")
@limiter.limit("60/minute")
async def get_widget_config(request: Request, widget_id: str):
    """
    Public endpoint to get widget display config.
    No auth required - returns only non-sensitive display settings.
    """
    firestore = get_firestore_client()
    widget = await firestore.get_widget(widget_id)

    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")

    if not widget.get("is_active", True):
        raise HTTPException(status_code=403, detail="Widget is disabled")

    return {
        "chatbot_name": widget.get("chatbot_name", "Chat"),
        "welcome_message": widget.get("welcome_message", "Hello! How can I help you?"),
        "widget_color": widget.get("widget_color", "#007bff"),
        "is_active": True,
    }


@router.post("/widget/{widget_id}/feedback")
@limiter.limit("10/minute")
async def submit_feedback(request: Request, widget_id: str, body: FeedbackRequest):
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
        "session_id": body.session_id,
        "message_id": body.message_id,
        "feedback": body.feedback,  # "positive" or "negative"
        "comment": body.comment,
        "created_at": datetime.utcnow(),
    }

    ref = firestore.db.collection("feedback").document()
    feedback_data["id"] = ref.id
    ref.set(feedback_data)

    return {"status": "ok", "id": ref.id}
