"""Hybrid search (vector + BM25 keyword) for RAG."""

import logging
import re

import numpy as np

from src.core.firestore import FirestoreClient, get_firestore_client
from src.core.gemini import GeminiClient, get_gemini_client

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi

    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    logger.warning(
        "rank-bm25 not available - hybrid search disabled, vector-only fallback"
    )

# Common Czech stopwords (filtered from BM25 tokenization)
_STOPWORDS = frozenset({
    "a", "v", "s", "na", "to", "je", "z", "o", "k", "i", "se", "do",
    "za", "od", "po", "pro", "ale", "by", "tak", "si", "co", "jak",
    "ze", "ve", "the", "is", "and", "of", "in", "to", "for", "it",
})


def _tokenize(text: str) -> list[str]:
    """Tokenize text with punctuation removal and stopword filtering."""
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


class RetrievalService:
    """Service for retrieving relevant document chunks using hybrid search."""

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
        Search for relevant chunks using hybrid vector + BM25 keyword search.

        Uses Reciprocal Rank Fusion (RRF) to combine vector similarity and
        BM25 keyword scores. Falls back to vector-only if BM25 unavailable.

        Args:
            query: Search query
            document_ids: Optional list of document IDs to search in
            top_k: Number of results to return
            min_score: Minimum vector similarity threshold

        Returns:
            List of chunks with scores, ranked by RRF
        """
        # Generate query embedding
        query_embedding = await self.gemini.generate_embedding(query)

        # Get all chunks from specified documents (or all)
        chunks = await self.firestore.get_all_chunks(document_ids)

        if not chunks:
            return []

        # Calculate vector similarity for all chunks
        scored_chunks = []
        for chunk in chunks:
            if "embedding" not in chunk or not chunk["embedding"]:
                continue

            vector_score = cosine_similarity(query_embedding, chunk["embedding"])
            scored_chunks.append(
                {
                    "id": chunk["id"],
                    "document_id": chunk["document_id"],
                    "text": chunk["text"],
                    "chunk_index": chunk["chunk_index"],
                    "page_number": chunk.get("page_number"),
                    "vector_score": vector_score,
                }
            )

        if not scored_chunks:
            return []

        # Hybrid search with BM25 if available
        if HAS_BM25 and len(scored_chunks) > 1:
            results = self._hybrid_rrf_search(
                scored_chunks, query, min_score
            )
        else:
            # Vector-only fallback
            results = [
                {**c, "score": c["vector_score"]}
                for c in scored_chunks
                if c["vector_score"] >= min_score
            ]

        results.sort(key=lambda x: x["score"], reverse=True)

        # Remove internal scoring fields
        for r in results:
            r.pop("vector_score", None)
            r.pop("bm25_score", None)

        return results[:top_k]

    def _hybrid_rrf_search(
        self,
        scored_chunks: list[dict],
        query: str,
        min_score: float,
    ) -> list[dict]:
        """Combine vector and BM25 scores using Reciprocal Rank Fusion."""
        # BM25 keyword scoring (with proper tokenization)
        corpus = [_tokenize(c["text"]) for c in scored_chunks]
        bm25 = BM25Okapi(corpus)
        query_tokens = _tokenize(query)
        bm25_scores = bm25.get_scores(query_tokens)

        for i, chunk in enumerate(scored_chunks):
            chunk["bm25_score"] = float(bm25_scores[i])

        # Rank independently by each method
        vector_ranked = sorted(
            range(len(scored_chunks)),
            key=lambda i: scored_chunks[i]["vector_score"],
            reverse=True,
        )
        bm25_ranked = sorted(
            range(len(scored_chunks)),
            key=lambda i: scored_chunks[i]["bm25_score"],
            reverse=True,
        )

        # Reciprocal Rank Fusion (k=60 is standard)
        k = 60
        rrf_scores: dict[str, float] = {}
        for rank, idx in enumerate(vector_ranked):
            chunk_id = scored_chunks[idx]["id"]
            rrf_scores[chunk_id] = 1.0 / (k + rank + 1)
        for rank, idx in enumerate(bm25_ranked):
            chunk_id = scored_chunks[idx]["id"]
            rrf_scores[chunk_id] = (
                rrf_scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            )

        # Apply RRF scores and filter
        results = []
        for chunk in scored_chunks:
            chunk["score"] = rrf_scores.get(chunk["id"], 0)
            # Include if vector passes threshold OR strong keyword match
            # with at least weak semantic relevance
            has_vector_match = chunk["vector_score"] >= min_score
            has_keyword_match = (
                chunk["bm25_score"] > 0 and chunk["vector_score"] >= 0.2
            )
            if has_vector_match or has_keyword_match:
                results.append(chunk)

        return results

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
