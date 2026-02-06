"""Admin portal response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CustomerSummary(BaseModel):
    """Customer summary for admin list view."""

    id: str
    email: str
    company_name: str
    subscription_tier: str
    status: str
    created_at: datetime
    current_month_messages: int = 0
    current_month_cost: float = 0.0


class CustomerListResponse(BaseModel):
    """Paginated customer list response."""

    customers: list[CustomerSummary]
    total: int
    offset: int
    limit: int


class CustomerDetailResponse(BaseModel):
    """Detailed customer information for admin."""

    customer: dict
    widgets: list[dict]
    documents_count: int
    current_usage: dict
    historical_usage: list[dict]


class PlatformStatsResponse(BaseModel):
    """Platform-wide statistics."""

    total_customers: int
    customers_by_status: dict[str, int]
    customers_by_tier: dict[str, int]
    total_widgets: int
    total_documents: int
    current_month_messages: int
    current_month_cost: float


class CustomerCreateRequest(BaseModel):
    """Request to create a new customer (admin onboarding)."""

    email: str
    company_name: str
    subscription_tier: str = "free"


class CustomerUpdateRequest(BaseModel):
    """Request to update customer (admin)."""

    company_name: Optional[str] = None
    subscription_tier: Optional[str] = None
    status: Optional[str] = None
    monthly_message_limit: Optional[int] = None
    monthly_document_limit: Optional[int] = None
    monthly_scrape_limit: Optional[int] = None
