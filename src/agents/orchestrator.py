"""
src/agents/orchestrator.py
───────────────────────────
Orchestrator agent: routes tasks to specialised sub-agents,
aggregates their results, and produces a unified final answer.
"""

from typing import Any

from src.agents.base_agent import BaseAgent
from src.agents.rag_agent import RAGAgent
from src.core.logging import get_logger
from src.core.models import AgentRun
from src.tools.registry import ToolRegistry

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Top-level agent that decomposes complex tasks and delegates
    to specialist agents (RAG, code execution, web search, etc.).
    """

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        super().__init__(tool_registry=tool_registry)
        self._rag_agent = RAGAgent()

    @property
    def system_prompt(self) -> str:
        return """You are an expert AI orchestrator. Your job is to:

1. Analyse the user's request and break it into sub-tasks.
2. Delegate sub-tasks to the appropriate specialist tool or agent.
3. Synthesise results into a coherent, accurate final answer.

Available specialists:
- **rag_search**: Retrieve relevant documents from the knowledge base.
- **web_search**: Search the internet for up-to-date information.
- **code_exec**: Execute Python code in a sandboxed environment.
- **file_ops**: Read, write, and transform files.

Always cite your sources. Be concise and accurate."""

    async def run_with_delegation(
        self, user_message: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Extended run that first queries the RAG agent for context,
        then passes enriched context to the main orchestrator loop.
        """
        ctx = context or {}

        # 1. Retrieve relevant context from vector store
        rag_run: AgentRun = await self._rag_agent.run(user_message)
        rag_context = rag_run.messages[-1].content if rag_run.messages else ""

        if rag_context:
            ctx["retrieved_context"] = rag_context
            logger.info("orchestrator_rag_context_retrieved", chars=len(rag_context))

        # 2. Run main loop with enriched context
        run = await self.run(user_message, context=ctx)

        return {
            "run_id": str(run.id),
            "status": run.status,
            "answer": run.messages[-1].content if run.messages else "",
            "tool_calls": [tc.model_dump() for tc in run.tool_calls],
            "usage": run.usage,
        }
