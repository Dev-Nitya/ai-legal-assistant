import time
import logging
import statistics
from typing import List, Dict, Optional
from collections import deque
import numpy as np
from datetime import datetime
from threading import Lock

from redis_cache.redis_cache import cache

logger = logging.getLogger(__name__)

class LatencyTracker:
    """
    Service for tracking and computing p95/p99 latency metrics.
    Uses Redis for persistence with in-memory fallback.
    """

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._lock = Lock()
        # In-memory fallback storage
        self._memory_store: Dict[str, deque] = {}

    def record_latency(self, endpoint: str, latency_ms: float, user_id: Optional[str] = None) -> None:
        """
        Record a latency measurement for an endpoint.
        
        Args:
            endpoint: The endpoint name (e.g., 'enhanced-chat')
            latency_ms: Latency in milliseconds
            user_id: Optional user ID for user-specific metrics
        """
        try:
            timestamp = int(time.time() * 1000)  # milliseconds since epoch
            
            # Record global endpoint latency
            self._record_sample(f"latency:{endpoint}", latency_ms, timestamp)
            
            # Record user-specific latency if user_id provided
            if user_id:
                self._record_sample(f"latency:{endpoint}:user:{user_id}", latency_ms, timestamp)
                
            logger.debug(f"Recorded latency {latency_ms}ms for {endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to record latency: {e}")

    def _record_sample(self, cache_key: str, latency_ms: float, timestamp: int) -> None:
        """Store a latency sample in Redis or in-memory store."""
        sample = {"latency_ms": latency_ms, "timestamp": timestamp}
        
        try:
            # Try Redis first
            existing_data = cache.get(cache_key) or []
            if isinstance(existing_data, str):
                import json
                existing_data = json.loads(existing_data)
            if not isinstance(existing_data, list):
                existing_data = []
                
            existing_data.append(sample)
            
            # Keep only the most recent samples
            if len(existing_data) > self.max_samples:
                existing_data = existing_data[-self.max_samples:]
            
            # Store back to Redis with 24-hour expiry
            cache.set(cache_key, existing_data, expire=86400)
            
        except Exception as e:
            logger.warning(f"Redis storage failed, using in-memory fallback: {e}")
            # Fallback to in-memory storage
            with self._lock:
                if cache_key not in self._memory_store:
                    self._memory_store[cache_key] = deque(maxlen=self.max_samples)
                self._memory_store[cache_key].append(sample)

    def get_latency_stats(self, endpoint: str, user_id: Optional[str] = None) -> Dict[str, float]:
        """
        Get latency statistics for an endpoint.
        
        Args:
            endpoint: The endpoint name
            user_id: Optional user ID for user-specific stats
            
        Returns:
            Dict containing median, p95, p99, min, max, count
        """
        cache_key = f"latency:{endpoint}"
        if user_id:
            cache_key = f"latency:{endpoint}:user:{user_id}"
            
        logger.debug(f"Getting latency stats for cache_key: {cache_key}")
        stats = self._compute_stats(cache_key)
        logger.debug(f"Stats for {cache_key}: count={stats.get('count', 0)}")
        return stats

    def _compute_stats(self, cache_key: str) -> Dict[str, float]:
        """Compute statistics from stored latency samples."""
        try:
            # Try Redis first
            data = cache.get(cache_key)
            if data and isinstance(data, str):
                import json
                data = json.loads(data)
            
            if not data or not isinstance(data, list):
                # Fallback to in-memory store
                with self._lock:
                    if cache_key in self._memory_store:
                        data = list(self._memory_store[cache_key])
                    else:
                        data = []
            
            if not data:
                return self._empty_stats()
                
            # Extract latency values
            latencies = [sample["latency_ms"] for sample in data if "latency_ms" in sample]
            
            if not latencies:
                return self._empty_stats()
                
            return self._calculate_percentiles(latencies)
            
        except Exception as e:
            logger.error(f"Failed to compute latency stats: {e}")
            return self._empty_stats()

    def _calculate_percentiles(self, latencies: List[float]) -> Dict[str, float]:
        """Calculate percentile statistics from latency values."""
        latencies = sorted(latencies)
        count = len(latencies)
        
        if count == 0:
            return self._empty_stats()
            
        stats = {
            "count": float(count),
            "min_ms": float(min(latencies)),
            "max_ms": float(max(latencies)),
            "median_ms": float(statistics.median(latencies)),
            "mean_ms": float(statistics.mean(latencies)),
        }
        
        # Calculate percentiles using numpy for accuracy
        if count >= 2:
            stats["p95_ms"] = float(np.percentile(latencies, 95))
            stats["p99_ms"] = float(np.percentile(latencies, 99))
        else:
            # For single sample, p95 and p99 are the same as the value
            stats["p95_ms"] = float(latencies[0])
            stats["p99_ms"] = float(latencies[0])
            
        return stats

    def _empty_stats(self) -> Dict[str, float]:
        """Return empty statistics structure."""
        return {
            "count": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "median_ms": 0.0,
            "mean_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
        }

    def get_all_endpoint_stats(self) -> Dict[str, Dict[str, float]]:
        """Get latency stats for all tracked endpoints."""
        stats = {}
        
        try:
            # Try to discover endpoints dynamically from Redis
            try:
                # Get all keys matching the pattern "latency:*"
                pattern = "latency:*"
                keys = cache.redis_client.keys(pattern) if hasattr(cache, 'redis_client') else []
                
                # Extract endpoint names from keys
                endpoint_names = set()
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    
                    # Extract endpoint from key like "latency:enhanced-chat" or "latency:endpoint:user:userid"
                    parts = key.split(':')
                    if len(parts) >= 2 and parts[0] == 'latency':
                        endpoint = parts[1]
                        # Skip user-specific keys (they contain 'user' as third part)
                        if len(parts) < 3 or parts[2] != 'user':
                            endpoint_names.add(endpoint)
                
                logger.info(f"Discovered endpoints from Redis: {list(endpoint_names)}")
                        
            except Exception as e:
                logger.warning(f"Failed to discover endpoints from Redis: {e}")
                endpoint_names = set()
            
            # Fallback to known endpoints if discovery failed
            if not endpoint_names:
                endpoint_names = {"enhanced-chat", "auth", "evaluation"}  # Add more as needed
                logger.info(f"Using fallback endpoints: {list(endpoint_names)}")
            
            for endpoint in endpoint_names:
                endpoint_stats = self.get_latency_stats(endpoint)
                if endpoint_stats["count"] > 0:
                    stats[endpoint] = endpoint_stats
                    logger.info(f"Found stats for {endpoint}: count={endpoint_stats['count']}")
                else:
                    logger.info(f"No stats found for {endpoint}")
                    
        except Exception as e:
            logger.error(f"Failed to get all endpoint stats: {e}")
            
        logger.info(f"Returning stats for {len(stats)} endpoints: {list(stats.keys())}")
        return stats

    def clear_stats(self, endpoint: str, user_id: Optional[str] = None) -> bool:
        """Clear latency statistics for an endpoint."""
        try:
            cache_key = f"latency:{endpoint}"
            if user_id:
                cache_key = f"latency:{endpoint}:user:{user_id}"
                
            # Clear from Redis
            cache.delete(cache_key)
            
            # Clear from in-memory store
            with self._lock:
                if cache_key in self._memory_store:
                    del self._memory_store[cache_key]
                    
            logger.info(f"Cleared latency stats for {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear latency stats: {e}")
            return False


# Global instance
latency_tracker = LatencyTracker()
