"""
src/api/main.py
────────────────
FastAPI application factory.
Wires together lifespan events, middleware, routers, and exception handlers.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.api.middleware import ErrorHandlingMiddleware, RequestLoggingMiddleware
from src.api.routes import router
from src.core.config import settings
from src.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    configure_logging()
    logger.info("app_starting", env=settings.app_env, model=settings.default_model)

    # Import tools to trigger registration
    import src.tools.web_search  # noqa: F401
    import src.tools.code_exec   # noqa: F401
    import src.tools.file_ops    # noqa: F401

    logger.info("app_ready")
    yield
    logger.info("app_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nexus API",
        description="Nexus — the connective core for your AI agent stack. MCP, RAG, tool use, and streaming.",
        version="0.1.0",
        debug=settings.app_debug,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── CORS ──────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom middleware ──────────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)

    # ── Routes ────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1")

    # ── OpenTelemetry ─────────────────────────────────────────
    FastAPIInstrumentor.instrument_app(app)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.app_debug,
        log_config=None,  # Use structlog
    )
