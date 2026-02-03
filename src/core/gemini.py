"""Gemini API client for chat and embeddings."""

from google import genai
from google.genai import types

from src.config import get_settings


class GeminiClient:
    """Wrapper for Gemini API operations."""

    _instance: "GeminiClient | None" = None
    _client: genai.Client | None = None

    # Model configuration
    CHAT_MODEL = "gemini-2.0-flash"
    EMBEDDING_MODEL = "text-embedding-004"
    EMBEDDING_DIMENSIONS = 768

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> genai.Client:
        """Get or create Gemini client."""
        if self._client is None:
            settings = get_settings()
            self._client = genai.Client(api_key=settings.google_api_key)
        return self._client

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
        # Build the prompt
        contents = []

        # Add system instruction
        system_instruction = system_prompt or "You are a helpful assistant."
        if context:
            system_instruction += f"\n\nUse the following context to answer questions:\n\n{context}"

        # Add conversation history
        if history:
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

        # Add current message
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        # Generate response
        response = self.client.models.generate_content(
            model=self.CHAT_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
                max_output_tokens=2048,
            ),
        )

        return response.text

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)
        """
        response = self.client.models.embed_content(
            model=self.EMBEDDING_MODEL,
            content=text,
        )
        return response.embeddings[0].values

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        # Process in batches to avoid rate limits
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)

        return embeddings


def get_gemini_client() -> GeminiClient:
    """Get Gemini client instance (dependency injection)."""
    return GeminiClient()
