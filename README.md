# Nexus

> The connective core for your AI stack.

Nexus is a production-ready Python monorepo for building and deploying AI agent systems. It wires together multi-agent orchestration, retrieval-augmented generation, MCP tool servers, a streaming FastAPI, and a full GitHub Actions CI/CD pipeline — so you can skip the boilerplate and ship.

**Mission:** Eliminate the 3-month setup tax on every AI project. Every developer building a production AI app has to solve the same ten problems before writing a single line of business logic — reliable LLM calls, tool use, streaming, memory, deployment, monitoring. Nexus solves all ten up front.

**Model-agnostic by design.** Ships with Claude by default, but swapping to any free [OpenRouter](https://openrouter.ai) model takes one line in `.env`. Recommended free models (June 2026):

| Model ID | Strengths | Context |
|---|---|---|
| `google/gemma-4-31b-it:free` | Best overall reasoning, vision | 262K |
| `qwen/qwen3-coder:free` | Best free coding model | 1M |
| `nvidia/nemotron-3-super-120b-a12b:free` | Strong general purpose | 1M |
| `meta-llama/llama-3.3-70b-instruct:free` | Most widely tested | 131K |

Free tier: 20 req/min · 200 req/day · no credit card required.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **LLM** | Anthropic Claude (Sonnet / Haiku) | Core reasoning, tool use, generation |
| **Agent Framework** | Custom async Python | Orchestrator + RAG agents with tool-call loop |
| **MCP** | `mcp` SDK (Anthropic) | Expose tools to Claude Desktop + external agents |
| **API** | FastAPI + Uvicorn | REST + SSE streaming endpoints |
| **Vector Store** | ChromaDB | Semantic search for RAG |
| **Embeddings** | sentence-transformers (`all-MiniLM-L6-v2`) | Chunk embedding |
| **Tokenisation** | tiktoken (`cl100k_base`) | Token-aware text chunking |
| **Config** | pydantic-settings | Type-safe env var management |
| **Logging** | structlog + OTEL | Structured JSON logs with trace context |
| **Tracing** | OpenTelemetry + Jaeger | Distributed tracing |
| **Caching** | Redis | Response cache + future task queue |
| **Database** | PostgreSQL + asyncpg | Persistent run storage |
| **Retries** | tenacity | Exponential back-off on LLM calls |
| **HTTP client** | httpx | Async HTTP for tools and MCP client |
| **Testing** | pytest + pytest-asyncio | Unit + integration + e2e suites |
| **Linting** | Ruff | Fast Python linter + formatter |
| **Type checking** | mypy (strict) | Static type safety |
| **Containerisation** | Docker (multi-stage) | Minimal runtime image |
| **Orchestration** | Kubernetes | Deployment, HPA, rolling updates |
| **CI/CD** | GitHub Actions | Lint → test → build → deploy pipeline |
| **Eval pipeline** | Custom harness | Nightly LLM regression evals |

---

## Folder Structure

```
nexus/
│
├── .github/
│   └── workflows/
│       ├── ci.yml          # Lint → unit tests → integration tests → Docker build
│       ├── cd.yml          # Build → push GHCR → deploy staging → deploy production
│       └── eval.yml        # Nightly LLM eval suite with PR comment reporting
│
├── src/
│   ├── agents/
│   │   ├── base_agent.py       # Abstract base: agentic loop, retries, tool dispatch
│   │   ├── orchestrator.py     # Top-level agent: task decomposition + delegation
│   │   └── rag_agent.py        # RAG agent: embed → retrieve → generate
│   │
│   ├── tools/
│   │   ├── registry.py         # Global tool registry + Anthropic schema converter
│   │   ├── web_search.py       # Web search tool (Brave / DuckDuckGo)
│   │   ├── code_exec.py        # Sandboxed Python execution tool
│   │   └── file_ops.py         # Workspace-scoped file read/write/list tools
│   │
│   ├── mcp/
│   │   ├── server.py           # MCP server (stdio transport) — run standalone
│   │   ├── client.py           # Async MCP client for calling remote servers
│   │   ├── handlers.py         # HTTP+SSE transport bridge for MCP
│   │   └── schemas.py          # Pydantic schemas for MCP request/response
│   │
│   ├── api/
│   │   ├── main.py             # FastAPI app factory + lifespan hooks
│   │   ├── routes.py           # All HTTP + SSE route handlers
│   │   ├── middleware.py       # Request logging + error handling middleware
│   │   └── deps.py             # FastAPI dependency injection providers
│   │
│   ├── core/
│   │   ├── config.py           # pydantic-settings: all env vars, single source of truth
│   │   ├── logging.py          # structlog + OTEL trace context injection
│   │   ├── exceptions.py       # Domain exception hierarchy (AgentError, ToolError…)
│   │   └── models.py           # Shared Pydantic models: Message, AgentRun, ToolCall…
│   │
│   └── utils/
│       ├── embeddings.py       # ChromaDB wrapper: upsert, query, delete
│       ├── chunker.py          # Token-aware sliding-window text chunker
│       └── prompts.py          # Versioned prompt template registry
│
├── tests/
│   ├── unit/
│   │   ├── test_agents.py      # Agent loop, tool dispatch, error handling
│   │   └── test_tools.py       # code_exec, file_ops, web_search (mocked HTTP)
│   ├── integration/
│   │   └── test_api.py         # FastAPI routes with real app, mocked LLM
│   └── e2e/
│       └── test_workflows.py   # End-to-end agent workflow tests
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile          # Multi-stage production image (non-root, minimal)
│   │   └── docker-compose.yml  # Full local stack: API + Chroma + Redis + Postgres + Jaeger
│   └── k8s/
│       ├── deployment.yaml     # K8s Deployment with rolling update + probes
│       └── service.yaml        # ClusterIP Service + HorizontalPodAutoscaler
│
├── scripts/
│   ├── run_evals.py            # LLM eval harness: define cases, score, exit code
│   └── seed_db.py              # Seed vector store with initial knowledge base docs
│
├── mcp.json                    # Claude Desktop MCP server configuration
├── pyproject.toml              # Dependencies, build config, pytest, ruff, mypy
├── Makefile                    # Developer shortcuts (make dev, make test, make eval…)
├── .env.example                # Environment variable template
└── .gitignore
```

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/your-org/nexus
cd nexus
make install

# 2. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 3. Start the full stack (Docker required)
make docker-up

# 4. Run the API in dev mode
make dev
# → http://localhost:8000/docs

# 5. Start the MCP server (for Claude Desktop)
make mcp
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/agent/run` | Synchronous agent run |
| `POST` | `/api/v1/agent/stream` | SSE streaming agent run |
| `GET` | `/api/v1/tools` | List all registered tools |
| `POST` | `/api/v1/tools/{name}` | Execute a specific tool directly |
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/mcp/info` | MCP server metadata |
| `POST` | `/mcp/call` | Invoke an MCP tool via HTTP |
| `GET` | `/mcp/sse` | MCP SSE transport endpoint |

---

## Adding a New Tool

```python
# src/tools/my_tool.py
from src.tools.registry import registry

@registry.register(
    name="my_tool",
    description="Does something useful.",
    input_schema={
        "type": "object",
        "properties": {"input": {"type": "string"}},
        "required": ["input"],
    },
)
async def my_tool(input: str) -> dict:
    return {"result": input.upper()}
```

Then import it in `src/api/main.py` lifespan to self-register.

---

## Adding a New Agent

```python
# src/agents/my_agent.py
from src.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are a specialised agent that..."
```

---

## CI/CD Pipeline

```
Push to PR
  └── ci.yml
        ├── ruff lint + format check
        ├── mypy type check
        ├── pytest unit tests + coverage upload
        ├── pytest integration tests (with Chroma + Redis services)
        ├── Trivy security scan
        └── Docker build check

Merge to main
  └── cd.yml
        ├── Build + push image to GHCR
        ├── Deploy to staging
        ├── Smoke test staging
        └── [on tag v*] Deploy to production + Slack notification

Nightly (02:00 UTC)
  └── eval.yml
        ├── Run all eval suites against staging
        ├── Score and compare to 80% threshold
        └── Comment results on any open PRs
```

---

## MCP Integration (Claude Desktop)

Copy `mcp.json` to your Claude Desktop config and set your `ANTHROPIC_API_KEY`:

```bash
# macOS
cp mcp.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Claude Desktop will then have access to `web_search`, `code_exec`, `file_read`, `file_write`, and `file_list`.

---

## Environment Variables

See `.env.example` for the full list. Required:

- `ANTHROPIC_API_KEY` — your Anthropic API key

Optional but recommended:
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `CHROMA_HOST` / `CHROMA_PORT` — ChromaDB location
- `BRAVE_API_KEY` — enables Brave Search (falls back to DuckDuckGo without it)

---

## Free AI Models via OpenRouter

Nexus uses [OpenRouter](https://openrouter.ai) as its LLM gateway — **no paid API key required**. Sign up at openrouter.ai/keys (free, no credit card) and you get access to 28+ free models.

| Role | Model ID | Why |
|---|---|---|
| **Default** | `deepseek/deepseek-r1:free` | Best free reasoning model |
| **Fallback** | `meta-llama/llama-3.3-70b-instruct:free` | Kicks in when default is rate-limited |
| **Fast** | `google/gemini-flash-1.5:free` | Low latency for simple tasks |
| **Code** | `qwen/qwen3-coder:free` | Best free model for code generation |

Free tier limits: **20 requests/minute, ~200 requests/day**. For production, add OpenRouter credits and drop the `:free` suffix to unlock higher limits on the same models.

To switch models, just change `DEFAULT_MODEL` in your `.env` — no code changes needed.
