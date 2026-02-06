"""Gemini API client using Vertex AI (no rate limits)."""

import vertexai
from vertexai.generative_models import GenerativeModel, Part, Content
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

from src.config import get_settings


class GeminiClient:
    """Wrapper for Gemini API operations using Vertex AI."""

    _instance: "GeminiClient | None" = None
    _model: GenerativeModel | None = None
    _initialized: bool = False

    # Configuration - use settings or default
    REGION = "europe-west1"

    @property
    def project_id(self) -> str:
        """Get project ID from settings or environment."""
        settings = get_settings()
        return settings.google_cloud_project or "chatbot-platform-2026"

    # Model configuration - using Vertex AI models
    CHAT_MODEL = "gemini-3-flash-preview"
    EMBEDDING_MODEL = "text-embedding-004"
    EMBEDDING_DIMENSIONS = 768

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self) -> None:
        """Initialize Vertex AI if not already done."""
        if not self._initialized:
            try:
                vertexai.init(project=self.project_id, location=self.REGION)
                self._initialized = True
            except Exception as e:
                raise RuntimeError(f"Vertex AI initialization failed: {e}")

    @property
    def model(self) -> GenerativeModel:
        """Get or create Gemini model."""
        self._ensure_initialized()
        if self._model is None:
            self._model = GenerativeModel(self.CHAT_MODEL)
        return self._model

    async def chat(
        self,
        message: str,
        system_prompt: str | None = None,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
    ) -> str:
        """
        Generate a chat response.

        Args:
            message: User's message
            system_prompt: System instructions for the model
            context: Retrieved context from documents (RAG)
            history: Previous conversation messages
            model_id: Specific Gemini model to use (defaults to CHAT_MODEL)

        Returns:
            Model's response text
        """
        self._ensure_initialized()

        # Build system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        # Use specified model or default
        chat_model = model_id or self.CHAT_MODEL

        # Create model with system instruction
        model = GenerativeModel(
            chat_model,
            system_instruction=system_instruction,
        )

        # Build contents from history
        contents = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

        # Add current message
        contents.append(Content(role="user", parts=[Part.from_text(message)]))

        # Generate response
        response = model.generate_content(
            contents,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2048,
            }
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
        """
        Generate a streaming chat response.

        Yields chunks of text as they are generated.
        """
        self._ensure_initialized()

        # Build system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        # Use specified model or default
        chat_model = model_id or self.CHAT_MODEL

        # Create model with system instruction
        model = GenerativeModel(
            chat_model,
            system_instruction=system_instruction,
        )

        # Build contents from history
        contents = []
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(Content(role=role, parts=[Part.from_text(msg["content"])]))

        # Add current message
        contents.append(Content(role="user", parts=[Part.from_text(message)]))

        # Generate streaming response
        response = model.generate_content(
            contents,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2048,
            },
            stream=True,
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text using Vertex AI.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)
        """
        from vertexai.language_models import TextEmbeddingModel

        self._ensure_initialized()

        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings([text])

        return embeddings[0].values

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        import logging
        from vertexai.language_models import TextEmbeddingModel

        logger = logging.getLogger(__name__)

        self._ensure_initialized()

        if not texts:
            return []

        logger.info(f"Generating embeddings for {len(texts)} texts")
        model = TextEmbeddingModel.from_pretrained("text-embedding-004")

        # Process in small batches to avoid token limit (20k tokens per request)
        all_embeddings = []
        batch_size = 5  # Small batch to stay under 20k token limit

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1}, texts {i} to {i + len(batch)}")

            # Sanitize batch: ensure strings, truncate long texts, replace empty with placeholder
            sanitized_batch = []
            for j, t in enumerate(batch):
                try:
                    if t is None:
                        sanitized_batch.append("[empty]")
                    elif not isinstance(t, str):
                        # Convert to string if possible
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
                # If batch fails, try one by one
                for j, text in enumerate(sanitized_batch):
                    try:
                        emb = model.get_embeddings([text])
                        all_embeddings.append(emb[0].values)
                    except Exception as single_err:
                        logger.error(f"Single embedding failed for text {i + j}: {single_err}")
                        # Use zero vector as fallback
                        all_embeddings.append([0.0] * self.EMBEDDING_DIMENSIONS)

        logger.info(f"Finished: generated {len(all_embeddings)} total embeddings")
        return all_embeddings


def get_gemini_client() -> GeminiClient:
    """Get Gemini client instance (dependency injection)."""
    return GeminiClient()
