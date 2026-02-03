"""Vector similarity search for RAG."""

import numpy as np

from src.core.firestore import FirestoreClient, get_firestore_client
from src.core.gemini import GeminiClient, get_gemini_client


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


class RetrievalService:
    """Service for retrieving relevant document chunks."""

    def __init__(
        self,
        firestore: FirestoreClient,
        gemini: GeminiClient,
    ):
        self.firestore = firestore
        self.gemini = gemini

    async def search(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> list[dict]:
        """
        Search for relevant chunks using vector similarity.

        Args:
            query: Search query
            document_ids: Optional list of document IDs to search in
            top_k: Number of results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of chunks with scores
        """
        # Generate query embedding
        query_embedding = await self.gemini.generate_embedding(query)

        # Get all chunks from specified documents (or all)
        chunks = await self.firestore.get_all_chunks(document_ids)

        if not chunks:
            return []

        # Calculate similarity scores
        results = []
        for chunk in chunks:
            if "embedding" not in chunk or not chunk["embedding"]:
                continue

            score = cosine_similarity(query_embedding, chunk["embedding"])

            if score >= min_score:
                results.append(
                    {
                        "id": chunk["id"],
                        "document_id": chunk["document_id"],
                        "text": chunk["text"],
                        "chunk_index": chunk["chunk_index"],
                        "page_number": chunk.get("page_number"),
                        "score": score,
                    }
                )

        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def build_context(self, chunks: list[dict], max_tokens: int = 4000) -> str:
        """
        Build context string from retrieved chunks.

        Args:
            chunks: Retrieved chunks with scores
            max_tokens: Approximate max tokens for context

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars

        for chunk in chunks:
            chunk_text = chunk["text"]
            if total_chars + len(chunk_text) > max_chars:
                break

            context_parts.append(f"[Source {chunk['chunk_index'] + 1}]\n{chunk_text}")
            total_chars += len(chunk_text)

        return "\n\n---\n\n".join(context_parts)


def get_retrieval_service() -> RetrievalService:
    """Get retrieval service instance."""
    return RetrievalService(
        firestore=get_firestore_client(),
        gemini=get_gemini_client(),
    )
