"""
Request timeout protection - prevents long-running requests from hanging.
"""

import asyncio
import time
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class TimeoutProtectionMiddleware(BaseHTTPMiddleware):
    """
    Protect against long-running requests that could exhaust resources.
    """

    def __init__(self, app, timeout_seconds: int = 30):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.skip_paths = ['/health', '/docs']

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        try:
            # Set timeout for request processing
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={
                    "error_code": "REQUEST_TIMEOUT",
                    "error_message": f"Request timed out after {self.timeout_seconds}s"
                }
            )