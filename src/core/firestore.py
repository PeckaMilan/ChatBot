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
            # Use project from settings if provided, otherwise auto-detect
            project = settings.google_cloud_project if settings.google_cloud_project else None
            self._db = firestore.Client(project=project)
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
        """Delete document and all its chunks using batch deletes."""
        doc_ref = self.db.collection("documents").document(doc_id)
        # Delete chunks in small batches (embeddings make docs large)
        chunks = list(doc_ref.collection("chunks").stream())
        for i in range(0, len(chunks), 20):
            batch = self.db.batch()
            for chunk in chunks[i:i + 20]:
                batch.delete(chunk.reference)
            batch.commit()
        # Delete document
        doc_ref.delete()

    # Chunk operations
    async def create_chunks(
        self, doc_id: str, chunks: list[dict[str, Any]]
    ) -> None:
        """Create multiple chunks for a document in batches."""
        doc_ref = self.db.collection("documents").document(doc_id)

        # Firestore batch limit is 500, but embeddings are large so use smaller batches
        batch_size = 50

        for i in range(0, len(chunks), batch_size):
            batch = self.db.batch()
            batch_chunks = chunks[i:i + batch_size]

            for chunk in batch_chunks:
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

    # ==================== MULTI-TENANT OPERATIONS ====================

    # Customer operations
    async def create_customer(self, customer_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new customer."""
        ref = self.db.collection("customers").document()
        customer_data = {
            **customer_data,
            "id": ref.id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        ref.set(customer_data)
        return customer_data

    async def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer by ID."""
        doc = self.db.collection("customers").document(customer_id).get()
        return doc.to_dict() if doc.exists else None

    async def get_customer_by_email(self, email: str) -> dict[str, Any] | None:
        """Get customer by email."""
        docs = (
            self.db.collection("customers")
            .where("email", "==", email)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    async def update_customer(
        self, customer_id: str, update_data: dict[str, Any]
    ) -> None:
        """Update customer data."""
        ref = self.db.collection("customers").document(customer_id)
        update_data["updated_at"] = datetime.utcnow()
        ref.update(update_data)

    async def list_customers(
        self,
        status: str | None = None,
        tier: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List customers with optional filters."""
        query = self.db.collection("customers")

        if status:
            query = query.where("status", "==", status)
        if tier:
            query = query.where("subscription_tier", "==", tier)

        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        docs = list(query.offset(offset).limit(limit).stream())
        return [doc.to_dict() for doc in docs]

    # API Key operations (top-level collection to avoid collection_group index requirement)
    async def create_api_key(
        self, customer_id: str, key_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create API key for customer."""
        ref = self.db.collection("api_keys").document()
        key_data = {
            **key_data,
            "id": ref.id,
            "customer_id": customer_id,
            "created_at": datetime.utcnow(),
        }
        ref.set(key_data)
        return key_data

    async def get_api_key_by_hash(self, key_hash: str) -> dict[str, Any] | None:
        """Find API key by hash (for authentication)."""
        docs = (
            self.db.collection("api_keys")
            .where("key_hash", "==", key_hash)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return doc.to_dict()
        return None

    async def list_api_keys(self, customer_id: str) -> list[dict[str, Any]]:
        """List all API keys for a customer."""
        docs = (
            self.db.collection("api_keys")
            .where("customer_id", "==", customer_id)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    async def deactivate_api_key(self, customer_id: str, key_id: str) -> None:
        """Deactivate an API key."""
        ref = self.db.collection("api_keys").document(key_id)
        ref.update({"is_active": False})

    # Widget operations
    async def create_widget(
        self, customer_id: str, widget_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create widget for customer."""
        ref = self.db.collection("widgets").document()
        widget_data = {
            **widget_data,
            "id": ref.id,
            "customer_id": customer_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        ref.set(widget_data)
        return widget_data

    async def get_widget(self, widget_id: str) -> dict[str, Any] | None:
        """Get widget by ID."""
        doc = self.db.collection("widgets").document(widget_id).get()
        return doc.to_dict() if doc.exists else None

    async def update_widget(
        self, widget_id: str, update_data: dict[str, Any]
    ) -> None:
        """Update widget data."""
        ref = self.db.collection("widgets").document(widget_id)
        update_data["updated_at"] = datetime.utcnow()
        ref.update(update_data)

    async def list_widgets_for_customer(
        self, customer_id: str
    ) -> list[dict[str, Any]]:
        """List all widgets for a customer."""
        docs = (
            self.db.collection("widgets")
            .where("customer_id", "==", customer_id)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    async def delete_widget(self, widget_id: str) -> None:
        """Delete a widget."""
        self.db.collection("widgets").document(widget_id).delete()

    # Usage tracking
    async def record_usage(self, usage_data: dict[str, Any]) -> None:
        """Record a usage event."""
        ref = self.db.collection("usage").document()
        usage_data = {
            **usage_data,
            "id": ref.id,
            "timestamp": datetime.utcnow(),
            "billing_period": datetime.utcnow().strftime("%Y-%m"),
        }
        ref.set(usage_data)

    async def get_monthly_usage(
        self, customer_id: str, billing_period: str
    ) -> dict[str, Any]:
        """Get aggregated monthly usage for a customer."""
        docs = (
            self.db.collection("usage")
            .where("customer_id", "==", customer_id)
            .where("billing_period", "==", billing_period)
            .stream()
        )

        summary = {
            "total_messages": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_embeddings": 0,
            "total_documents": 0,
            "total_scrapes": 0,
            "estimated_cost": 0.0,
        }

        for doc in docs:
            data = doc.to_dict()
            usage_type = data.get("usage_type", "")

            if usage_type == "chat_message":
                summary["total_messages"] += data.get("quantity", 1)
            elif usage_type == "embedding_generation":
                summary["total_embeddings"] += data.get("quantity", 1)
            elif usage_type == "document_upload":
                summary["total_documents"] += data.get("quantity", 1)
            elif usage_type == "web_scrape":
                summary["total_scrapes"] += data.get("quantity", 1)

            summary["total_input_tokens"] += data.get("input_tokens", 0)
            summary["total_output_tokens"] += data.get("output_tokens", 0)
            summary["estimated_cost"] += data.get("estimated_cost_usd", 0)

        return summary

    # Tenant-scoped document operations
    async def list_documents_for_customer(
        self, customer_id: str
    ) -> list[dict[str, Any]]:
        """List documents for a specific customer (tenant isolation)."""
        # Note: Removed order_by to avoid needing composite index
        # Add index later: customer_id ASC, created_at DESC
        docs = (
            self.db.collection("documents")
            .where("customer_id", "==", customer_id)
            .stream()
        )
        result = [doc.to_dict() for doc in docs]
        # Sort in memory (OK for small datasets)
        result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return result

    async def create_document_for_customer(
        self,
        customer_id: str,
        filename: str,
        content_type: str,
        storage_path: str,
    ) -> dict[str, Any]:
        """Create a new document record for a customer."""
        doc_ref = self.db.collection("documents").document()
        doc_data = {
            "id": doc_ref.id,
            "customer_id": customer_id,
            "user_id": customer_id,  # For backward compatibility
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


def get_firestore_client() -> FirestoreClient:
    """Get Firestore client instance (dependency injection)."""
    return FirestoreClient()
