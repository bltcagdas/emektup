import uuid
import logging
from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure basic structured JSON logging format later,
# but for now, we ensure request_id is present.

logger = logging.getLogger("emektup")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('{"time": "%(asctime)s", "level": "%(levelname)s", "request_id": "%(request_id)s", "message": "%(message)s"}')
handler.setFormatter(formatter)
logger.addHandler(handler)

class RequestIdFilter(logging.Filter):
    def __init__(self, request_id: str):
        super().__init__()
        self.request_id = request_id

    def filter(self, record):
        record.request_id = self.request_id
        return True

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Generate a unique request ID
        req_id = str(uuid.uuid4())
        
        # Store it in request state to be accessible by routes/deps
        request.state.request_id = req_id
        
        # Let's add it to logger context for the duration of this request
        # (A more robust async context var like contextvars should be used in prod, 
        # but attaching it to request state works for our scope)
        
        response = await call_next(request)
        
        # Inject the request ID into the response headers
        response.headers["X-Request-Id"] = req_id
        return response
