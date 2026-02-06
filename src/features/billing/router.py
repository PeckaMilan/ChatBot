"""Billing API endpoints."""

from fastapi import APIRouter, Depends

from src.features.auth.dependencies import (
    AuthenticatedCustomer,
    get_current_customer,
)

from .models import UsageResponse, PRICING_TIERS
from .service import UsageService, get_usage_service

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/usage", response_model=UsageResponse)
async def get_current_usage(
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Get current month's usage for the authenticated customer."""
    usage = await usage_service.get_current_usage(customer.customer_id)
    return UsageResponse(
        customer_id=usage.customer_id,
        billing_period=usage.billing_period,
        total_messages=usage.total_messages,
        total_input_tokens=usage.total_input_tokens,
        total_output_tokens=usage.total_output_tokens,
        total_estimated_cost=usage.total_estimated_cost,
        messages_remaining=usage.messages_remaining,
        at_limit=usage.at_limit,
    )


@router.get("/usage/history")
async def get_usage_history(
    months: int = 6,
    customer: AuthenticatedCustomer = Depends(get_current_customer),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Get usage history for past N months."""
    history = await usage_service.get_usage_history(customer.customer_id, months)
    return {"history": history}


@router.get("/pricing")
async def get_pricing_tiers():
    """Get available pricing tiers."""
    return {
        "tiers": {
            name: tier.model_dump()
            for name, tier in PRICING_TIERS.items()
        }
    }
