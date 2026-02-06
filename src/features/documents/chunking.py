"""Pluggable chunking strategies for document processing."""

import re
from abc import ABC, abstractmethod

from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str) -> list[dict]:
        """Split text into chunks with metadata."""
        pass


class RecursiveChunking(ChunkingStrategy):
    """Default recursive character-based chunking."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk(self, text: str) -> list[dict]:
        chunks = self.splitter.split_text(text)
        return [
            {"text": chunk, "chunk_index": idx, "strategy": "recursive"}
            for idx, chunk in enumerate(chunks)
        ]


class SentenceChunking(ChunkingStrategy):
    """Sentence-based chunking for better semantic coherence."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[dict]:
        # Split into sentences (Czech-aware with common abbreviations)
        # Handle Czech sentence endings properly
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if current_length + len(sentence) > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": len(chunks),
                    "strategy": "sentence",
                })
                # Overlap: keep some sentences
                overlap_text = ""
                overlap_sentences = []
                while current_chunk and len(overlap_text) < self.chunk_overlap:
                    s = current_chunk.pop()
                    overlap_text = s + " " + overlap_text
                    overlap_sentences.insert(0, s)
                current_chunk = overlap_sentences
                current_length = len(overlap_text)

            current_chunk.append(sentence)
            current_length += len(sentence) + 1

        if current_chunk:
            chunks.append({
                "text": " ".join(current_chunk),
                "chunk_index": len(chunks),
                "strategy": "sentence",
            })

        return chunks


class SemanticChunking(ChunkingStrategy):
    """Semantic chunking based on paragraph boundaries."""

    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 1500):
        self.min_size = min_chunk_size
        self.max_size = max_chunk_size

    def chunk(self, text: str) -> list[dict]:
        # Split by paragraph (double newline)
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If single paragraph exceeds max, split it
            if len(para) > self.max_size:
                # Flush current chunk first
                if current_chunk:
                    chunks.append({
                        "text": "\n\n".join(current_chunk),
                        "chunk_index": len(chunks),
                        "strategy": "semantic",
                    })
                    current_chunk = []
                    current_length = 0

                # Split large paragraph by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_chunk = []
                temp_length = 0
                for sent in sentences:
                    if temp_length + len(sent) > self.max_size and temp_chunk:
                        chunks.append({
                            "text": " ".join(temp_chunk),
                            "chunk_index": len(chunks),
                            "strategy": "semantic",
                        })
                        temp_chunk = []
                        temp_length = 0
                    temp_chunk.append(sent)
                    temp_length += len(sent)
                if temp_chunk:
                    current_chunk = [" ".join(temp_chunk)]
                    current_length = temp_length
                continue

            if current_length + len(para) > self.max_size and current_chunk:
                chunks.append({
                    "text": "\n\n".join(current_chunk),
                    "chunk_index": len(chunks),
                    "strategy": "semantic",
                })
                current_chunk = []
                current_length = 0

            current_chunk.append(para)
            current_length += len(para)

        if current_chunk:
            chunks.append({
                "text": "\n\n".join(current_chunk),
                "chunk_index": len(chunks),
                "strategy": "semantic",
            })

        return chunks


def get_chunking_strategy(
    strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> ChunkingStrategy:
    """
    Factory function for chunking strategies.

    Args:
        strategy: 'recursive', 'sentence', or 'semantic'
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        ChunkingStrategy instance
    """
    strategies = {
        "recursive": lambda: RecursiveChunking(chunk_size, chunk_overlap),
        "sentence": lambda: SentenceChunking(chunk_size, chunk_overlap),
        "semantic": lambda: SemanticChunking(
            min_chunk_size=200,
            max_chunk_size=chunk_size
        ),
    }
    factory = strategies.get(strategy, strategies["recursive"])
    return factory()
