"""Billing and usage tracking models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class UsageType(str, Enum):
    """Types of billable usage."""

    CHAT_MESSAGE = "chat_message"
    EMBEDDING_GENERATION = "embedding_generation"
    DOCUMENT_UPLOAD = "document_upload"
    WEB_SCRAPE = "web_scrape"
    STORAGE_BYTES = "storage_bytes"


class UsageRecord(BaseModel):
    """Individual usage event record."""

    id: str
    customer_id: str
    widget_id: Optional[str] = None
    conversation_id: Optional[str] = None
    usage_type: UsageType
    quantity: int = 1

    # Token tracking for chat
    input_tokens: int = 0
    output_tokens: int = 0

    # Cost
    estimated_cost_usd: float = 0.0

    # Metadata
    timestamp: datetime
    billing_period: str  # "2026-02" format

    class Config:
        use_enum_values = True


class MonthlyUsageSummary(BaseModel):
    """Aggregated monthly usage for a customer."""

    customer_id: str
    billing_period: str

    # Counts
    total_messages: int = 0
    total_embeddings: int = 0
    total_documents: int = 0
    total_scrapes: int = 0

    # Token usage
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    # Costs
    estimated_gemini_cost: float = 0.0
    estimated_storage_cost: float = 0.0
    total_estimated_cost: float = 0.0

    # Limits
    messages_remaining: int = 0
    at_limit: bool = False


class PricingTier(BaseModel):
    """Pricing tier configuration."""

    name: str
    monthly_price_usd: float

    # Limits
    messages_per_month: int
    documents_per_month: int
    scrapes_per_month: int
    widgets_allowed: int

    # Features
    custom_branding: bool = False
    remove_powered_by: bool = False
    priority_support: bool = False
    api_access: bool = False
    jwt_identity: bool = False


# Predefined pricing tiers
PRICING_TIERS = {
    "free": PricingTier(
        name="Free",
        monthly_price_usd=0,
        messages_per_month=1000,
        documents_per_month=5,
        scrapes_per_month=10,
        widgets_allowed=1,
        custom_branding=False,
        remove_powered_by=False,
        priority_support=False,
        api_access=False,
        jwt_identity=False,
    ),
    "starter": PricingTier(
        name="Starter",
        monthly_price_usd=29,
        messages_per_month=5000,
        documents_per_month=25,
        scrapes_per_month=50,
        widgets_allowed=3,
        custom_branding=True,
        remove_powered_by=False,
        priority_support=False,
        api_access=True,
        jwt_identity=False,
    ),
    "professional": PricingTier(
        name="Professional",
        monthly_price_usd=99,
        messages_per_month=25000,
        documents_per_month=100,
        scrapes_per_month=200,
        widgets_allowed=10,
        custom_branding=True,
        remove_powered_by=True,
        priority_support=False,
        api_access=True,
        jwt_identity=True,
    ),
    "enterprise": PricingTier(
        name="Enterprise",
        monthly_price_usd=299,
        messages_per_month=1000000,
        documents_per_month=1000,
        scrapes_per_month=1000,
        widgets_allowed=100,
        custom_branding=True,
        remove_powered_by=True,
        priority_support=True,
        api_access=True,
        jwt_identity=True,
    ),
}


class UsageResponse(BaseModel):
    """API response for usage data."""

    customer_id: str
    billing_period: str
    total_messages: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost: float
    messages_remaining: int
    at_limit: bool


class InvoiceItem(BaseModel):
    """Line item on an invoice."""

    description: str
    quantity: int
    unit_price_usd: float
    total_usd: float


class Invoice(BaseModel):
    """Monthly invoice for a customer."""

    id: str
    customer_id: str
    billing_period: str
    items: list[InvoiceItem]
    subtotal_usd: float
    tax_usd: float = 0.0
    total_usd: float
    status: str = "pending"  # pending, paid, overdue
    created_at: datetime
    due_date: datetime
