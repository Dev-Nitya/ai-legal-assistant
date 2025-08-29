# This file handles Redis connections smartly

import redis
import json
import logging
from typing import Optional, Any, Dict, List
from config.settings import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Connect to Redis based on environment"""
        try:
            redis_url = settings.redis_url
            
            if settings.is_production:
                logger.info("🌐 Connecting to AWS ElastiCache Redis")
            else:
                logger.info("💻 Connecting to local Redis")
            
            # Create Redis connection
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Automatically decode responses
                socket_connect_timeout=5,  # 5 second connection timeout
                socket_timeout=5,  # 5 second operation timeout
                retry_on_timeout=True,  # Retry if timeout
                health_check_interval=30  # Check connection health every 30s
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def set_cache(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Store value in Redis cache
        
        USAGE:
        cache.set_cache("user:123", {"name": "John"}, expire=1800)
        """
        if not self.is_connected():
            logger.warning("Redis not connected, skipping cache set")
            return False
        
        try:
            # Convert value to JSON string
            json_value = json.dumps(value, default=str)
            
            # Store in Redis with expiration
            self.redis_client.setex(key, expire, json_value)
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache
        
        USAGE:
        user_data = cache.get_cache("user:123")
        """
        if not self.is_connected():
            return None
        
        try:
            # Get value from Redis
            json_value = self.redis_client.get(key)
            
            if json_value is None:
                return None
            
            # Convert JSON string back to Python object
            return json.loads(json_value)
            
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete value from Redis cache"""
        if not self.is_connected():
            return False
        
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False
    
    def get_cached_query(self, cache_key: str) -> Optional[Dict]:
        """Get cached query result (used by enhanced_chat)"""
        return self.get_cache(f"query:{cache_key}")
    
    def set_cached_query(self, cache_key: str, result: Dict, expire: int = 1800) -> bool:
        """Set cached query result (used by enhanced_chat)"""
        return self.set_cache(f"query:{cache_key}", result, expire)

# Global cache instance
cache = RedisCache()

# Helper functions for backward compatibility
def get_cached_query(cache_key: str) -> Optional[Dict]:
    return cache.get_cached_query(cache_key)

def set_cached_query(cache_key: str, result: Dict, expire: int = 1800) -> bool:
    return cache.set_cached_query(cache_key, result, expire)