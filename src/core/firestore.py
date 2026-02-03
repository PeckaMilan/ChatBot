"""Firestore client wrapper for document and chunk storage."""

from datetime import datetime
from typing import Any

from google.cloud import firestore

from src.config import get_settings


class FirestoreClient:
    """Wrapper for Firestore operations."""

    _instance: "FirestoreClient | None" = None
    _db: firestore.Client | None = None

    def __new__(cls) -> "FirestoreClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def db(self) -> firestore.Client:
        """Get or create Firestore client."""
        if self._db is None:
            settings = get_settings()
            self._db = firestore.Client(project=settings.google_cloud_project)
        return self._db

    # Document operations
    async def create_document(
        self,
        user_id: str,
        filename: str,
        content_type: str,
        storage_path: str,
    ) -> dict[str, Any]:
        """Create a new document record."""
        doc_ref = self.db.collection("documents").document()
        doc_data = {
            "id": doc_ref.id,
            "user_id": user_id,
            "filename": filename,
            "content_type": content_type,
            "storage_path": storage_path,
            "status": "pending",
            "chunk_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        doc_ref.set(doc_data)
        return doc_data

    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get document by ID."""
        doc_ref = self.db.collection("documents").document(doc_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None

    async def update_document_status(
        self, doc_id: str, status: str, chunk_count: int = 0
    ) -> None:
        """Update document processing status."""
        doc_ref = self.db.collection("documents").document(doc_id)
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if chunk_count > 0:
            update_data["chunk_count"] = chunk_count
        doc_ref.update(update_data)

    async def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        """List all documents for a user."""
        docs = (
            self.db.collection("documents")
            .where("user_id", "==", user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    async def delete_document(self, doc_id: str) -> None:
        """Delete document and all its chunks."""
        doc_ref = self.db.collection("documents").document(doc_id)
        # Delete all chunks first
        chunks = doc_ref.collection("chunks").stream()
        for chunk in chunks:
            chunk.reference.delete()
        # Delete document
        doc_ref.delete()

    # Chunk operations
    async def create_chunks(
        self, doc_id: str, chunks: list[dict[str, Any]]
    ) -> None:
        """Create multiple chunks for a document."""
        doc_ref = self.db.collection("documents").document(doc_id)
        batch = self.db.batch()

        for chunk in chunks:
            chunk_ref = doc_ref.collection("chunks").document()
            chunk_data = {
                "id": chunk_ref.id,
                "document_id": doc_id,
                "text": chunk["text"],
                "embedding": chunk["embedding"],
                "page_number": chunk.get("page_number"),
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk.get("metadata", {}),
            }
            batch.set(chunk_ref, chunk_data)

        batch.commit()

    async def get_all_chunks(self, doc_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Get all chunks, optionally filtered by document IDs."""
        all_chunks = []

        if doc_ids:
            for doc_id in doc_ids:
                doc_ref = self.db.collection("documents").document(doc_id)
                chunks = doc_ref.collection("chunks").stream()
                all_chunks.extend([chunk.to_dict() for chunk in chunks])
        else:
            # Get chunks from all documents (for single user/project)
            docs = self.db.collection("documents").stream()
            for doc in docs:
                chunks = doc.reference.collection("chunks").stream()
                all_chunks.extend([chunk.to_dict() for chunk in chunks])

        return all_chunks

    # Conversation operations
    async def create_conversation(self, session_id: str, document_ids: list[str]) -> dict[str, Any]:
        """Create a new conversation."""
        conv_ref = self.db.collection("conversations").document()
        conv_data = {
            "id": conv_ref.id,
            "session_id": session_id,
            "document_ids": document_ids,
            "created_at": datetime.utcnow(),
            "last_message_at": datetime.utcnow(),
        }
        conv_ref.set(conv_data)
        return conv_data

    async def get_conversation_by_session(self, session_id: str) -> dict[str, Any] | None:
        """Get conversation by session ID."""
        convs = (
            self.db.collection("conversations")
            .where("session_id", "==", session_id)
            .limit(1)
            .stream()
        )
        for conv in convs:
            return conv.to_dict()
        return None

    async def add_message(
        self, conversation_id: str, role: str, content: str, sources: list[dict] | None = None
    ) -> dict[str, Any]:
        """Add a message to a conversation."""
        conv_ref = self.db.collection("conversations").document(conversation_id)
        msg_ref = conv_ref.collection("messages").document()

        msg_data = {
            "id": msg_ref.id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources,
            "created_at": datetime.utcnow(),
        }
        msg_ref.set(msg_data)

        # Update last_message_at
        conv_ref.update({"last_message_at": datetime.utcnow()})

        return msg_data

    async def get_messages(self, conversation_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent messages from a conversation."""
        conv_ref = self.db.collection("conversations").document(conversation_id)
        messages = (
            conv_ref.collection("messages")
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return list(reversed([msg.to_dict() for msg in messages]))

    # Settings operations
    async def get_settings(self, user_id: str) -> dict[str, Any]:
        """Get user/project settings."""
        doc_ref = self.db.collection("settings").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        # Return defaults
        return {
            "chatbot_name": "Assistant",
            "welcome_message": "Hello! How can I help you today?",
            "system_prompt": "You are a helpful assistant.",
            "widget_color": "#007bff",
        }

    async def update_settings(self, user_id: str, settings: dict[str, Any]) -> None:
        """Update user/project settings."""
        doc_ref = self.db.collection("settings").document(user_id)
        doc_ref.set(settings, merge=True)


def get_firestore_client() -> FirestoreClient:
    """Get Firestore client instance (dependency injection)."""
    return FirestoreClient()
