"""FastAPI authentication dependencies."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status

from src.core.firestore import FirestoreClient, get_firestore_client

from .jwt import hash_api_key, verify_user_identity_token


class AuthenticatedCustomer:
    """Authenticated customer context."""

    def __init__(self, customer: dict, api_key: dict):
        self.customer = customer
        self.api_key = api_key
        self.customer_id = customer["id"]
        self.email = customer.get("email")
        self.subscription_tier = customer.get("subscription_tier", "free")


class AuthenticatedWidget:
    """Authenticated widget context for chat requests."""

    def __init__(
        self,
        widget: dict,
        customer: dict,
        end_user_id: Optional[str] = None,
        end_user_email: Optional[str] = None,
    ):
        self.widget = widget
        self.customer = customer
        self.widget_id = widget["id"]
        self.customer_id = customer["id"]
        self.end_user_id = end_user_id
        self.end_user_email = end_user_email


async def get_current_customer(
    authorization: str = Header(
        ..., description="API Key: Bearer cb_live_xxx"
    ),
    firestore: FirestoreClient = Depends(get_firestore_client),
) -> AuthenticatedCustomer:
    """
    Validate API key and return customer context.

    Used for customer portal API endpoints.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <api_key>",
        )

    api_key = authorization[7:]  # Remove "Bearer "

    if not api_key.startswith("cb_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    key_hash = hash_api_key(api_key)

    # Look up API key
    key_record = await firestore.get_api_key_by_hash(key_hash)
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not key_record.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is disabled",
        )

    # Check expiration
    expires_at = key_record.get("expires_at")
    if expires_at:
        from datetime import datetime

        if isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

    # Get customer
    customer = await firestore.get_customer(key_record["customer_id"])
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer not found",
        )

    if customer.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Customer account is {customer.get('status', 'inactive')}",
        )

    return AuthenticatedCustomer(customer=customer, api_key=key_record)


async def get_widget_context(
    widget_id: str,
    request: Request,
    x_user_token: Optional[str] = Header(
        None, description="JWT for user identity verification"
    ),
    firestore: FirestoreClient = Depends(get_firestore_client),
) -> AuthenticatedWidget:
    """
    Validate widget access and optionally verify user identity.

    Used for public widget chat endpoints.
    """
    # Get widget
    widget = await firestore.get_widget(widget_id)
    if not widget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found",
        )

    if not widget.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget is disabled",
        )

    # Check domain restriction
    origin = request.headers.get("origin", "")
    allowed_domains = widget.get("allowed_domains", [])

    if allowed_domains and origin:
        domain_allowed = any(domain in origin for domain in allowed_domains)
        if not domain_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Domain not allowed for this widget",
            )

    # Get customer
    customer = await firestore.get_customer(widget["customer_id"])
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget owner not found",
        )

    if customer.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Widget owner account is not active",
        )

    # Verify user identity if required
    end_user_id = None
    end_user_email = None

    if widget.get("require_jwt", False):
        if not x_user_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User identity token required for this widget",
            )

        jwt_secret = widget.get("jwt_secret")
        if not jwt_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Widget JWT not configured",
            )

        try:
            token_data = verify_user_identity_token(
                x_user_token, jwt_secret, widget_id
            )
            end_user_id = token_data.sub
            end_user_email = token_data.email
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid user identity token: {str(e)}",
            )
    elif x_user_token:
        # JWT provided but not required - still validate if secret exists
        jwt_secret = widget.get("jwt_secret")
        if jwt_secret:
            try:
                token_data = verify_user_identity_token(
                    x_user_token, jwt_secret, widget_id
                )
                end_user_id = token_data.sub
                end_user_email = token_data.email
            except Exception:
                pass  # Ignore validation errors if JWT not required

    return AuthenticatedWidget(
        widget=widget,
        customer=customer,
        end_user_id=end_user_id,
        end_user_email=end_user_email,
    )


async def verify_admin_token(
    x_admin_token: str = Header(..., description="Admin API token"),
) -> bool:
    """
    Verify admin access token.

    For MVP, uses environment variable.
    In production, use proper admin auth (OAuth, Firebase Admin, etc.)
    """
    from src.config import get_settings

    settings = get_settings()

    if not settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin authentication not configured",
        )

    if x_admin_token != settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    return True
