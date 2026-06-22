"""
src/core/config.py
──────────────────
Centralised application settings loaded from environment variables / .env file.
All other modules import `settings` from here — never read os.environ directly.

LLM backend: OpenRouter (https://openrouter.ai)
Free models are used by default — no credits required, just a free API key.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ───────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_port: int = 8000
    app_debug: bool = False
    secret_key: SecretStr = Field(default="change-me")

    # ── OpenRouter (free tier) ─────────────────────────────────
    # Get a free key at https://openrouter.ai/keys — no credit card needed
    openrouter_api_key: SecretStr
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Free models — all end in :free, zero cost
    # Primary: DeepSeek R1 — best free reasoning model
    default_model: str = "deepseek/deepseek-r1:free"
    # Fallback: Llama 3.3 70B — reliable general-purpose
    fallback_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    # Fast: Gemini Flash — low latency for simple tasks
    fast_model: str = "google/gemini-flash-1.5:free"
    # Coding: Qwen3 Coder — best free model for code tasks
    code_model: str = "qwen/qwen3-coder:free"

    # Shown in OpenRouter dashboard under your key
    app_name: str = "Nexus"
    app_url: str = "https://github.com/your-org/nexus"

    # ── Database ──────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    redis_url: str = "redis://localhost:6379/0"

    # ── Vector DB ─────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "knowledge_base"

    # ── MCP ───────────────────────────────────────────────────
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 8002
    mcp_auth_token: SecretStr | None = None

    # ── Observability ─────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton. Use this everywhere."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
