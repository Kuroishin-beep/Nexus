"""
src/agents/base_agent.py
─────────────────────────
Abstract base class for all agents.
Uses OpenRouter's OpenAI-compatible API so any free model can be swapped in
by changing a single config value — no code changes needed.

Free model fallback chain:
  default_model (DeepSeek R1) → fallback_model (Llama 3.3 70B)
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import settings
from src.core.exceptions import AgentError, ContextWindowExceededError, LLMTimeoutError
from src.core.logging import get_logger
from src.core.models import AgentRun, Message, Role, RunStatus, ToolCall, ToolResult
from src.tools.registry import ToolRegistry

logger = get_logger(__name__)

# OpenRouter requires these headers for usage tracking on free tier
_OPENROUTER_HEADERS = {
    "HTTP-Referer": settings.app_url,
    "X-Title": settings.app_name,
}


def _build_client(model: str | None = None) -> AsyncOpenAI:
    """Build an AsyncOpenAI client pointed at OpenRouter."""
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key.get_secret_value(),
        base_url=settings.openrouter_base_url,
        default_headers=_OPENROUTER_HEADERS,
        timeout=60.0,
    )


class BaseAgent(ABC):
    """
    Every agent extends this class.
    Subclasses implement `system_prompt` and optionally override model selection.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model or settings.default_model
        self.max_tokens = max_tokens
        self.tool_registry = tool_registry or ToolRegistry()
        self._client = _build_client()

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    # ── Public interface ──────────────────────────────────────

    async def run(self, user_message: str, context: dict[str, Any] | None = None) -> AgentRun:
        """Non-streaming run. Returns a completed AgentRun."""
        run = AgentRun()
        run.messages.append(Message(role=Role.USER, content=user_message))
        run.status = RunStatus.RUNNING

        try:
            await self._agentic_loop(run, context or {})
            run.status = RunStatus.SUCCESS
        except Exception as exc:
            run.status = RunStatus.FAILED
            run.error = str(exc)
            logger.error("agent_run_failed", run_id=str(run.id), error=str(exc))
            raise
        finally:
            from src.core.models import utcnow
            run.completed_at = utcnow()

        return run

    async def stream(
        self, user_message: str, context: dict[str, Any] | None = None
    ) -> AsyncIterator[str]:
        """Streaming run — yields text deltas."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._openrouter_tools(),
            max_tokens=self.max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    # ── Internal agentic loop ─────────────────────────────────

    async def _agentic_loop(self, run: AgentRun, context: dict[str, Any]) -> None:
        """Drive the tool-use loop until no more tool calls remain."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self._build_messages(run),
        ]

        for iteration in range(10):  # guard against infinite loops
            logger.debug("agent_loop_iteration", iteration=iteration, run_id=str(run.id))

            response = await self._call_llm(messages)
            choice = response.choices[0]
            msg = choice.message

            run.usage = {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            }

            # Collect text
            if msg.content:
                run.messages.append(Message(role=Role.ASSISTANT, content=msg.content))

            # Check for tool calls
            if not msg.tool_calls:
                break  # final answer

            tool_calls = []
            for tc in msg.tool_calls:
                import json
                parsed_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
                tool_call = ToolCall(id=tc.id, name=tc.function.name, input=parsed_input)
                tool_calls.append(tool_call)
                run.tool_calls.append(tool_call)

            # Execute tools
            tool_results = await self._execute_tools(tool_calls)
            run.tool_results.extend(tool_results)

            # Append assistant + tool results to conversation
            messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]})
            for result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": result.content,
                })

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_llm(self, messages: list[dict]) -> Any:
        try:
            return await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._openrouter_tools() or None,
                max_tokens=self.max_tokens,
            )
        except Exception as e:
            err = str(e).lower()
            if "timeout" in err:
                raise LLMTimeoutError("LLM request timed out") from e
            if "context" in err or "token" in err:
                raise ContextWindowExceededError("Context window exceeded") from e
            # On rate limit or 5xx, try fallback model
            if "rate" in err or "429" in err or "503" in err:
                logger.warning("llm_switching_to_fallback", model=self.model)
                self.model = settings.fallback_model
            raise AgentError(str(e)) from e

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        results = []
        for tc in tool_calls:
            logger.info("tool_executing", tool=tc.name, tool_call_id=tc.id)
            try:
                output = await self.tool_registry.execute(tc.name, tc.input)
                results.append(ToolResult(tool_call_id=tc.id, content=str(output)))
            except Exception as exc:
                logger.warning("tool_failed", tool=tc.name, error=str(exc))
                results.append(ToolResult(tool_call_id=tc.id, content=str(exc), is_error=True))
        return results

    def _build_messages(self, run: AgentRun) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in run.messages]

    def _openrouter_tools(self) -> list[dict]:
        """Convert registry tools to OpenAI-compatible function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in self.tool_registry.as_anthropic_tools()
        ]
