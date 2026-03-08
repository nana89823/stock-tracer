import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.access")

# Paths to exclude from logging
EXCLUDED_PATHS = {"/health"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, duration, and client IP."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip excluded paths
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        try:
            start_time = time.perf_counter()

            response = await call_next(request)

            duration_ms = (time.perf_counter() - start_time) * 1000

            self._log_request(request, response.status_code, duration_ms)

            return response
        except Exception:
            # If call_next itself raises, log as 500 and re-raise
            try:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_request(request, 500, duration_ms)
            except Exception:
                pass
            raise

    def _log_request(
        self, request: Request, status_code: int, duration_ms: float
    ) -> None:
        try:
            method = request.method
            path = request.url.path
            query = str(request.url.query)
            full_path = f"{path}?{query}" if query else path

            # Client IP: prefer X-Real-IP (behind reverse proxy), then X-Forwarded-For
            client_ip = (
                request.headers.get("x-real-ip")
                or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
                or (request.client.host if request.client else "unknown")
            )

            message = (
                f"{method} {full_path} | {status_code} | {duration_ms:.0f}ms | {client_ip}"
            )

            if status_code >= 500:
                logger.error(message)
            elif status_code >= 400:
                logger.warning(message)
            else:
                logger.info(message)
        except Exception:
            # Middleware must never crash
            pass
