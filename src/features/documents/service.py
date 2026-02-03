"""Document service for upload and processing."""

from typing import Any

from src.core.firestore import FirestoreClient, get_firestore_client
from src.core.gemini import GeminiClient, get_gemini_client
from src.core.storage import StorageClient, get_storage_client

from .processor import DocumentProcessor, get_document_processor


class DocumentService:
    """Service for document operations."""

    def __init__(
        self,
        firestore: FirestoreClient,
        storage: StorageClient,
        gemini: GeminiClient,
        processor: DocumentProcessor,
    ):
        self.firestore = firestore
        self.storage = storage
        self.gemini = gemini
        self.processor = processor

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Upload and process a document.

        Args:
            file_content: Raw file bytes
            filename: Original filename
            content_type: MIME type
            user_id: Owner user ID

        Returns:
            Document record
        """
        # 1. Upload to Cloud Storage
        storage_path = await self.storage.upload_file(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            user_id=user_id,
        )

        # 2. Create document record (pending status)
        doc_record = await self.firestore.create_document(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
        )

        # 3. Process document asynchronously
        # For MVP, we process synchronously. In production, use Cloud Tasks/Pub-Sub
        try:
            await self._process_document(doc_record["id"], file_content, content_type)
        except Exception as e:
            await self.firestore.update_document_status(doc_record["id"], "failed")
            raise e

        return doc_record

    async def _process_document(
        self,
        doc_id: str,
        file_content: bytes,
        content_type: str,
    ) -> None:
        """Process document: extract text, chunk, generate embeddings."""
        # Update status to processing
        await self.firestore.update_document_status(doc_id, "processing")

        # 1. Extract text
        text = await self.processor.extract_text(file_content, content_type)

        if not text.strip():
            raise ValueError("No text content extracted from document")

        # 2. Chunk text
        chunks = self.processor.chunk_text(text)

        if not chunks:
            raise ValueError("No chunks generated from document")

        # 3. Generate embeddings
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await self.gemini.generate_embeddings_batch(chunk_texts)

        # 4. Prepare chunks with embeddings
        chunks_with_embeddings = [
            {
                "text": chunks[i]["text"],
                "embedding": embeddings[i],
                "chunk_index": chunks[i]["chunk_index"],
                "page_number": chunks[i].get("page_number"),
                "metadata": {},
            }
            for i in range(len(chunks))
        ]

        # 5. Store chunks in Firestore
        await self.firestore.create_chunks(doc_id, chunks_with_embeddings)

        # 6. Update document status
        await self.firestore.update_document_status(doc_id, "ready", len(chunks))

    async def list_documents(self, user_id: str) -> list[dict[str, Any]]:
        """List all documents for a user."""
        return await self.firestore.list_documents(user_id)

    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Get document by ID."""
        return await self.firestore.get_document(doc_id)

    async def delete_document(self, doc_id: str) -> None:
        """Delete document and its chunks."""
        doc = await self.firestore.get_document(doc_id)
        if doc:
            # Delete from storage
            await self.storage.delete_file(doc["storage_path"])
            # Delete from Firestore
            await self.firestore.delete_document(doc_id)


def get_document_service() -> DocumentService:
    """Get document service instance."""
    return DocumentService(
        firestore=get_firestore_client(),
        storage=get_storage_client(),
        gemini=get_gemini_client(),
        processor=get_document_processor(),
    )
