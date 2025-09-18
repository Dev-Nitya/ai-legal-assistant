import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional

from services.latency_tracking_service import latency_tracker
from config.database import get_db
from services.latency_metric_service import LatencyMetricService

logger = logging.getLogger(__name__)

class LatencyTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically track latency for all HTTP requests.
    Records both in-memory (Redis) and database metrics.
    """

    def __init__(
        self, 
        app,
        track_all_endpoints: bool = False,
        specific_endpoints: Optional[list] = None,
        store_in_db: bool = True
    ):
        super().__init__(app)
        self.track_all_endpoints = track_all_endpoints
        self.specific_endpoints = specific_endpoints or ["/enhanced-chat"]
        self.store_in_db = store_in_db

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Main middleware function that tracks latency for each request.
        
        Flow:
        1. Record start time
        2. Process the request
        3. Calculate latency
        4. Store latency metrics if endpoint is tracked
        5. Return response with latency headers
        """
        start_time = time.time()
        
        # Get request metadata
        endpoint = self._extract_endpoint(request)
        user_id = self._extract_user_id(request)
        request_id = self._extract_request_id(request)
        
        logger.debug(f"Processing request to '{request.url.path}' -> endpoint: '{endpoint}'")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate latency
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Track latency if this endpoint is monitored
        if self._should_track_endpoint(endpoint):
            logger.info(f"Recording latency for endpoint '{endpoint}': {latency_ms:.2f}ms")
            await self._record_latency(
                endpoint=endpoint,
                latency_ms=latency_ms,
                user_id=user_id,
                request_id=request_id,
                status_code=response.status_code
            )
        else:
            logger.debug(f"Not tracking endpoint '{endpoint}' (not in tracked list: {self.specific_endpoints})")
        
        # Add latency header to response for debugging
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
        
        return response

    def _extract_endpoint(self, request: Request) -> str:
        """Extract normalized endpoint name from request."""
        try:
            path = request.url.path
            
            # Normalize endpoint names - handle /api prefix
            if "/enhanced-chat" in path:
                return "enhanced-chat"
            elif "/auth" in path:
                return "auth"
            elif "/health" in path:
                return "health"
            elif "/eval" in path:
                return "evaluation"
            elif "/latency" in path:
                return "latency"
            elif "/cache" in path:
                return "cache"
            else:
                # Use the last meaningful path segment as endpoint name
                segments = [seg for seg in path.split("/") if seg and seg != "api"]
                return segments[0] if segments else "root"
                
        except Exception as e:
            logger.warning(f"Failed to extract endpoint from request: {e}")
            return "unknown"

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request headers or query params."""
        try:
            # Try different common locations for user ID
            user_id = (
                request.headers.get("x-user-id") or
                request.headers.get("user-id") or
                request.query_params.get("user_id")
            )
            
            # Also try to extract from request body if it's a POST with JSON
            if not user_id and request.method == "POST":
                try:
                    # This is tricky because we can't easily read the body in middleware
                    # without consuming it. For now, rely on headers.
                    pass
                except Exception:
                    pass
                    
            return user_id
            
        except Exception as e:
            logger.debug(f"Could not extract user ID: {e}")
            return None

    def _extract_request_id(self, request: Request) -> Optional[str]:
        """Extract request ID from headers."""
        try:
            return (
                request.headers.get("x-request-id") or
                request.headers.get("request-id") or
                request.headers.get("correlation-id")
            )
        except Exception:
            return None

    def _should_track_endpoint(self, endpoint: str) -> bool:
        """Determine if this endpoint should be tracked."""
        if self.track_all_endpoints:
            return True
        return endpoint in self.specific_endpoints

    async def _record_latency(
        self,
        endpoint: str,
        latency_ms: float,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        status_code: int = 200
    ) -> None:
        """Record latency in both in-memory tracker and database."""
        try:
            # Record in in-memory tracker (Redis)
            latency_tracker.record_latency(endpoint, latency_ms, user_id)
            
            # Record in database if enabled
            if self.store_in_db:
                await self._store_in_database(
                    endpoint, latency_ms, user_id, request_id, status_code
                )
                
        except Exception as e:
            logger.error(f"Failed to record latency for {endpoint}: {e}")

    async def _store_in_database(
        self,
        endpoint: str,
        latency_ms: float,
        user_id: Optional[str],
        request_id: Optional[str],
        status_code: int
    ) -> None:
        """Store latency measurement in database."""
        db = None
        try:
            # Get database session
            db_gen = get_db()
            db = next(db_gen)
            
            # Prepare metadata
            latency_metadata = {
                "status_code": status_code,
                "timestamp": time.time()
            }
            
            # Store in database
            success = LatencyMetricService.record_latency(
                db=db,
                endpoint=endpoint,
                latency_ms=latency_ms,
                user_id=user_id,
                request_id=request_id,
                latency_metadata=latency_metadata
            )
            
            if not success:
                logger.warning(f"Failed to store latency metric in database for {endpoint}")
                
        except Exception as e:
            logger.error(f"Database storage failed for latency metric: {e}")
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass
