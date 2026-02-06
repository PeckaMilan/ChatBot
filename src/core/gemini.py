"""Gemini API client using google-genai SDK."""

import logging

import vertexai
from google import genai
from google.genai import types
from vertexai.language_models import TextEmbeddingModel

from src.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Wrapper for Gemini API operations."""

    _instance: "GeminiClient | None" = None
    _client: genai.Client | None = None
    _vertexai_initialized: bool = False

    CHAT_MODEL = "gemini-3-flash-preview"
    EMBEDDING_MODEL = "text-embedding-004"
    EMBEDDING_DIMENSIONS = 768
    REGION = "europe-west1"

    @property
    def project_id(self) -> str:
        settings = get_settings()
        return settings.google_cloud_project or "chatbot-platform-2026"

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> genai.Client:
        """Get or create google-genai client with Vertex AI auth."""
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location="global",
            )
        return self._client

    def _ensure_vertexai(self) -> None:
        """Initialize Vertex AI for embeddings (still uses vertexai SDK)."""
        if not self._vertexai_initialized:
            vertexai.init(project=self.project_id, location=self.REGION)
            self._vertexai_initialized = True

    async def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
    ) -> str:
        """Generate a chat response."""
        chat_model = model_id or self.CHAT_MODEL

        # Build system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        print(f"[GEMINI] Model={chat_model} Prompt={system_instruction[:80]}...")

        # Build contents from history
        contents = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )

        # Add current message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            )
        )

        response = self.client.models.generate_content(
            model=chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )

        return response.text

    async def chat_stream(
        self,
        message: str,
        system_prompt: str | None = None,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
    ):
        """Generate a streaming chat response. Yields text chunks."""
        chat_model = model_id or self.CHAT_MODEL

        # Build system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        # Build contents from history
        contents = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)],
            )
        )

        response = self.client.models.generate_content_stream(
            model=chat_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        self._ensure_vertexai()
        model = TextEmbeddingModel.from_pretrained(self.EMBEDDING_MODEL)
        embeddings = model.get_embeddings([text])
        return embeddings[0].values

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        self._ensure_vertexai()

        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")
        model = TextEmbeddingModel.from_pretrained(self.EMBEDDING_MODEL)

        all_embeddings = []
        batch_size = 5

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}, texts {i} to {i + len(batch)}")

            sanitized_batch = []
            for j, t in enumerate(batch):
                try:
                    if t is None:
                        sanitized_batch.append("[empty]")
                    elif not isinstance(t, str):
                        sanitized_batch.append(str(t)[:8000] if t else "[empty]")
                    elif len(t) == 0:
                        sanitized_batch.append("[empty]")
                    elif len(t) > 8000:
                        sanitized_batch.append(t[:8000])
                    else:
                        sanitized_batch.append(t)
                except Exception as sanitize_err:
                    logger.error(f"Error sanitizing text {i + j}: {sanitize_err}")
                    sanitized_batch.append("[error]")

            try:
                embeddings = model.get_embeddings(sanitized_batch)
                all_embeddings.extend([e.values for e in embeddings])
                logger.info(f"Batch {i // batch_size + 1} succeeded: {len(embeddings)} embeddings")
            except Exception as e:
                logger.warning(f"Batch {i // batch_size + 1} failed: {e}, trying one by one")
                for j, text in enumerate(sanitized_batch):
                    try:
                        emb = model.get_embeddings([text])
                        all_embeddings.append(emb[0].values)
                    except Exception as single_err:
                        logger.error(f"Single embedding failed for text {i + j}: {single_err}")
                        all_embeddings.append([0.0] * self.EMBEDDING_DIMENSIONS)

        logger.info(f"Finished: generated {len(all_embeddings)} total embeddings")
        return all_embeddings


def get_gemini_client() -> GeminiClient:
    """Get Gemini client instance (dependency injection)."""
    return GeminiClient()
