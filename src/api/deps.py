"""
src/api/deps.py
────────────────
FastAPI dependency providers.
Using functools.lru_cache on factory functions ensures singletons
are shared across requests (agents, clients, etc.).
"""

from functools import lru_cache

from fastapi import Depends

from src.agents.orchestrator import OrchestratorAgent
from src.tools.registry import registry


@lru_cache
def _get_orchestrator_singleton() -> OrchestratorAgent:
    return OrchestratorAgent(tool_registry=registry)


async def get_orchestrator() -> OrchestratorAgent:
    """Dependency: shared OrchestratorAgent instance."""
    return _get_orchestrator_singleton()
