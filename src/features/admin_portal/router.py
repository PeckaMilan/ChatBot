"""Admin portal API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.firestore import FirestoreClient, get_firestore_client
from src.features.auth.dependencies import verify_admin_token
from src.features.auth.jwt import generate_api_key
from src.features.billing.service import UsageService, get_usage_service
from src.features.customers.models import TIER_LIMITS, SubscriptionTier

from .models import (
    CustomerCreateRequest,
    CustomerDetailResponse,
    CustomerListResponse,
    CustomerSummary,
    CustomerUpdateRequest,
    PlatformStatsResponse,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-portal"],
    dependencies=[Depends(verify_admin_token)],
)


@router.get("/stats", response_model=PlatformStatsResponse)
async def get_platform_stats(
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Get platform-wide statistics."""
    # Get all customers
    customers = await firestore.list_customers(limit=1000)

    by_status: dict[str, int] = {}
    by_tier: dict[str, int] = {}

    for c in customers:
        status = c.get("status", "unknown")
        tier = c.get("subscription_tier", "free")
        by_status[status] = by_status.get(status, 0) + 1
        by_tier[tier] = by_tier.get(tier, 0) + 1

    # Count widgets
    widgets_count = 0
    docs_count = 0
    for c in customers:
        widgets = await firestore.list_widgets_for_customer(c["id"])
        widgets_count += len(widgets)
        docs = await firestore.list_documents_for_customer(c["id"])
        docs_count += len(docs)

    # Get current month total usage
    billing_period = datetime.utcnow().strftime("%Y-%m")
    total_messages = 0
    total_cost = 0.0

    for c in customers:
        usage = await firestore.get_monthly_usage(c["id"], billing_period)
        total_messages += usage.get("total_messages", 0)
        total_cost += usage.get("estimated_cost", 0.0)

    return PlatformStatsResponse(
        total_customers=len(customers),
        customers_by_status=by_status,
        customers_by_tier=by_tier,
        total_widgets=widgets_count,
        total_documents=docs_count,
        current_month_messages=total_messages,
        current_month_cost=total_cost,
    )


@router.get("/customers", response_model=CustomerListResponse)
async def list_customers(
    status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List all customers with filtering."""
    customers = await firestore.list_customers(
        status=status,
        tier=tier,
        limit=limit,
        offset=offset,
    )

    billing_period = datetime.utcnow().strftime("%Y-%m")
    customer_summaries = []

    for c in customers:
        usage = await firestore.get_monthly_usage(c["id"], billing_period)
        customer_summaries.append(
            CustomerSummary(
                id=c["id"],
                email=c.get("email", ""),
                company_name=c.get("company_name", ""),
                subscription_tier=c.get("subscription_tier", "free"),
                status=c.get("status", "pending"),
                created_at=c.get("created_at", datetime.utcnow()),
                current_month_messages=usage.get("total_messages", 0),
                current_month_cost=usage.get("estimated_cost", 0.0),
            )
        )

    return CustomerListResponse(
        customers=customer_summaries,
        total=len(customer_summaries),
        offset=offset,
        limit=limit,
    )


@router.post("/customers", response_model=CustomerSummary)
async def create_customer(
    data: CustomerCreateRequest,
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Create a new customer (admin onboarding)."""
    # Check if email already exists
    existing = await firestore.get_customer_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Customer with this email already exists",
        )

    # Get tier limits
    tier = SubscriptionTier(data.subscription_tier)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])

    customer_data = {
        "email": data.email,
        "company_name": data.company_name,
        "subscription_tier": data.subscription_tier,
        "status": "active",
        "monthly_message_limit": limits["monthly_message_limit"],
        "monthly_document_limit": limits["monthly_document_limit"],
        "monthly_scrape_limit": limits["monthly_scrape_limit"],
    }

    customer = await firestore.create_customer(customer_data)

    # Create initial API key
    plain_key, key_hash = generate_api_key()
    await firestore.create_api_key(
        customer["id"],
        {"name": "Default", "key_hash": key_hash, "is_active": True},
    )

    return CustomerSummary(
        id=customer["id"],
        email=customer["email"],
        company_name=customer["company_name"],
        subscription_tier=customer["subscription_tier"],
        status=customer["status"],
        created_at=customer["created_at"],
        current_month_messages=0,
        current_month_cost=0.0,
    )


@router.get("/customers/{customer_id}", response_model=CustomerDetailResponse)
async def get_customer_detail(
    customer_id: str,
    firestore: FirestoreClient = Depends(get_firestore_client),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Get detailed customer information."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    widgets = await firestore.list_widgets_for_customer(customer_id)
    documents = await firestore.list_documents_for_customer(customer_id)
    current_usage = await usage_service.get_current_usage(customer_id)
    historical = await usage_service.get_usage_history(customer_id, months=6)

    return CustomerDetailResponse(
        customer=customer,
        widgets=widgets,
        documents_count=len(documents),
        current_usage=current_usage.model_dump(),
        historical_usage=historical,
    )


@router.patch("/customers/{customer_id}")
async def update_customer(
    customer_id: str,
    data: CustomerUpdateRequest,
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Update customer details."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    update_data = data.model_dump(exclude_unset=True)

    # If changing tier, update limits
    if data.subscription_tier:
        tier = SubscriptionTier(data.subscription_tier)
        limits = TIER_LIMITS.get(tier, TIER_LIMITS[SubscriptionTier.FREE])
        update_data["monthly_message_limit"] = limits["monthly_message_limit"]
        update_data["monthly_document_limit"] = limits["monthly_document_limit"]
        update_data["monthly_scrape_limit"] = limits["monthly_scrape_limit"]

    await firestore.update_customer(customer_id, update_data)

    return {"status": "updated"}


@router.post("/customers/{customer_id}/suspend")
async def suspend_customer(
    customer_id: str,
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Suspend a customer account."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    await firestore.update_customer(customer_id, {"status": "suspended"})
    return {"status": "suspended"}


@router.post("/customers/{customer_id}/activate")
async def activate_customer(
    customer_id: str,
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Activate a customer account."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    await firestore.update_customer(customer_id, {"status": "active"})
    return {"status": "active"}


@router.post("/customers/{customer_id}/create-api-key")
async def create_customer_api_key(
    customer_id: str,
    name: str = Query("API Key"),
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """Create a new API key for a customer (admin action)."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    plain_key, key_hash = generate_api_key()
    key_record = await firestore.create_api_key(
        customer_id,
        {"name": name, "key_hash": key_hash, "is_active": True},
    )

    return {
        "id": key_record["id"],
        "name": key_record["name"],
        "plain_key": plain_key,  # Only returned once!
    }


@router.get("/customers/{customer_id}/api-keys")
async def list_customer_api_keys(
    customer_id: str,
    firestore: FirestoreClient = Depends(get_firestore_client),
):
    """List API keys for a customer."""
    customer = await firestore.get_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    keys = await firestore.list_api_keys(customer_id)
    return {
        "api_keys": [
            {
                "id": k["id"],
                "name": k["name"],
                "is_active": k.get("is_active", True),
                "created_at": k["created_at"],
            }
            for k in keys
        ]
    }
