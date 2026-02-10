"""Rate limiting configuration for API endpoints."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_rate_limit_key(request: Request) -> str:
    """Get composite key: widget_id + IP for chat endpoints, IP otherwise."""
    ip = get_remote_address(request)

    # For widget endpoints, combine widget_id with IP
    path = request.url.path
    if "/widget/" in path:
        parts = path.split("/widget/")
        if len(parts) > 1:
            widget_id = parts[1].split("/")[0]
            return f"widget:{widget_id}:{ip}"

    return ip


limiter = Limiter(key_func=get_rate_limit_key)
