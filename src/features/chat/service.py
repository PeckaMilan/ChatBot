"""Chat service with RAG pipeline."""

from src.core.firestore import get_firestore_client
from src.core.gemini import GeminiClient, get_gemini_client
from src.utils.language import detect_language

from .memory import ConversationMemory, get_conversation_memory
from .models import ChatResponse, SourceReference
from .retrieval import RetrievalService, get_retrieval_service


class ChatService:
    """Service for chat with RAG."""

    def __init__(
        self,
        gemini: GeminiClient,
        retrieval: RetrievalService,
        memory: ConversationMemory,
    ):
        self.gemini = gemini
        self.retrieval = retrieval
        self.memory = memory

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
        document_ids: list[str] | None = None,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """
        Process a chat message with RAG.

        Args:
            message: User's message
            session_id: Session ID for conversation continuity
            document_ids: Document IDs to search in
            system_prompt: Custom system prompt

        Returns:
            Chat response with sources
        """
        # Generate or use provided session ID
        if not session_id:
            session_id = self.memory.generate_session_id()

        # Get or create conversation
        conversation = await self.memory.get_or_create_conversation(
            session_id=session_id,
            document_ids=document_ids,
        )

        # Detect language
        language = detect_language(message)

        # Retrieve relevant chunks
        chunks = await self.retrieval.search(
            query=message,
            document_ids=document_ids or conversation.get("document_ids"),
            top_k=5,
        )

        # Build context from chunks
        context = self.retrieval.build_context(chunks)

        # Get conversation history
        history = await self.memory.get_history(conversation["id"], limit=6)

        # Build system prompt
        default_prompt = "You are a helpful assistant. Answer questions based on the provided context. If the context doesn't contain relevant information, say so. Always respond in the same language as the user's question."
        final_prompt = system_prompt or default_prompt

        # Generate response
        response_text = await self.gemini.chat(
            message=message,
            system_prompt=final_prompt,
            context=context if context else None,
            history=history if history else None,
        )

        # Save messages to conversation
        await self.memory.add_message(
            conversation_id=conversation["id"],
            role="user",
            content=message,
        )

        # Prepare sources for response
        sources = [
            SourceReference(
                chunk_id=chunk["id"],
                text=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                score=chunk["score"],
                page_number=chunk.get("page_number"),
            )
            for chunk in chunks[:3]  # Top 3 sources
        ]

        await self.memory.add_message(
            conversation_id=conversation["id"],
            role="assistant",
            content=response_text,
            sources=[s.model_dump() for s in sources],
        )

        return ChatResponse(
            message=response_text,
            sources=sources,
            session_id=session_id,
            language=language,
        )


def get_chat_service() -> ChatService:
    """Get chat service instance."""
    return ChatService(
        gemini=get_gemini_client(),
        retrieval=get_retrieval_service(),
        memory=get_conversation_memory(),
    )
