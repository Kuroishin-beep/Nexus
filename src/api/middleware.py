"""
src/api/middleware.py
──────────────────────
Custom Starlette middleware:
  - RequestLoggingMiddleware: logs every request with timing and trace ID
  - ErrorHandlingMiddleware: converts AppError exceptions to structured JSON
"""

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.exceptions import AppError
from src.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
        )

        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            request_id=request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except AppError as exc:
            logger.warning(
                "app_error",
                code=exc.code,
                message=exc.message,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "success": False,
                    "error": exc.message,
                    "code": exc.code,
                    "detail": exc.detail,
                },
            )
        except Exception as exc:
            logger.exception("unhandled_error", path=request.url.path, error=str(exc))
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal server error",
                    "code": "INTERNAL_ERROR",
                },
            )
