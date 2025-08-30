import redis
import json
import logging
import threading
import time
from typing import Optional, Any, Dict
from config.settings import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self, reconnect_interval: int = 5, max_reconnect_interval: int = 60):
        """
        Non-blocking Redis wrapper:
          - Starts a background thread that attempts to connect.
          - If Redis is unavailable, falls back to in-memory store.
          - Methods never raise due to Redis being down.
        """
        self.redis_client = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_interval = max_reconnect_interval
        self._use_memory = True
        self._store: Dict[str, Any] = {}

        # Start background reconnection thread (daemon so it won't block shutdown)
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()

    def _connect(self) -> bool:
        """Attempt to create a Redis client and ping it. Returns True on success."""
        try:
            redis_url = getattr(settings, "redis_url", None)
            if not redis_url:
                logger.info("No redis_url configured, using in-memory cache")
                return False

            if getattr(settings, "is_production", False):
                logger.info("🌐 Attempting to connect to AWS ElastiCache Redis")
            else:
                logger.info("💻 Attempting to connect to Redis")

            client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Ping to verify connection
            client.ping()

            with self._lock:
                self.redis_client = client
                self._use_memory = False

            logger.info("✅ Redis connection established")
            return True

        except Exception as e:
            logger.warning("❌ Redis connection failed: %s", e)
            with self._lock:
                self.redis_client = None
                self._use_memory = True
            return False

    def _reconnect_loop(self):
        """Background loop that attempts to connect and backs off on failure."""
        interval = self._reconnect_interval
        while not self._stop_event.is_set():
            with self._lock:
                client = self.redis_client
            if client is None:
                success = self._connect()
                if success:
                    interval = self._reconnect_interval
                else:
                    # exponential backoff capped at max_reconnect_interval
                    time.sleep(interval)
                    interval = min(interval * 2, self._max_reconnect_interval)
            else:
                # If connected, check health occasionally
                try:
                    client.ping()
                    time.sleep(30)
                except Exception:
                    logger.warning("Redis ping failed, dropping client and switching to in-memory")
                    with self._lock:
                        self.redis_client = None
                        self._use_memory = True

    def stop(self):
        """Stop background thread (call from shutdown hooks if needed)."""
        self._stop_event.set()
        try:
            self._reconnect_thread.join(timeout=2)
        except Exception:
            pass

    def is_connected(self) -> bool:
        """Check if Redis is connected and responsive."""
        with self._lock:
            client = self.redis_client
        if not client:
            return False
        try:
            client.ping()
            return True
        except Exception:
            # Mark as disconnected; let background thread attempt reconnect
            with self._lock:
                self.redis_client = None
                self._use_memory = True
            return False

    def _switch_to_memory(self, err: Exception):
        logger.warning("Switching to in-memory cache due to Redis error: %s", err)
        with self._lock:
            self.redis_client = None
            self._use_memory = True

    def set_cache(self, key: str, value: Any, expire: int = 3600) -> bool:
        if not self.is_connected():
            # store in-memory (stringify for JSON-compat)
            try:
                self._store[key] = value
                return True
            except Exception as e:
                logger.error("Failed to set in-memory cache for key %s: %s", key, e)
                return False

        try:
            json_value = json.dumps(value, default=str)
            with self._lock:
                # redis_client may have changed; capture locally
                client = self.redis_client
            if client is None:
                return self.set_cache(key, value, expire)

            client.setex(key, expire, json_value)
            return True
        except Exception as e:
            logger.error("Error setting cache for key %s: %s", key, e)
            self._switch_to_memory(e)
            try:
                self._store[key] = value
            except Exception:
                pass
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        if not self.is_connected():
            return self._store.get(key)

        try:
            with self._lock:
                client = self.redis_client
            if client is None:
                return self._store.get(key)

            json_value = client.get(key)
            if json_value is None:
                return None
            return json.loads(json_value)
        except Exception as e:
            logger.error("Error getting cache for key %s: %s", key, e)
            self._switch_to_memory(e)
            return self._store.get(key)

    def delete_cache(self, key: str) -> bool:
        if not self.is_connected():
            self._store.pop(key, None)
            return True
        try:
            with self._lock:
                client = self.redis_client
            if client is None:
                self._store.pop(key, None)
                return True
            client.delete(key)
            return True
        except Exception as e:
            logger.error("Error deleting cache for key %s: %s", key, e)
            self._switch_to_memory(e)
            self._store.pop(key, None)
            return True

    # Convenience wrappers used by app
    def get_cached_query(self, cache_key: str) -> Optional[Dict]:
        return self.get_cache(f"query:{cache_key}")

    def set_cached_query(self, cache_key: str, result: Dict, expire: int = 1800) -> bool:
        return self.set_cache(f"query:{cache_key}", result, expire)

# Global cache instance (non-blocking init)
cache = RedisCache()

# Backwards-compatible helpers
def get_cached_query(cache_key: str) -> Optional[Dict]:
    return cache.get_cached_query(cache_key)

def set_cached_query(cache_key: str, result: Dict, expire: int = 1800) -> bool:
    return cache.set_cached_query(cache_key, result, expire)