"""Usage tracking and billing service."""

from datetime import datetime
from typing import Optional

from src.core.firestore import FirestoreClient, get_firestore_client

from .models import UsageType, MonthlyUsageSummary


# Gemini/Vertex AI pricing (as of 2025)
PRICING = {
    "gemini_2_flash_input_per_1m": 0.075,  # $0.075 per 1M input tokens
    "gemini_2_flash_output_per_1m": 0.30,  # $0.30 per 1M output tokens
    "embedding_per_1m_chars": 0.00025,  # text-embedding-004
    "firestore_read_per_100k": 0.036,
    "firestore_write_per_100k": 0.108,
    "storage_per_gb_month": 0.026,
}


class UsageLimitExceededError(Exception):
    """Raised when customer exceeds usage limits."""

    pass


class UsageService:
    """Service for tracking and billing usage."""

    def __init__(self, firestore: FirestoreClient):
        self.firestore = firestore

    def calculate_token_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for Gemini API usage."""
        input_cost = (input_tokens / 1_000_000) * PRICING["gemini_2_flash_input_per_1m"]
        output_cost = (output_tokens / 1_000_000) * PRICING["gemini_2_flash_output_per_1m"]
        return input_cost + output_cost

    def calculate_embedding_cost(self, char_count: int) -> float:
        """Calculate cost for embedding generation."""
        return (char_count / 1_000_000) * PRICING["embedding_per_1m_chars"]

    async def record_chat_usage(
        self,
        customer_id: str,
        widget_id: str,
        input_tokens: int,
        output_tokens: int,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Record a chat message usage event."""
        cost = self.calculate_token_cost(input_tokens, output_tokens)

        usage_data = {
            "customer_id": customer_id,
            "widget_id": widget_id,
            "conversation_id": conversation_id,
            "usage_type": UsageType.CHAT_MESSAGE.value,
            "quantity": 1,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost,
        }

        await self.firestore.record_usage(usage_data)

    async def record_embedding_usage(
        self,
        customer_id: str,
        char_count: int,
        chunk_count: int,
    ) -> None:
        """Record embedding generation usage."""
        cost = self.calculate_embedding_cost(char_count)

        usage_data = {
            "customer_id": customer_id,
            "usage_type": UsageType.EMBEDDING_GENERATION.value,
            "quantity": chunk_count,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost_usd": cost,
        }

        await self.firestore.record_usage(usage_data)

    async def record_document_upload(self, customer_id: str) -> None:
        """Record document upload usage."""
        usage_data = {
            "customer_id": customer_id,
            "usage_type": UsageType.DOCUMENT_UPLOAD.value,
            "quantity": 1,
            "estimated_cost_usd": 0.0,
        }
        await self.firestore.record_usage(usage_data)

    async def record_scrape_usage(
        self,
        customer_id: str,
        page_count: int,
    ) -> None:
        """Record web scrape usage."""
        usage_data = {
            "customer_id": customer_id,
            "usage_type": UsageType.WEB_SCRAPE.value,
            "quantity": page_count,
            "estimated_cost_usd": 0.0,
        }
        await self.firestore.record_usage(usage_data)

    async def get_current_usage(
        self,
        customer_id: str,
    ) -> MonthlyUsageSummary:
        """Get current month's usage for a customer."""
        billing_period = datetime.utcnow().strftime("%Y-%m")
        usage = await self.firestore.get_monthly_usage(customer_id, billing_period)

        # Get customer limits
        customer = await self.firestore.get_customer(customer_id)
        if not customer:
            message_limit = 1000
        else:
            message_limit = customer.get("monthly_message_limit", 1000)

        messages_used = usage.get("total_messages", 0)

        return MonthlyUsageSummary(
            customer_id=customer_id,
            billing_period=billing_period,
            total_messages=messages_used,
            total_embeddings=usage.get("total_embeddings", 0),
            total_documents=usage.get("total_documents", 0),
            total_scrapes=usage.get("total_scrapes", 0),
            total_input_tokens=usage.get("total_input_tokens", 0),
            total_output_tokens=usage.get("total_output_tokens", 0),
            total_estimated_cost=usage.get("estimated_cost", 0.0),
            messages_remaining=max(0, message_limit - messages_used),
            at_limit=messages_used >= message_limit,
        )

    async def check_usage_limit(
        self,
        customer_id: str,
        usage_type: str = "message",
    ) -> tuple[bool, str]:
        """
        Check if customer is within usage limits.

        Returns:
            Tuple of (is_allowed, reason)
        """
        usage = await self.get_current_usage(customer_id)

        if usage_type == "message" and usage.at_limit:
            return False, "Monthly message limit reached"

        # Get customer for other limits
        customer = await self.firestore.get_customer(customer_id)
        if customer:
            doc_limit = customer.get("monthly_document_limit", 5)
            scrape_limit = customer.get("monthly_scrape_limit", 10)

            if usage_type == "document" and usage.total_documents >= doc_limit:
                return False, "Monthly document upload limit reached"

            if usage_type == "scrape" and usage.total_scrapes >= scrape_limit:
                return False, "Monthly web scrape limit reached"

        return True, "OK"

    async def get_usage_history(
        self,
        customer_id: str,
        months: int = 6,
    ) -> list[dict]:
        """Get usage history for past N months."""
        from datetime import timedelta

        history = []
        now = datetime.utcnow()

        for i in range(months):
            period_date = now - timedelta(days=30 * i)
            billing_period = period_date.strftime("%Y-%m")
            usage = await self.firestore.get_monthly_usage(customer_id, billing_period)
            history.append(
                {
                    "billing_period": billing_period,
                    **usage,
                }
            )

        return history


def get_usage_service() -> UsageService:
    """Get usage service instance."""
    return UsageService(firestore=get_firestore_client())
