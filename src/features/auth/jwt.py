"""JWT and API key utilities."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """Decoded JWT token data."""

    sub: str  # user_id
    customer_id: str
    widget_id: str
    exp: datetime
    iat: datetime
    email: Optional[str] = None
    name: Optional[str] = None


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key and its hash.

    Returns:
        Tuple of (plain_key, key_hash)
    """
    plain_key = f"cb_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return plain_key, key_hash


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage/lookup."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_widget_jwt_secret() -> str:
    """Generate a secure JWT secret for a widget."""
    return secrets.token_urlsafe(32)


def create_user_identity_token(
    customer_id: str,
    widget_id: str,
    user_id: str,
    jwt_secret: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    expires_hours: int = 24,
) -> str:
    """
    Create a JWT for end-user identity verification.

    This is used when customers want to identify their end-users
    securely (like ChatBase's identity verification).

    Args:
        customer_id: The customer who owns the widget
        widget_id: The widget being used
        user_id: The end-user's ID from the customer's system
        jwt_secret: The widget's JWT secret
        email: Optional end-user email
        name: Optional end-user name
        expires_hours: Token expiration in hours

    Returns:
        Signed JWT token string
    """
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "customer_id": customer_id,
        "widget_id": widget_id,
        "email": email,
        "name": name,
        "iat": now,
        "exp": now + timedelta(hours=expires_hours),
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def verify_user_identity_token(
    token: str,
    jwt_secret: str,
    widget_id: str,
) -> TokenPayload:
    """
    Verify a user identity JWT.

    Args:
        token: The JWT token to verify
        jwt_secret: The widget's JWT secret
        widget_id: Expected widget ID

    Returns:
        Decoded token payload

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
        jwt.ExpiredSignatureError: If token has expired
    """
    payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])

    # Verify widget_id matches
    if payload.get("widget_id") != widget_id:
        raise jwt.InvalidTokenError("Widget ID mismatch")

    return TokenPayload(
        sub=payload["sub"],
        customer_id=payload["customer_id"],
        widget_id=payload["widget_id"],
        exp=datetime.fromtimestamp(payload["exp"]),
        iat=datetime.fromtimestamp(payload["iat"]),
        email=payload.get("email"),
        name=payload.get("name"),
    )
