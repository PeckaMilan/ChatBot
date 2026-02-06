"""Customer portal API endpoints."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl

from src.config import get_settings
from src.core.firestore import FirestoreClient, get_firestore_client
from src.features.auth.dependencies import (
    AuthenticatedCustomer,
    get_current_customer,
)
from src.features.auth.jwt import generate_api_key, generate_widget_jwt_secret
from src.features.billing.service import UsageService, get_usage_service
from src.features.customers.models import (
    APIKeyCreate,
    APIKeyResponse,
    GeminiModel,
    TIER_LIMITS,
    SubscriptionTier,
    WidgetCreate,
    WidgetUpdate,
    WidgetResponse,
)
from src.features.documents.service import get_document_service
from src.features.scraper.service import get_scraper_service
from src.features.scraper.models import ScrapeRequest, ScrapeType

from .embed import generate_embed_code
from .models import DashboardResponse, EmbedCodeResponse


# Supported content types for upload
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "text/plain": "txt",
    "text/markdown": "md",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class ScrapeURLRequest(BaseModel):
    """Request to scrape a URL."""
    url: HttpUrl
    scrape_type: ScrapeType = ScrapeType.SINGLE
    max_pages: int = 10

router = APIRouter(prefix="/api/portal", tags=["customer-portal"])


# Dashboard
@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Get dashboard overview for the customer."""
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    documents = await firestore.list_documents_for_customer(customer.customer_id)
    usage = await usage_service.get_current_usage(customer.customer_id)

    return DashboardResponse(
        customer_id=customer.customer_id,
        company_name=customer.customer.get("company_name", ""),
        subscription_tier=customer.subscription_tier,
        widgets_count=len(widgets),
        documents_count=len(documents),
        usage=usage,
    )


# Widget Management
@router.post("/widgets", response_model=WidgetResponse)
async def create_widget(
    data: WidgetCreate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Create a new widget (chatbot)."""
    # Check widget limit based on tier
    existing = await firestore.list_widgets_for_customer(customer.customer_id)
    tier = SubscriptionTier(customer.subscription_tier)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])

    if len(existing) >= limits["widgets_allowed"]:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Widget limit ({limits['widgets_allowed']}) reached for {tier.value} tier. Upgrade to create more widgets.",
        )

    # Generate JWT secret for identity verification
    jwt_secret = generate_widget_jwt_secret() if data.require_jwt else None

    widget_data = {
        **data.model_dump(),
        "jwt_secret": jwt_secret,
        "show_powered_by": True,  # Free tier always shows branding
        "document_ids": [],
        "is_active": True,
    }

    widget = await firestore.create_widget(customer.customer_id, widget_data)

    # Ensure all required fields have values
    return WidgetResponse(
        id=widget["id"],
        customer_id=widget["customer_id"],
        name=widget["name"],
        chatbot_name=widget.get("chatbot_name", "Assistant"),
        welcome_message=widget.get("welcome_message", "Hello!"),
        widget_color=widget.get("widget_color", "#007bff"),
        show_powered_by=widget.get("show_powered_by", True),
        allowed_domains=widget.get("allowed_domains", []),
        document_ids=widget.get("document_ids", []),
        require_jwt=widget.get("require_jwt", False),
        is_active=widget.get("is_active", True),
        created_at=widget["created_at"],
        updated_at=widget["updated_at"],
    )


@router.get("/widgets", response_model=list[WidgetResponse])
async def list_widgets(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List all widgets for the customer."""
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    return [WidgetResponse(**w) for w in widgets]


@router.get("/widgets/{widget_id}", response_model=WidgetResponse)
async def get_widget(
    widget_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get a specific widget."""
    widget = await firestore.get_widget(widget_id)

    if not widget or widget.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Widget not found")

    return WidgetResponse(**widget)


@router.patch("/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    widget_id: str,
    data: WidgetUpdate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Update a widget."""
    widget = await firestore.get_widget(widget_id)

    if not widget or widget.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Widget not found")

    update_data = data.model_dump(exclude_unset=True)

    # Generate JWT secret if enabling require_jwt
    if data.require_jwt and not widget.get("jwt_secret"):
        update_data["jwt_secret"] = generate_widget_jwt_secret()

    await firestore.update_widget(widget_id, update_data)

    updated_widget = await firestore.get_widget(widget_id)
    return WidgetResponse(**updated_widget)


@router.delete("/widgets/{widget_id}")
async def delete_widget(
    widget_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Delete a widget."""
    widget = await firestore.get_widget(widget_id)

    if not widget or widget.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Widget not found")

    await firestore.delete_widget(widget_id)
    return {"status": "deleted"}


@router.get("/widgets/{widget_id}/embed-code", response_model=EmbedCodeResponse)
async def get_embed_code(
    widget_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get embed code for a widget."""
    widget = await firestore.get_widget(widget_id)

    if not widget or widget.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Widget not found")

    settings = get_settings()

    embed_data = generate_embed_code(
        widget_id=widget_id,
        api_url=settings.public_api_url,
        settings=widget,
        jwt_secret=widget.get("jwt_secret"),
    )

    return EmbedCodeResponse(**embed_data)


@router.post("/widgets/{widget_id}/regenerate-jwt-secret")
async def regenerate_jwt_secret(
    widget_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Regenerate JWT secret for a widget."""
    widget = await firestore.get_widget(widget_id)

    if not widget or widget.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Widget not found")

    new_secret = generate_widget_jwt_secret()
    await firestore.update_widget(widget_id, {"jwt_secret": new_secret})

    return {"jwt_secret": new_secret}


# API Key Management
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    data: APIKeyCreate,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Create a new API key."""
    plain_key, key_hash = generate_api_key()

    key_data = {
        "name": data.name,
        "key_hash": key_hash,
        "allowed_domains": data.allowed_domains,
        "is_active": True,
    }

    key_record = await firestore.create_api_key(customer.customer_id, key_data)

    # Return plain key only once (it's not stored)
    return APIKeyResponse(
        id=key_record["id"],
        name=key_record["name"],
        is_active=key_record["is_active"],
        created_at=key_record["created_at"],
        allowed_domains=key_record.get("allowed_domains", []),
        plain_key=plain_key,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List all API keys for the customer."""
    keys = await firestore.list_api_keys(customer.customer_id)
    return [
        APIKeyResponse(
            id=k["id"],
            name=k["name"],
            is_active=k.get("is_active", True),
            created_at=k["created_at"],
            allowed_domains=k.get("allowed_domains", []),
            plain_key=None,  # Never return plain key after creation
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def deactivate_api_key(
    key_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Deactivate an API key."""
    await firestore.deactivate_api_key(customer.customer_id, key_id)
    return {"status": "deactivated"}


# Documents (for assigning to widgets)
@router.get("/documents")
async def list_documents(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List all documents for the customer."""
    documents = await firestore.list_documents_for_customer(customer.customer_id)
    return {"documents": documents}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Upload a document for RAG knowledge base."""
    # Check document limit
    is_allowed, reason = await usage_service.check_usage_limit(
        customer.customer_id, "document"
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=reason,
        )

    # Validate content type
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported: PDF, DOCX, TXT, MD",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size: 50MB",
        )

    try:
        print(f"[UPLOAD] Starting upload for {file.filename}, size: {len(content)} bytes")
        service = get_document_service()
        doc = await service.upload_document_for_customer(
            file_content=content,
            filename=file.filename or "untitled",
            content_type=file.content_type,
            customer_id=customer.customer_id,
        )
        print(f"[UPLOAD] Upload complete: {doc.get('id')}")

        # Record usage
        await usage_service.record_document_upload(customer.customer_id)

        return {
            "id": doc["id"],
            "filename": doc["filename"],
            "status": doc["status"],
            "message": "Document uploaded and processing",
        }
    except ValueError as e:
        print(f"[UPLOAD] ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        print(f"[UPLOAD] Exception: {type(e).__name__}: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/documents/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get document processing status (for polling during upload)."""
    doc = await firestore.get_document(doc_id)

    if not doc or doc.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc_id,
        "status": doc.get("status", "pending"),
        "filename": doc.get("filename"),
        "chunk_count": doc.get("chunk_count", 0),
    }


@router.post("/documents/upload-batch")
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Upload multiple documents at once (max 10 files)."""
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 files per batch upload",
        )

    # Check document limit for all files
    for _ in files:
        is_allowed, reason = await usage_service.check_usage_limit(
            customer.customer_id, "document"
        )
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=reason,
            )

    results = []
    service = get_document_service()

    for file in files:
        result = {"filename": file.filename, "status": "pending", "error": None}

        try:
            # Validate content type
            if file.content_type not in SUPPORTED_TYPES:
                result["status"] = "failed"
                result["error"] = f"Unsupported file type: {file.content_type}"
                results.append(result)
                continue

            # Read and validate file size
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                result["status"] = "failed"
                result["error"] = f"File too large ({len(content) // (1024*1024)}MB). Max: 50MB"
                results.append(result)
                continue

            # Upload and process
            doc = await service.upload_document_for_customer(
                file_content=content,
                filename=file.filename or "untitled",
                content_type=file.content_type,
                customer_id=customer.customer_id,
            )

            # Record usage
            await usage_service.record_document_upload(customer.customer_id)

            result["status"] = "success"
            result["id"] = doc["id"]

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        results.append(result)

    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    return {
        "message": f"Processed {len(files)} files: {successful} successful, {failed} failed",
        "results": results,
    }


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Delete a document."""
    doc = await firestore.get_document(doc_id)

    if not doc or doc.get("customer_id") != customer.customer_id:
        raise HTTPException(status_code=404, detail="Document not found")

    service = get_document_service()
    await service.delete_document(doc_id)

    return {"status": "deleted"}


@router.post("/documents/scrape")
async def scrape_url(
    request: ScrapeURLRequest,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Scrape a URL or sitemap and add to knowledge base."""
    # Check scrape limit
    is_allowed, reason = await usage_service.check_usage_limit(
        customer.customer_id, "scrape"
    )
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=reason,
        )

    try:
        service = get_scraper_service()
        scrape_request = ScrapeRequest(
            url=request.url,
            scrape_type=request.scrape_type,
            max_pages=min(request.max_pages, 50),  # Cap at 50 pages
        )
        result = await service.scrape_and_ingest_for_customer(
            request=scrape_request,
            customer_id=customer.customer_id,
        )

        # Record usage
        await usage_service.record_scrape_usage(
            customer.customer_id,
            result["processed"],
        )

        return {
            "status": "completed",
            "pages_processed": result["processed"],
            "pages_failed": result["failed"],
            "documents": [r for r in result["results"] if "error" not in r],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


# Available Models
@router.get("/models")
async def list_available_models(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
):
    """List available Gemini models."""
    from src.features.customers.models import MODEL_PRICING

    models = []
    for model in GeminiModel:
        pricing = MODEL_PRICING.get(model, {"input": 0, "output": 0})
        models.append({
            "id": model.value,
            "name": model.name.replace("_", " ").title(),
            "pricing": {
                "input_per_1m_tokens": pricing["input"],
                "output_per_1m_tokens": pricing["output"],
            },
        })
    return {"models": models}


# Conversations
@router.get("/conversations")
async def list_conversations(
    widget_id: str | None = None,
    limit: int = 50,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List conversations for customer's widgets."""
    # Get customer's widget IDs
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_ids = [w["id"] for w in widgets]

    if not widget_ids:
        return {"conversations": []}

    # If specific widget requested, verify ownership
    if widget_id:
        if widget_id not in widget_ids:
            raise HTTPException(status_code=404, detail="Widget not found")
        widget_ids = [widget_id]

    # Get conversations from analytics_events grouped by conversation_id
    from collections import defaultdict
    from datetime import datetime, timedelta

    # Query recent analytics events
    cutoff = datetime.utcnow() - timedelta(days=30)
    events_query = firestore.db.collection("analytics_events")
    events_query = events_query.where("timestamp", ">=", cutoff)
    events = list(events_query.order_by("timestamp", direction="DESCENDING").limit(1000).stream())

    # Group by conversation_id
    conversations = defaultdict(lambda: {
        "messages": [],
        "widget_id": None,
        "first_message_at": None,
        "last_message_at": None,
    })

    for event in events:
        data = event.to_dict()
        if data.get("widget_id") not in widget_ids:
            continue

        conv_id = data.get("conversation_id")
        if not conv_id:
            continue

        conv = conversations[conv_id]
        conv["widget_id"] = data.get("widget_id")
        conv["session_id"] = data.get("session_id")

        timestamp = data.get("timestamp")
        if conv["first_message_at"] is None or timestamp < conv["first_message_at"]:
            conv["first_message_at"] = timestamp
        if conv["last_message_at"] is None or timestamp > conv["last_message_at"]:
            conv["last_message_at"] = timestamp

        if data.get("role") == "user" and data.get("message_preview"):
            conv["messages"].append({
                "role": "user",
                "preview": data.get("message_preview"),
                "timestamp": timestamp,
            })

    # Convert to list and sort by last_message_at
    result = []
    for conv_id, conv_data in conversations.items():
        if not conv_data["messages"]:
            continue

        # Get widget name
        widget = next((w for w in widgets if w["id"] == conv_data["widget_id"]), None)
        widget_name = widget["name"] if widget else "Unknown"

        result.append({
            "id": conv_id,
            "widget_id": conv_data["widget_id"],
            "widget_name": widget_name,
            "session_id": conv_data["session_id"],
            "message_count": len(conv_data["messages"]),
            "first_message": conv_data["messages"][-1]["preview"] if conv_data["messages"] else "",
            "first_message_at": conv_data["first_message_at"],
            "last_message_at": conv_data["last_message_at"],
        })

    # Sort by last_message_at descending
    result.sort(key=lambda x: x["last_message_at"] or datetime.min, reverse=True)

    return {"conversations": result[:limit]}


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get messages for a specific conversation."""
    # Verify this conversation belongs to customer's widget
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_ids = [w["id"] for w in widgets]

    # Get messages from the conversation subcollection
    messages = await firestore.get_messages(conversation_id, limit=100)

    if not messages:
        return {"messages": []}

    # Format messages for display
    result = []
    for msg in messages:
        result.append({
            "id": msg.get("id"),
            "role": msg.get("role"),
            "content": msg.get("content"),
            "created_at": msg.get("created_at"),
            "sources": msg.get("sources", []),
        })

    return {"messages": result}


# Analytics
@router.get("/analytics/overview")
async def get_analytics_overview(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get all-time and current month analytics overview."""
    from collections import defaultdict
    from datetime import datetime

    # Get customer's widget IDs
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_ids = [w["id"] for w in widgets]

    if not widget_ids:
        return {
            "all_time": {"total_messages": 0, "total_conversations": 0, "avg_response_time_ms": 0},
            "current_month": {"messages": 0, "conversations": 0},
        }

    # Query all analytics events for customer's widgets
    events_query = firestore.db.collection("analytics_events")
    all_events = list(events_query.stream())

    # Filter for customer's widgets and aggregate
    total_messages = 0
    total_response_time = 0
    response_count = 0
    conversations = set()
    current_month = datetime.utcnow().strftime("%Y-%m")
    monthly_messages = 0
    monthly_conversations = set()

    for event in all_events:
        data = event.to_dict()
        if data.get("widget_id") not in widget_ids:
            continue

        total_messages += 1
        conv_id = data.get("conversation_id")
        if conv_id:
            conversations.add(conv_id)

        if data.get("response_time_ms"):
            total_response_time += data["response_time_ms"]
            response_count += 1

        # Check if current month
        timestamp = data.get("timestamp")
        if timestamp and timestamp.strftime("%Y-%m") == current_month:
            monthly_messages += 1
            if conv_id:
                monthly_conversations.add(conv_id)

    avg_response_time = total_response_time / max(response_count, 1)

    return {
        "all_time": {
            "total_messages": total_messages,
            "total_conversations": len(conversations),
            "avg_response_time_ms": round(avg_response_time, 0),
        },
        "current_month": {
            "messages": monthly_messages,
            "conversations": len(monthly_conversations),
        },
    }


@router.get("/analytics/daily-usage")
async def get_daily_usage(
    days: int = 30,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get daily usage statistics. Set days=0 for all-time."""
    from collections import defaultdict
    from datetime import datetime, timedelta

    # Get customer's widget IDs
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_ids = [w["id"] for w in widgets]

    if not widget_ids:
        return {"period": f"{days}d" if days > 0 else "all", "data": []}

    # Query analytics events
    events_query = firestore.db.collection("analytics_events")

    if days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        events_query = events_query.where("timestamp", ">=", cutoff)

    events = list(events_query.stream())

    # Group by day
    daily_stats = defaultdict(lambda: {"messages": 0, "conversations": set()})

    for event in events:
        data = event.to_dict()
        if data.get("widget_id") not in widget_ids:
            continue

        timestamp = data.get("timestamp")
        if not timestamp:
            continue

        day = timestamp.strftime("%Y-%m-%d")
        daily_stats[day]["messages"] += 1
        conv_id = data.get("conversation_id")
        if conv_id:
            daily_stats[day]["conversations"].add(conv_id)

    # Convert to list
    result = []
    for day in sorted(daily_stats.keys()):
        stats = daily_stats[day]
        result.append({
            "date": day,
            "messages": stats["messages"],
            "conversations": len(stats["conversations"]),
        })

    period = "all" if days == 0 else f"{days}d"
    return {"period": period, "data": result}


@router.get("/analytics/widgets")
async def get_widget_analytics(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get per-widget message counts."""
    from collections import defaultdict

    # Get customer's widgets
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_map = {w["id"]: w["name"] for w in widgets}
    widget_ids = list(widget_map.keys())

    if not widget_ids:
        return {"widgets": []}

    # Query analytics events
    events = list(firestore.db.collection("analytics_events").stream())

    # Count per widget
    widget_counts = defaultdict(int)
    for event in events:
        data = event.to_dict()
        wid = data.get("widget_id")
        if wid in widget_ids:
            widget_counts[wid] += 1

    # Build result
    result = []
    for wid, count in sorted(widget_counts.items(), key=lambda x: x[1], reverse=True):
        result.append({
            "id": wid,
            "name": widget_map.get(wid, "Unknown"),
            "messages": count,
        })

    # Include widgets with 0 messages
    for wid, name in widget_map.items():
        if wid not in widget_counts:
            result.append({"id": wid, "name": name, "messages": 0})

    return {"widgets": result}


@router.get("/analytics/top-questions")
async def get_top_questions(
    limit: int = 10,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get most frequently asked questions."""
    from collections import defaultdict

    # Get customer's widget IDs
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_ids = [w["id"] for w in widgets]

    if not widget_ids:
        return {"questions": []}

    # Query user messages from analytics events
    events_query = firestore.db.collection("analytics_events")
    events_query = events_query.where("role", "==", "user")
    events = list(events_query.stream())

    # Count questions
    question_counts = defaultdict(lambda: {"count": 0, "original": ""})

    for event in events:
        data = event.to_dict()
        if data.get("widget_id") not in widget_ids:
            continue

        preview = data.get("message_preview", "")
        if len(preview) < 10:
            continue

        # Normalize for grouping
        normalized = preview.lower().strip()[:100]
        question_counts[normalized]["count"] += 1
        question_counts[normalized]["original"] = preview

    # Sort and return top N
    sorted_questions = sorted(
        question_counts.items(),
        key=lambda x: x[1]["count"],
        reverse=True,
    )[:limit]

    return {
        "questions": [
            {"text": data["original"], "count": data["count"]}
            for _, data in sorted_questions
        ]
    }


def _sanitize_csv_field(value: str) -> str:
    """Prevent CSV injection by escaping formula characters."""
    if isinstance(value, str) and value and value[0] in ("=", "@", "+", "-", "\t", "\r"):
        return "'" + value
    return value


@router.get("/analytics/export")
async def export_analytics_csv(
    days: int = Query(default=30, ge=0, le=365),
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Export analytics data as CSV."""
    import re
    from datetime import timedelta

    # Get customer's widget IDs
    widgets = await firestore.list_widgets_for_customer(customer.customer_id)
    widget_map = {w["id"]: w["name"] for w in widgets}
    widget_ids = list(widget_map.keys())

    if not widget_ids:
        # Return empty CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "widget_name", "messages", "conversations"])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics.csv"},
        )

    # Query analytics events
    events_query = firestore.db.collection("analytics_events")

    if days > 0:
        cutoff = datetime.utcnow() - timedelta(days=days)
        events_query = events_query.where("timestamp", ">=", cutoff)

    events = list(events_query.stream())

    # Group by day and widget
    from collections import defaultdict
    daily_widget_stats = defaultdict(lambda: defaultdict(lambda: {"messages": 0, "conversations": set()}))

    for event in events:
        data = event.to_dict()
        wid = data.get("widget_id")
        if wid not in widget_ids:
            continue

        timestamp = data.get("timestamp")
        if not timestamp:
            continue

        day = timestamp.strftime("%Y-%m-%d")
        daily_widget_stats[day][wid]["messages"] += 1
        conv_id = data.get("conversation_id")
        if conv_id:
            daily_widget_stats[day][wid]["conversations"].add(conv_id)

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "widget_name", "messages", "conversations"])

    for day in sorted(daily_widget_stats.keys()):
        for wid, stats in daily_widget_stats[day].items():
            writer.writerow([
                day,
                _sanitize_csv_field(widget_map.get(wid, "Unknown")),
                stats["messages"],
                len(stats["conversations"]),
            ])

    output.seek(0)
    # Sanitize filename to prevent header injection
    safe_customer_id = re.sub(r"[^a-zA-Z0-9_-]", "", customer.customer_id)
    filename = f"analytics_{safe_customer_id}_{days}d.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
