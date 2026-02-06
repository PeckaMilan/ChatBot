"""Scraper service for web content ingestion."""

from datetime import datetime
from typing import Any

import httpx

from src.core.firestore import FirestoreClient, get_firestore_client
from src.core.gemini import GeminiClient, get_gemini_client
from src.features.documents.chunking import get_chunking_strategy

from .extractor import HTMLExtractor
from .sitemap import SitemapParser
from .models import ScrapeRequest, ScrapeResult


class ScraperService:
    """Service for web scraping and RAG ingestion."""

    def __init__(
        self,
        firestore: FirestoreClient,
        gemini: GeminiClient,
    ):
        self.firestore = firestore
        self.gemini = gemini
        self.extractor = HTMLExtractor()
        self.sitemap_parser = SitemapParser()

    async def scrape_url(self, url: str) -> ScrapeResult:
        """
        Scrape a single URL and extract content.

        Args:
            url: URL to scrape

        Returns:
            Extracted content
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=30.0,
                follow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; ChatBot-Scraper/1.0)',
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'cs,en;q=0.9',
                },
            )
            response.raise_for_status()

        extracted = self.extractor.extract(response.text, url)

        return ScrapeResult(
            url=url,
            title=extracted['title'],
            content=extracted['content'],
            word_count=extracted['word_count'],
            scraped_at=datetime.utcnow(),
        )

    async def scrape_and_ingest(
        self,
        request: ScrapeRequest,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """
        Scrape URL(s) and add to RAG knowledge base.

        Args:
            request: Scrape configuration
            user_id: Owner user ID

        Returns:
            Ingestion result with document IDs
        """
        urls_to_scrape = []

        if request.scrape_type == "sitemap":
            # Find and parse sitemap
            sitemap_url = await self.sitemap_parser.find_sitemap(str(request.url))
            if sitemap_url:
                urls_to_scrape = await self.sitemap_parser.parse(
                    sitemap_url,
                    request.max_pages,
                )
            else:
                # Fallback to single URL
                urls_to_scrape = [str(request.url)]
        else:
            urls_to_scrape = [str(request.url)]

        # Filter URLs by patterns
        if request.include_patterns:
            urls_to_scrape = [
                u for u in urls_to_scrape
                if any(p in u for p in request.include_patterns)
            ]
        if request.exclude_patterns:
            urls_to_scrape = [
                u for u in urls_to_scrape
                if not any(p in u for p in request.exclude_patterns)
            ]

        # Scrape and ingest each URL
        results = []
        for url in urls_to_scrape[:request.max_pages]:
            try:
                result = await self._scrape_and_store(
                    url,
                    user_id,
                    request.chunking_strategy,
                )
                results.append(result)
            except Exception as e:
                results.append({"url": url, "error": str(e)})

        return {
            "total_urls": len(urls_to_scrape),
            "processed": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "results": results,
        }

    async def scrape_and_ingest_for_customer(
        self,
        request: ScrapeRequest,
        customer_id: str,
    ) -> dict[str, Any]:
        """
        Scrape URL(s) and add to customer's RAG knowledge base.

        Args:
            request: Scrape configuration
            customer_id: Owner customer ID

        Returns:
            Ingestion result with document IDs
        """
        urls_to_scrape = []

        if request.scrape_type == "sitemap":
            sitemap_url = await self.sitemap_parser.find_sitemap(str(request.url))
            if sitemap_url:
                urls_to_scrape = await self.sitemap_parser.parse(
                    sitemap_url,
                    request.max_pages,
                )
            else:
                urls_to_scrape = [str(request.url)]
        else:
            urls_to_scrape = [str(request.url)]

        if request.include_patterns:
            urls_to_scrape = [
                u for u in urls_to_scrape
                if any(p in u for p in request.include_patterns)
            ]
        if request.exclude_patterns:
            urls_to_scrape = [
                u for u in urls_to_scrape
                if not any(p in u for p in request.exclude_patterns)
            ]

        results = []
        for url in urls_to_scrape[:request.max_pages]:
            try:
                result = await self._scrape_and_store_for_customer(
                    url,
                    customer_id,
                    request.chunking_strategy,
                )
                results.append(result)
            except Exception as e:
                results.append({"url": url, "error": str(e)})

        return {
            "total_urls": len(urls_to_scrape),
            "processed": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r]),
            "results": results,
        }

    async def _scrape_and_store_for_customer(
        self,
        url: str,
        customer_id: str,
        chunking_strategy: str = "semantic",
    ) -> dict[str, Any]:
        """Scrape URL and store as document for customer."""
        result = await self.scrape_url(url)

        if not result.content or result.word_count < 50:
            raise ValueError("Insufficient content extracted")

        doc_ref = self.firestore.db.collection("documents").document()
        doc_data = {
            "id": doc_ref.id,
            "customer_id": customer_id,
            "user_id": customer_id,
            "filename": f"web: {result.title or url[:50]}",
            "content_type": "text/html",
            "storage_path": url,
            "source_type": "web",
            "source_url": url,
            "title": result.title,
            "word_count": result.word_count,
            "status": "processing",
            "chunk_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "scraped_at": result.scraped_at,
        }
        doc_ref.set(doc_data)

        chunker = get_chunking_strategy(
            strategy=chunking_strategy,
            chunk_size=1000,
            chunk_overlap=200,
        )
        chunks = chunker.chunk(result.content)

        if not chunks:
            raise ValueError("No chunks generated from content")

        chunk_texts = [c["text"] for c in chunks]
        embeddings = await self.gemini.generate_embeddings_batch(chunk_texts)

        batch = self.firestore.db.batch()
        for i, chunk in enumerate(chunks):
            chunk_ref = doc_ref.collection("chunks").document()
            chunk_data = {
                "id": chunk_ref.id,
                "document_id": doc_ref.id,
                "text": chunk["text"],
                "embedding": embeddings[i],
                "chunk_index": chunk["chunk_index"],
                "metadata": {"source_url": url, "strategy": chunk.get("strategy")},
            }
            batch.set(chunk_ref, chunk_data)

        batch.commit()

        doc_ref.update({
            "status": "ready",
            "chunk_count": len(chunks),
            "updated_at": datetime.utcnow(),
        })

        return {
            "document_id": doc_ref.id,
            "url": url,
            "title": result.title,
            "word_count": result.word_count,
            "chunks": len(chunks),
        }

    async def _scrape_and_store(
        self,
        url: str,
        user_id: str,
        chunking_strategy: str = "semantic",
    ) -> dict[str, Any]:
        """Scrape URL and store as document."""
        # Scrape content
        result = await self.scrape_url(url)

        if not result.content or result.word_count < 50:
            raise ValueError("Insufficient content extracted")

        # Create document record
        doc_ref = self.firestore.db.collection("documents").document()
        doc_data = {
            "id": doc_ref.id,
            "user_id": user_id,
            "filename": f"web: {result.title or url[:50]}",
            "content_type": "text/html",
            "storage_path": url,
            "source_type": "web",
            "source_url": url,
            "title": result.title,
            "word_count": result.word_count,
            "status": "processing",
            "chunk_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "scraped_at": result.scraped_at,
        }
        doc_ref.set(doc_data)

        # Chunk content
        chunker = get_chunking_strategy(
            strategy=chunking_strategy,
            chunk_size=1000,
            chunk_overlap=200,
        )
        chunks = chunker.chunk(result.content)

        if not chunks:
            raise ValueError("No chunks generated from content")

        # Generate embeddings
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await self.gemini.generate_embeddings_batch(chunk_texts)

        # Prepare chunks with embeddings
        batch = self.firestore.db.batch()
        for i, chunk in enumerate(chunks):
            chunk_ref = doc_ref.collection("chunks").document()
            chunk_data = {
                "id": chunk_ref.id,
                "document_id": doc_ref.id,
                "text": chunk["text"],
                "embedding": embeddings[i],
                "chunk_index": chunk["chunk_index"],
                "metadata": {"source_url": url, "strategy": chunk.get("strategy")},
            }
            batch.set(chunk_ref, chunk_data)

        batch.commit()

        # Update document status
        doc_ref.update({
            "status": "ready",
            "chunk_count": len(chunks),
            "updated_at": datetime.utcnow(),
        })

        return {
            "document_id": doc_ref.id,
            "url": url,
            "title": result.title,
            "word_count": result.word_count,
            "chunks": len(chunks),
        }

    async def list_scraped_documents(self, user_id: str = "default") -> list[dict]:
        """List all scraped web documents."""
        docs = (
            self.firestore.db.collection("documents")
            .where("source_type", "==", "web")
            .order_by("created_at", direction="DESCENDING")
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    async def delete_scraped_document(self, doc_id: str) -> None:
        """Delete a scraped document and its chunks."""
        doc_ref = self.firestore.db.collection("documents").document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise ValueError("Document not found")

        # Delete chunks
        chunks = doc_ref.collection("chunks").stream()
        for chunk in chunks:
            chunk.reference.delete()

        # Delete document
        doc_ref.delete()


def get_scraper_service() -> ScraperService:
    """Get scraper service instance."""
    return ScraperService(
        firestore=get_firestore_client(),
        gemini=get_gemini_client(),
    )
