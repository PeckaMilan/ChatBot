"""Customer portal response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.features.billing.models import MonthlyUsageSummary
from src.features.customers.models import WidgetResponse


class DashboardResponse(BaseModel):
    """Dashboard overview for a customer."""

    customer_id: str
    company_name: str
    subscription_tier: str
    widgets_count: int
    documents_count: int
    documents_limit: int
    usage: MonthlyUsageSummary


class EmbedCodeResponse(BaseModel):
    """Widget embed code options."""

    widget_id: str
    api_url: str
    standard: str
    with_identity: str
    iframe: str
    jwt_secret: Optional[str] = None
