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

    async def upload_document_for_customer(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        customer_id: str,
        process_async: bool = True,
    ) -> dict[str, Any]:
        """
        Upload and process a document for a customer (multi-tenant).

        Args:
            file_content: Raw file bytes
            filename: Original filename
            content_type: MIME type
            customer_id: Owner customer ID
            process_async: If True, process in background and return immediately

        Returns:
            Document record
        """
        import asyncio

        print(f"[SERVICE] upload_document_for_customer: {filename}, {len(file_content)} bytes")

        # 1. Upload to Cloud Storage (use customer_id as folder)
        print("[SERVICE] Step 1: Uploading to Cloud Storage...")
        storage_path = await self.storage.upload_file(
            file_content=file_content,
            filename=filename,
            content_type=content_type,
            user_id=customer_id,
        )
        print(f"[SERVICE] Uploaded to: {storage_path}")

        # 2. Create document record with customer_id
        print("[SERVICE] Step 2: Creating Firestore document record...")
        doc_record = await self.firestore.create_document_for_customer(
            customer_id=customer_id,
            filename=filename,
            content_type=content_type,
            storage_path=storage_path,
        )
        print(f"[SERVICE] Created document: {doc_record.get('id')}")

        # 3. Process document (async or sync)
        if process_async:
            # Start background processing and return immediately
            print("[SERVICE] Starting background processing...")
            asyncio.create_task(self._process_document_background(
                doc_record["id"], file_content, content_type
            ))
            return doc_record
        else:
            # Process synchronously (for small files or testing)
            print("[SERVICE] Step 3: Processing document synchronously...")
            try:
                await self._process_document(doc_record["id"], file_content, content_type)
                print("[SERVICE] Processing complete!")
            except Exception as e:
                print(f"[SERVICE] Processing failed: {type(e).__name__}: {e}")
                import traceback
                print(traceback.format_exc())
                await self.firestore.update_document_status(doc_record["id"], "failed")
                raise e

            return doc_record

    async def _process_document_background(
        self,
        doc_id: str,
        file_content: bytes,
        content_type: str,
    ) -> None:
        """Background wrapper for document processing with error handling."""
        try:
            print(f"[SERVICE] Background processing started for {doc_id}")
            await self._process_document(doc_id, file_content, content_type)
            print(f"[SERVICE] Background processing complete for {doc_id}")
        except Exception as e:
            print(f"[SERVICE] Background processing failed for {doc_id}: {e}")
            import traceback
            print(traceback.format_exc())
            try:
                await self.firestore.update_document_status(doc_id, "failed")
            except Exception:
                pass

    async def _process_document(
        self,
        doc_id: str,
        file_content: bytes,
        content_type: str,
    ) -> None:
        """Process document: extract text, chunk, generate embeddings."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Update status to processing
            logger.info(f"[{doc_id}] Starting document processing...")
            await self.firestore.update_document_status(doc_id, "processing")

            # 1. Extract text
            logger.info(f"[{doc_id}] Extracting text from {content_type}...")
            text = await self.processor.extract_text(file_content, content_type)
            logger.info(f"[{doc_id}] Extracted {len(text)} characters")

            if not text.strip():
                raise ValueError("No text content extracted from document")

            # 2. Chunk text
            logger.info(f"[{doc_id}] Chunking text...")
            chunks = self.processor.chunk_text(text)
            logger.info(f"[{doc_id}] Created {len(chunks)} chunks")

            if not chunks:
                raise ValueError("No chunks generated from document")

            # 3. Generate embeddings
            logger.info(f"[{doc_id}] Generating embeddings for {len(chunks)} chunks...")
            chunk_texts = [c["text"] for c in chunks]

            # Validate chunk texts
            for i, ct in enumerate(chunk_texts):
                if not ct or not isinstance(ct, str):
                    logger.warning(f"[{doc_id}] Chunk {i} is invalid: {repr(ct)[:100]}")

            embeddings = await self.gemini.generate_embeddings_batch(chunk_texts)
            logger.info(f"[{doc_id}] Generated {len(embeddings)} embeddings")

            # Validate embeddings match chunks
            if len(embeddings) != len(chunks):
                raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(chunks)} chunks")

            # 4. Prepare chunks with embeddings
            logger.info(f"[{doc_id}] Preparing chunks with embeddings...")
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
            logger.info(f"[{doc_id}] Storing {len(chunks_with_embeddings)} chunks in Firestore...")
            await self.firestore.create_chunks(doc_id, chunks_with_embeddings)

            # 6. Update document status
            logger.info(f"[{doc_id}] Document processing complete!")
            await self.firestore.update_document_status(doc_id, "ready", len(chunks))

        except Exception as e:
            logger.error(f"[{doc_id}] Processing failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

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
