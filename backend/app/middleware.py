"""Request-scoped middleware for correlation and idempotency tracking."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Propagates or generates an X-Correlation-Id for every request.
    
    If the client sends ``X-Correlation-Id``, it is preserved.
    Otherwise a new UUID is generated.  The id is stashed on
    ``request.state.correlation_id`` so downstream handlers can read it,
    and echoed back in the response header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        idempotency_key = request.headers.get("idempotency-key")

        request.state.correlation_id = correlation_id
        request.state.idempotency_key = idempotency_key

        response: Response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response
