"""Analytics API endpoints."""

from fastapi import APIRouter, Query

from .models import DashboardStats
from .service import get_analytics_service

router = APIRouter(prefix="/api/admin/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard(
    widget_id: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Get complete dashboard statistics.

    Args:
        widget_id: Filter by widget ID (optional)
        days: Number of days to include (default 30)

    Returns:
        Dashboard statistics including overview, daily usage, and popular questions
    """
    service = get_analytics_service()
    return await service.get_dashboard_stats(widget_id=widget_id, days=days)


@router.get("/overview")
async def get_overview(widget_id: str | None = None):
    """
    Get overview statistics.

    Returns total conversations, messages, and averages.
    """
    service = get_analytics_service()
    return await service.get_stats_overview(widget_id)


@router.get("/usage")
async def get_usage(
    widget_id: str | None = None,
    days: int = Query(default=30, ge=1, le=365),
):
    """
    Get daily usage statistics.

    Returns conversation and message counts per day.
    """
    service = get_analytics_service()
    return await service.get_usage_by_day(days, widget_id)


@router.get("/popular-questions")
async def get_popular_questions(
    widget_id: str | None = None,
    limit: int = Query(default=10, ge=1, le=100),
):
    """
    Get most frequently asked questions.

    Returns top questions sorted by frequency.
    """
    service = get_analytics_service()
    return await service.get_popular_questions(widget_id, limit)


@router.get("/widgets")
async def get_widget_usage():
    """
    Get message counts per widget.

    Returns a map of widget_id to message count.
    """
    service = get_analytics_service()
    return await service.get_widget_usage()
