"""Analytics data models."""

from datetime import datetime
from pydantic import BaseModel, Field


class MessageEvent(BaseModel):
    """Event logged for each message."""
    conversation_id: str
    session_id: str
    widget_id: str
    role: str  # 'user' or 'assistant'
    message_length: int
    response_time_ms: int | None = None
    language: str | None = None
    timestamp: datetime


class ConversationStats(BaseModel):
    """Aggregated conversation statistics."""
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    avg_response_time_ms: float


class UsageStats(BaseModel):
    """Usage statistics for a time period."""
    date: str
    conversations: int
    messages: int
    unique_sessions: int


class PopularQuestion(BaseModel):
    """Popular question tracking."""
    question_text: str
    count: int
    last_asked: datetime


class DashboardStats(BaseModel):
    """Complete dashboard statistics."""
    overview: ConversationStats
    usage_by_day: list[UsageStats]
    popular_questions: list[PopularQuestion]
    widget_usage: dict[str, int]
