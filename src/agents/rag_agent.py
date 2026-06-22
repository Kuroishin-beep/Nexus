"""
src/agents/rag_agent.py
────────────────────────
RAG (Retrieval-Augmented Generation) agent.
Embeds the query, retrieves top-k chunks from ChromaDB,
injects them into context, then generates a grounded answer.
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.core.logging import get_logger
from src.utils.embeddings import EmbeddingService

logger = get_logger(__name__)

_RETRIEVAL_PREAMBLE = """You are a precise, knowledge-grounded assistant.
You have been provided retrieved context below.
Answer ONLY using the provided context. If the context is insufficient, say so.

--- RETRIEVED CONTEXT ---
{context}
--- END CONTEXT ---
"""


class RAGAgent(BaseAgent):
    """Agent that retrieves relevant documents before answering."""

    def __init__(self) -> None:
        super().__init__()
        self._embedding_svc = EmbeddingService()

    @property
    def system_prompt(self) -> str:
        # Dynamically injected per-run via _build_system_with_context
        return "You are a helpful knowledge assistant."

    def _build_system_with_context(self, context: str) -> str:
        return _RETRIEVAL_PREAMBLE.format(context=context)

    async def run(self, user_message: str, context: dict[str, Any] | None = None) -> Any:
        # Retrieve relevant chunks
        retrieved = await self._embedding_svc.query(user_message, top_k=5)
        context_text = "\n\n".join(
            f"[{i+1}] {chunk['text']}" for i, chunk in enumerate(retrieved)
        )
        logger.info("rag_retrieved", chunks=len(retrieved))

        # Override system prompt with retrieved context
        original_system = self.system_prompt
        self.__class__.system_prompt = property(  # type: ignore[assignment]
            lambda self: self._build_system_with_context(context_text)
        )

        try:
            result = await super().run(user_message, context)
        finally:
            # Restore original system prompt property
            self.__class__.system_prompt = property(lambda self: original_system)  # type: ignore[assignment]

        return result
