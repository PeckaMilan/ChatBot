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

    # Configuration
    PROJECT_ID = "glassy-polymer-477908-g9"
    REGION = "europe-west1"

    # Model configuration - using Vertex AI models
    CHAT_MODEL = "gemini-2.0-flash-001"
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
                vertexai.init(project=self.PROJECT_ID, location=self.REGION)
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
    ) -> str:
        """
        Generate a chat response.

        Args:
            message: User's message
            system_prompt: System instructions for the model
            context: Retrieved context from documents (RAG)
            history: Previous conversation messages

        Returns:
            Model's response text
        """
        self._ensure_initialized()

        # Build system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        # Create model with system instruction
        model = GenerativeModel(
            self.CHAT_MODEL,
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
        from vertexai.language_models import TextEmbeddingModel

        self._ensure_initialized()

        model = TextEmbeddingModel.from_pretrained("text-embedding-004")

        # Process in batches of 250 (Vertex AI limit)
        all_embeddings = []
        batch_size = 250

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = model.get_embeddings(batch)
            all_embeddings.extend([e.values for e in embeddings])

        return all_embeddings


def get_gemini_client() -> GeminiClient:
    """Get Gemini client instance (dependency injection)."""
    return GeminiClient()
