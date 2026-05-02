"""
FastAPI middleware for the Boston Parking RAG API.
Handles: request logging, error handling, rate limiting (basic).
"""

import time
import uuid
import logging
from collections import defaultdict
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("boston_parking_rag")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status code, and latency."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Log incoming request
        logger.info(f"[{request_id}] → {request.method} {request.url.path}")

        try:
            response = await call_next(request)
            elapsed = (time.time() - start_time) * 1000
            logger.info(
                f"[{request_id}] ← {response.status_code} "
                f"({elapsed:.0f}ms)"
            )
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"[{request_id}] ✗ Unhandled error ({elapsed:.0f}ms): {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Please try again."},
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter.
    Default: 30 requests per minute per IP.
    Not suitable for multi-process deployments — use Redis for production.
    """

    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        window_start = now - self.window_seconds

        # Remove timestamps outside the window
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > window_start
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s."
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns clean JSON error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except ValueError as e:
            logger.error(f"ValueError: {e}")
            return JSONResponse(
                status_code=400,
                content={"detail": str(e)},
            )
        except FileNotFoundError as e:
            logger.error(f"FileNotFoundError: {e}")
            return JSONResponse(
                status_code=503,
                content={"detail": "Index not found. Please run the indexing pipeline first."},
            )
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "An unexpected error occurred."},
            )