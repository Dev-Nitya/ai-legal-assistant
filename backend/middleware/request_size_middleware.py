"""
Request size middleware using existing security validators.
Lightweight wrapper around validators/security.py functions.
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from schemas.validation import ValidationError
from validators.security import validate_request_size, validate_request_headers_size

logger = logging.getLogger(__name__)

class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Lightweight request size middleware using existing validators.
    Validates request content and headers size.
    """

    def __init__(self, app, max_content_kb: int = 100, max_headers_kb: int = 10):
        super().__init__(app)
        self.max_content_kb = max_content_kb
        self.max_headers_kb = max_headers_kb
        self.skip_paths = ['/health', '/metrics', '/docs', '/redoc', '/openapi.json']

    async def dispatch(self, request: Request, call_next):
        """Apply request size validation using existing security validators."""
        
        # Skip validation for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
    
        try:
        
            # Validate headers size first (lightweight check)
            validate_request_headers_size(dict(request.headers), self.max_headers_kb)

            if request.method in ['POST', 'PUT', 'PATCH']:
                content_length = request.headers.get('content-length')
                validate_request_size('', self.max_content_kb, content_length)

            return await call_next(request)

        except ValidationError as e:
            logger.warning(f"Request size validation failed: {e}")
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error_code": "REQUEST_TOO_LARGE",
                    "error_message": str(e),
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            )
        except Exception as e:
            logger.error(f"Request size middleware error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error_code": "SIZE_VALIDATION_ERROR",
                    "error_message": "Request size validation failed"
                }
            )