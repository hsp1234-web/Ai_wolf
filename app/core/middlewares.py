import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
import structlog

class RequestContextLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Clear previous context variables
        structlog.contextvars.clear_contextvars()
        # Bind the request ID to structlog's context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Optional: Log request start
        # logger = structlog.get_logger('request_context') # Not strictly needed here, but can be useful
        # logger.info(f'Request received: {request.method} {request.url.path}')

        response = await call_next(request)

        # Optional: Log request end
        # logger.info(f'Request finished: {request.method} {request.url.path}', status_code=response.status_code)

        return response
