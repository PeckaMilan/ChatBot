"""Analytics service for tracking and retrieving statistics."""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any

from src.core.firestore import FirestoreClient, get_firestore_client

from .models import DashboardStats, ConversationStats, UsageStats, PopularQuestion


class AnalyticsService:
    """Service for analytics operations."""

    def __init__(self, firestore: FirestoreClient):
        self.firestore = firestore

    async def log_message_event(
        self,
        conversation_id: str,
        session_id: str,
        widget_id: str,
        role: str,
        message: str,
        language: str | None = None,
        response_time_ms: int | None = None,
    ) -> None:
        """Log a message event for analytics."""
        event_data = {
            "conversation_id": conversation_id,
            "session_id": session_id,
            "widget_id": widget_id,
            "role": role,
            "message_length": len(message),
            "language": language,
            "response_time_ms": response_time_ms,
            "timestamp": datetime.utcnow(),
        }

        # Store preview for popular questions (user messages only)
        if role == "user":
            event_data["message_preview"] = message[:200]

        ref = self.firestore.db.collection("analytics_events").document()
        event_data["id"] = ref.id
        ref.set(event_data)

    async def get_stats_overview(self, widget_id: str | None = None) -> dict[str, Any]:
        """Get overview statistics."""
        # Count conversations
        query = self.firestore.db.collection("conversations")
        conversations = list(query.stream())
        total_convs = len(conversations)

        # Count messages and response times
        total_messages = 0
        total_response_time = 0
        response_count = 0

        events_query = self.firestore.db.collection("analytics_events")
        if widget_id:
            events_query = events_query.where("widget_id", "==", widget_id)

        events = list(events_query.stream())
        for event in events:
            data = event.to_dict()
            total_messages += 1
            if data.get("response_time_ms"):
                total_response_time += data["response_time_ms"]
                response_count += 1

        avg_response_time = total_response_time / max(response_count, 1)
        avg_messages = total_messages / max(total_convs, 1)

        return {
            "total_conversations": total_convs,
            "total_messages": total_messages,
            "avg_messages_per_conversation": round(avg_messages, 2),
            "avg_response_time_ms": round(avg_response_time, 2),
        }

    async def get_usage_by_day(
        self,
        days: int = 30,
        widget_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get usage statistics grouped by day."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        query = self.firestore.db.collection("analytics_events")
        query = query.where("timestamp", ">=", start_date)

        events = list(query.stream())

        # Group by day
        daily_stats = defaultdict(lambda: {
            "conversations": set(),
            "messages": 0,
            "sessions": set(),
        })

        for event in events:
            data = event.to_dict()
            if widget_id and data.get("widget_id") != widget_id:
                continue

            day = data["timestamp"].strftime("%Y-%m-%d")
            daily_stats[day]["conversations"].add(data.get("conversation_id"))
            daily_stats[day]["messages"] += 1
            daily_stats[day]["sessions"].add(data.get("session_id"))

        # Convert to list
        result = []
        for day in sorted(daily_stats.keys()):
            stats = daily_stats[day]
            result.append({
                "date": day,
                "conversations": len(stats["conversations"]),
                "messages": stats["messages"],
                "unique_sessions": len(stats["sessions"]),
            })

        return result

    async def get_popular_questions(
        self,
        widget_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get most frequently asked questions."""
        query = self.firestore.db.collection("analytics_events")
        query = query.where("role", "==", "user")

        events = list(query.stream())

        # Count question occurrences
        question_counts = defaultdict(lambda: {"count": 0, "last_asked": None})

        for event in events:
            data = event.to_dict()
            if widget_id and data.get("widget_id") != widget_id:
                continue

            preview = data.get("message_preview", "")
            if len(preview) < 10:  # Skip very short messages
                continue

            # Normalize question for grouping
            normalized = preview.lower().strip()[:100]
            question_counts[normalized]["count"] += 1
            question_counts[normalized]["last_asked"] = data["timestamp"]
            question_counts[normalized]["original"] = preview

        # Sort by count and return top N
        sorted_questions = sorted(
            question_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:limit]

        return [
            {
                "question_text": data["original"],
                "count": data["count"],
                "last_asked": data["last_asked"],
            }
            for _, data in sorted_questions
        ]

    async def get_widget_usage(self) -> dict[str, int]:
        """Get message counts per widget."""
        events = list(self.firestore.db.collection("analytics_events").stream())

        widget_counts = defaultdict(int)
        for event in events:
            data = event.to_dict()
            widget_id = data.get("widget_id", "unknown")
            widget_counts[widget_id] += 1

        return dict(widget_counts)

    async def get_dashboard_stats(
        self,
        widget_id: str | None = None,
        days: int = 30,
    ) -> DashboardStats:
        """Get complete dashboard statistics."""
        overview = await self.get_stats_overview(widget_id)
        usage_by_day = await self.get_usage_by_day(days, widget_id)
        popular = await self.get_popular_questions(widget_id)
        widget_usage = await self.get_widget_usage()

        return DashboardStats(
            overview=ConversationStats(**overview),
            usage_by_day=[UsageStats(**u) for u in usage_by_day],
            popular_questions=[PopularQuestion(**p) for p in popular],
            widget_usage=widget_usage,
        )


def get_analytics_service() -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService(firestore=get_firestore_client())
