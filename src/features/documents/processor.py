"""Document text extraction and chunking."""

import io
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """Extract text from documents and split into chunks."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def extract_text(self, file_content: bytes, content_type: str) -> str:
        """
        Extract text from file content.

        Args:
            file_content: Raw file bytes
            content_type: MIME type of the file

        Returns:
            Extracted text
        """
        if content_type == "application/pdf":
            return self._extract_pdf(file_content)
        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            return self._extract_docx(file_content)
        elif content_type in ["text/plain", "text/markdown"]:
            return file_content.decode("utf-8")
        else:
            raise ValueError(f"Unsupported content type: {content_type}")

    def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF."""
        text_parts = []
        with fitz.open(stream=content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
        return "\n\n".join(text_parts)

    def _extract_docx(self, content: bytes) -> str:
        """Extract text from DOCX."""
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            doc = Document(tmp_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def chunk_text(self, text: str) -> list[dict]:
        """
        Split text into chunks with metadata.

        Args:
            text: Full document text

        Returns:
            List of chunk dicts with text and metadata
        """
        chunks = self.splitter.split_text(text)
        return [
            {
                "text": chunk,
                "chunk_index": idx,
                "page_number": self._detect_page_number(chunk),
            }
            for idx, chunk in enumerate(chunks)
        ]

    def _detect_page_number(self, chunk: str) -> int | None:
        """Try to detect page number from chunk content."""
        import re

        match = re.search(r"\[Page (\d+)\]", chunk)
        if match:
            return int(match.group(1))
        return None


def get_document_processor() -> DocumentProcessor:
    """Get document processor instance."""
    return DocumentProcessor()
