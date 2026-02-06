"""Customer, API Key, and Widget data models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SubscriptionTier(str, Enum):
    """Customer subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class CustomerStatus(str, Enum):
    """Customer account status."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class GeminiModel(str, Enum):
    """Available Gemini models."""

    GEMINI_3_FLASH = "gemini-3-flash-preview"  # Newest, fast + capable
    GEMINI_3_PRO = "gemini-3-pro-preview"  # Newest, most capable
    GEMINI_2_FLASH = "gemini-2.0-flash-001"  # Fast, cost-effective
    GEMINI_2_PRO = "gemini-2.0-pro-exp-02-05"  # More capable


# Model pricing (per 1M tokens)
MODEL_PRICING = {
    GeminiModel.GEMINI_3_FLASH: {"input": 0.15, "output": 0.60},
    GeminiModel.GEMINI_3_PRO: {"input": 1.25, "output": 10.00},
    GeminiModel.GEMINI_2_FLASH: {"input": 0.075, "output": 0.30},
    GeminiModel.GEMINI_2_PRO: {"input": 1.25, "output": 5.00},
}


# Tier limits configuration
TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "monthly_message_limit": 1000,
        "monthly_document_limit": 5,
        "monthly_scrape_limit": 10,
        "widgets_allowed": 1,
        "rate_limit_per_minute": 20,
    },
    SubscriptionTier.STARTER: {
        "monthly_message_limit": 5000,
        "monthly_document_limit": 25,
        "monthly_scrape_limit": 50,
        "widgets_allowed": 3,
        "rate_limit_per_minute": 60,
    },
    SubscriptionTier.PROFESSIONAL: {
        "monthly_message_limit": 25000,
        "monthly_document_limit": 100,
        "monthly_scrape_limit": 200,
        "widgets_allowed": 10,
        "rate_limit_per_minute": 200,
    },
    SubscriptionTier.ENTERPRISE: {
        "monthly_message_limit": 1000000,  # Effectively unlimited
        "monthly_document_limit": 1000,
        "monthly_scrape_limit": 1000,
        "widgets_allowed": 100,
        "rate_limit_per_minute": 1000,
    },
}


class Customer(BaseModel):
    """Customer account model."""

    id: str
    email: EmailStr
    company_name: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    status: CustomerStatus = CustomerStatus.PENDING

    # Limits (populated from tier)
    monthly_message_limit: int = 1000
    monthly_document_limit: int = 5
    monthly_scrape_limit: int = 10

    # Billing
    stripe_customer_id: Optional[str] = None
    billing_email: Optional[EmailStr] = None

    # Metadata
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class CustomerCreate(BaseModel):
    """Request model for creating a customer."""

    email: EmailStr
    company_name: str
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE


class CustomerUpdate(BaseModel):
    """Request model for updating a customer."""

    company_name: Optional[str] = None
    subscription_tier: Optional[SubscriptionTier] = None
    status: Optional[CustomerStatus] = None
    billing_email: Optional[EmailStr] = None


class APIKey(BaseModel):
    """API key for customer authentication."""

    id: str
    customer_id: str
    key_hash: str  # SHA256 hash of the actual key
    name: str
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

    # Permissions
    allowed_domains: list[str] = Field(default_factory=list)
    rate_limit_per_minute: int = 60


class APIKeyCreate(BaseModel):
    """Request model for creating an API key."""

    name: str
    allowed_domains: list[str] = Field(default_factory=list)


class APIKeyResponse(BaseModel):
    """Response model for API key (includes plain key only on creation)."""

    id: str
    name: str
    is_active: bool
    created_at: datetime
    allowed_domains: list[str]
    plain_key: Optional[str] = None  # Only returned on creation


class Widget(BaseModel):
    """Embeddable chatbot widget configuration."""

    id: str
    customer_id: str
    name: str

    # Configuration
    chatbot_name: str = "Assistant"
    welcome_message: str = "Hello! How can I help you?"
    system_prompt: str = "You are a helpful assistant."
    widget_color: str = "#007bff"
    logo_url: Optional[str] = None

    # AI Model selection
    model: GeminiModel = GeminiModel.GEMINI_3_FLASH

    # Branding
    show_powered_by: bool = True

    # Knowledge base
    document_ids: list[str] = Field(default_factory=list)

    # Security
    allowed_domains: list[str] = Field(default_factory=list)
    jwt_secret: Optional[str] = None
    require_jwt: bool = False

    # Metadata
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class WidgetCreate(BaseModel):
    """Request model for creating a widget."""

    name: str
    chatbot_name: str = "Assistant"
    welcome_message: str = "Hello! How can I help you?"
    system_prompt: str = "You are a helpful assistant."
    widget_color: str = "#007bff"
    model: GeminiModel = GeminiModel.GEMINI_3_FLASH
    allowed_domains: list[str] = Field(default_factory=list)
    require_jwt: bool = False


class WidgetUpdate(BaseModel):
    """Request model for updating a widget."""

    name: Optional[str] = None
    chatbot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    system_prompt: Optional[str] = None
    widget_color: Optional[str] = None
    logo_url: Optional[str] = None
    model: Optional[GeminiModel] = None
    show_powered_by: Optional[bool] = None
    allowed_domains: Optional[list[str]] = None
    document_ids: Optional[list[str]] = None
    require_jwt: Optional[bool] = None
    is_active: Optional[bool] = None


class WidgetResponse(BaseModel):
    """Response model for widget."""

    id: str
    customer_id: str
    name: str
    chatbot_name: str
    welcome_message: str
    system_prompt: str = "You are a helpful assistant."
    widget_color: str
    model: str = "gemini-3-flash-preview"
    show_powered_by: bool
    allowed_domains: list[str]
    document_ids: list[str]
    require_jwt: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
