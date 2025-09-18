import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from config.database import get_db
from redis_cache.redis_cache import cache

logger = logging.getLogger(__name__)

router = APIRouter()

@router.delete("/cache/clear-queries")
async def clear_cached_queries():
    """
    Clear all cached query responses while preserving vector store embeddings.
    This will force fresh responses for all future queries.
    """
    try:
        cleared_count = 0
        
        if cache.client:
            # Redis implementation
            try:
                # Get all keys with the query prefix
                query_keys = cache.client.keys("query:*")
                if query_keys:
                    deleted = cache.client.delete(*query_keys)
                    cleared_count = deleted
                    logger.info(f"Cleared {deleted} cached queries from Redis")
                else:
                    logger.info("No cached queries found in Redis")
            except Exception as e:
                logger.error(f"Failed to clear Redis query cache: {e}")
                raise
        else:
            # In-memory implementation
            query_keys = [key for key in cache._store.keys() if key.startswith("query:")]
            for key in query_keys:
                del cache._store[key]
            cleared_count = len(query_keys)
            logger.info(f"Cleared {cleared_count} cached queries from memory")
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} cached query responses",
            "queries_cleared": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cached queries: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cached queries: {str(e)}"
        )

@router.delete("/cache/clear-latency")
async def clear_cached_latency_data():
    """
    Clear only latency-related data from cache (not query responses).
    """
    try:
        cleared_count = 0
        
        if cache.client:
            # Redis implementation
            try:
                # Get all keys with the latency prefix
                latency_keys = cache.client.keys("latency:*")
                if latency_keys:
                    deleted = cache.client.delete(*latency_keys)
                    cleared_count = deleted
                    logger.info(f"Cleared {deleted} latency entries from Redis")
                else:
                    logger.info("No latency data found in Redis")
            except Exception as e:
                logger.error(f"Failed to clear Redis latency cache: {e}")
                raise
        else:
            # In-memory implementation
            latency_keys = [key for key in cache._store.keys() if key.startswith("latency:")]
            for key in latency_keys:
                del cache._store[key]
            cleared_count = len(latency_keys)
            logger.info(f"Cleared {cleared_count} latency entries from memory")
        
        return {
            "success": True,
            "message": f"Cleared {cleared_count} latency cache entries",
            "latency_entries_cleared": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear latency cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear latency cache: {str(e)}"
        )

@router.get("/cache/info")
async def get_cache_info():
    """
    Get information about what's currently in the cache.
    """
    try:
        info = {
            "using_redis": cache.client is not None,
            "query_count": 0,
            "latency_count": 0,
            "other_count": 0,
            "total_keys": 0
        }
        
        if cache.client:
            # Redis implementation
            try:
                all_keys = cache.client.keys("*")
                info["total_keys"] = len(all_keys)
                
                for key in all_keys:
                    if key.startswith("query:"):
                        info["query_count"] += 1
                    elif key.startswith("latency:"):
                        info["latency_count"] += 1
                    else:
                        info["other_count"] += 1
                        
            except Exception as e:
                logger.warning(f"Failed to get Redis info: {e}")
        else:
            # In-memory implementation
            all_keys = list(cache._store.keys())
            info["total_keys"] = len(all_keys)
            
            for key in all_keys:
                if key.startswith("query:"):
                    info["query_count"] += 1
                elif key.startswith("latency:"):
                    info["latency_count"] += 1
                else:
                    info["other_count"] += 1
        
        return {
            "success": True,
            "message": "Cache information retrieved",
            "cache_info": info
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache info: {str(e)}"
        )

@router.delete("/cache/clear-all")
async def clear_all_cache(
    confirm: bool = Query(False, description="Set to true to confirm deletion"),
    preserve_vectors: bool = Query(True, description="Set to false to also clear vector embeddings")
):
    """
    Clear all cache data. By default preserves vector store embeddings.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to proceed with deletion"
        )
    
    try:
        cleared_count = 0
        
        if cache.client:
            # Redis implementation
            if preserve_vectors:
                # Clear only specific prefixes, preserving vector embeddings
                prefixes_to_clear = ["query:", "latency:", "eval_score:", "eval_rerank_weights"]
                for prefix in prefixes_to_clear:
                    keys = cache.client.keys(f"{prefix}*")
                    if keys:
                        deleted = cache.client.delete(*keys)
                        cleared_count += deleted
                        logger.info(f"Cleared {deleted} keys with prefix '{prefix}'")
            else:
                # Clear everything
                all_keys = cache.client.keys("*")
                if all_keys:
                    cleared_count = cache.client.delete(*all_keys)
                    logger.info(f"Cleared all {cleared_count} keys from Redis")
        else:
            # In-memory implementation
            if preserve_vectors:
                # Clear only specific prefixes
                keys_to_clear = []
                for key in cache._store.keys():
                    if any(key.startswith(prefix) for prefix in ["query:", "latency:", "eval_score:", "eval_rerank_weights"]):
                        keys_to_clear.append(key)
                
                for key in keys_to_clear:
                    del cache._store[key]
                cleared_count = len(keys_to_clear)
            else:
                # Clear everything
                cleared_count = len(cache._store)
                cache._store.clear()
        
        message = f"Cleared {cleared_count} cache entries"
        if preserve_vectors:
            message += " (vector embeddings preserved)"
        
        return {
            "success": True,
            "message": message,
            "entries_cleared": cleared_count,
            "vectors_preserved": preserve_vectors
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )
