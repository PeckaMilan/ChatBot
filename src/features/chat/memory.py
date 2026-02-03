"""Conversation memory management."""

import uuid
from typing import Any

from src.core.firestore import FirestoreClient, get_firestore_client


class ConversationMemory:
    """Manage conversation history and context."""

    def __init__(self, firestore: FirestoreClient):
        self.firestore = firestore

    @staticmethod
    def generate_session_id() -> str:
        """Generate a new session ID."""
        return str(uuid.uuid4())

    async def get_or_create_conversation(
        self,
        session_id: str,
        document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get existing conversation or create new one.

        Args:
            session_id: Session identifier
            document_ids: Document IDs to associate with conversation

        Returns:
            Conversation record
        """
        # Try to get existing conversation
        conversation = await self.firestore.get_conversation_by_session(session_id)

        if conversation:
            return conversation

        # Create new conversation
        return await self.firestore.create_conversation(
            session_id=session_id,
            document_ids=document_ids or [],
        )

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Add a message to the conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional source references

        Returns:
            Message record
        """
        return await self.firestore.add_message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources,
        )

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """
        Get conversation history for context.

        Args:
            conversation_id: Conversation ID
            limit: Max messages to retrieve

        Returns:
            List of message dicts with role and content
        """
        messages = await self.firestore.get_messages(conversation_id, limit)
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]


def get_conversation_memory() -> ConversationMemory:
    """Get conversation memory instance."""
    return ConversationMemory(firestore=get_firestore_client())
