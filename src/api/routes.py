"""
src/api/routes.py
──────────────────
All HTTP + SSE route definitions.

Routes:
  POST /agent/run         — synchronous agent run
  POST /agent/stream      — SSE streaming agent run
  GET  /tools             — list registered tools
  POST /tools/{name}      — execute a specific tool directly
  GET  /health            — health check
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from src.agents.orchestrator import OrchestratorAgent
from src.api.deps import get_orchestrator
from src.core.exceptions import AppError
from src.core.models import APIResponse
from src.tools.registry import registry

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────

class RunRequest(BaseModel):
    message: str
    context: dict[str, Any] | None = None


class ToolExecRequest(BaseModel):
    inputs: dict[str, Any]


# ── Agent endpoints ───────────────────────────────────────────

@router.post("/agent/run", response_model=APIResponse)
async def agent_run(
    req: RunRequest,
    agent: OrchestratorAgent = Depends(get_orchestrator),
) -> APIResponse:
    """Synchronous agent run. Blocks until the agent completes."""
    try:
        result = await agent.run_with_delegation(req.message, req.context)
        return APIResponse(data=result)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


@router.post("/agent/stream")
async def agent_stream(
    req: RunRequest,
    agent: OrchestratorAgent = Depends(get_orchestrator),
) -> EventSourceResponse:
    """Streaming SSE endpoint. Yields text deltas in real time."""

    async def event_generator():
        try:
            async for chunk in agent.stream(req.message, req.context):
                yield {"event": "delta", "data": json.dumps({"text": chunk})}
            yield {"event": "done", "data": json.dumps({"status": "complete"})}
        except AppError as e:
            yield {"event": "error", "data": json.dumps({"error": e.message})}

    return EventSourceResponse(event_generator())


# ── Tool endpoints ────────────────────────────────────────────

@router.get("/tools", response_model=APIResponse)
async def list_tools() -> APIResponse:
    """List all registered tools and their schemas."""
    return APIResponse(data=registry.as_anthropic_tools())


@router.post("/tools/{tool_name}", response_model=APIResponse)
async def execute_tool(tool_name: str, req: ToolExecRequest) -> APIResponse:
    """Directly invoke a tool by name."""
    try:
        result = await registry.execute(tool_name, req.inputs)
        return APIResponse(data=result)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e


# ── Health ────────────────────────────────────────────────────

@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "tools": registry.list_tools()}
