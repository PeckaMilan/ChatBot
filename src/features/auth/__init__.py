"""Authentication and authorization module."""

from .jwt import (
    generate_api_key,
    hash_api_key,
    create_user_identity_token,
    verify_user_identity_token,
    generate_widget_jwt_secret,
)
from .dependencies import (
    get_current_customer,
    get_widget_context,
    verify_admin_token,
    AuthenticatedCustomer,
    AuthenticatedWidget,
)

__all__ = [
    "generate_api_key",
    "hash_api_key",
    "create_user_identity_token",
    "verify_user_identity_token",
    "generate_widget_jwt_secret",
    "get_current_customer",
    "get_widget_context",
    "verify_admin_token",
    "AuthenticatedCustomer",
    "AuthenticatedWidget",
]
