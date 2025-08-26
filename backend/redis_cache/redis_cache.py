import redis
import json
import hashlib
import os
from typing import Optional, Any, List, Dict
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class LegalAssistantCache:
    def __init__(self):
        """Initialize Redis connection with fallback to local memory"""
        self.redis_client = None
        self.local_cache = {} # Fallback local cache

        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable, using in-memory cache: {e}")
            self.redis_client = None

    def _generate_cache_key(self, prefix: str, data: Any) -> str:
        """Generate consistent cache key from data"""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)

        hash_object = hashlib.md5(content.encode())
        return f"legal_assistant:{prefix}:{hash_object.hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
            else:
                return self.local_cache.get(key)
        except Exception as e:
            logger.error(f"Error retrieving cache key {key}: {e}")
        return None
    
    def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """Set value in cache with expiration"""
        try:
            serialized_value = json.dumps(value, default=str)

            if self.redis_client:
                return self.redis_client.setex(key, expire_seconds, serialized_value)
            else:
                self.local_cache[key] = value
                return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            return False

    def cache_query_response(self, query: str, response: Dict, ttl: int = 1800) -> bool:
        """Cache a query response for 30 minutes"""
        cache_key = self._generate_cache_key("query", query.lower().strip())
        return self.set(cache_key, response, ttl)
    
    def get_cached_query(self, query: str) -> Optional[Dict]:
        """Get cached response for a query"""
        cache_key = self._generate_cache_key("query", query.lower().strip())
        return self.get(cache_key)
    
    def cache_document_metadata(self, doc_hash: str, metadata: Dict, ttl_seconds: int = 86400) -> bool:
        """Cache document metadata for 24 hours"""
        cache_key = self._generate_cache_key("doc_meta", doc_hash)
        return self.set(cache_key, metadata, ttl_seconds)

    def get_document_metadata(self, doc_hash: str) -> Optional[Dict]:
        """Get cached document metadata"""
        cache_key = self._generate_cache_key("doc_meta", doc_hash)
        return self.get(cache_key)
    
    def cache_vector_search(self, query: str, filters: Dict, results: List[Dict], ttl_seconds: int = 3600) -> bool:
        """Cache vector search results for 1 hour"""
        cache_data = {"query": query, "filters": filters}
        cache_key = self._generate_cache_key("vector_search", cache_data)
        return self.set(cache_key, results, ttl_seconds)

    def get_cached_vector_search(self, query: str, filters: Dict) -> Optional[List[Dict]]:
        """Get cached vector search results"""
        cache_data = {"query": query, "filters": filters}
        cache_key = self._generate_cache_key("vector_search", cache_data)
        return self.get(cache_key)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(f"legal_assistant:{pattern}:*")
                if keys:
                    return self.redis_client.delete(*keys)
            else:
                # Clear local cache
                keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.local_cache[key]
                return len(keys_to_delete)
        except Exception as e:
            logger.error(f"Cache invalidation error for pattern {pattern}: {e}")
        return 0
    
# Global cache instance
cache = LegalAssistantCache()
