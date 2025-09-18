import logging
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from config.database import get_db
from services.latency_tracking_service import latency_tracker
from services.latency_metric_service import LatencyMetricService

logger = logging.getLogger(__name__)

router = APIRouter()

class LatencyStatsResponse(BaseModel):
    """Response model for latency statistics."""
    success: bool
    message: str
    endpoint: str
    user_id: Optional[str] = None
    stats: Dict[str, float]
    source: str  # "memory" or "database"
    
class EndpointSummaryResponse(BaseModel):
    """Response model for endpoint summary."""
    success: bool
    message: str
    endpoints: Dict[str, Dict[str, float]]
    source: str

@router.get("/latency/stats/{endpoint}", response_model=LatencyStatsResponse)
async def get_endpoint_latency_stats(
    endpoint: str,
    user_id: Optional[str] = Query(None, description="Optional user ID for user-specific stats"),
    source: str = Query("memory", description="Data source: 'memory' or 'database'"),
    hours_back: int = Query(24, description="Hours back to analyze (for database source)"),
    exclude_cache: bool = Query(False, description="Exclude cache hits (for database source)"),
    db: Session = Depends(get_db)
):
    """
    Get latency statistics for a specific endpoint.
    
    Returns p95, p99, median, mean, min, max, and count.
    """
    try:
        if source == "memory":
            # Get stats from in-memory tracker (Redis)
            stats = latency_tracker.get_latency_stats(endpoint, user_id)
            data_source = "memory"
        elif source == "database":
            # Get stats from database
            stats = LatencyMetricService.calculate_stats_from_db(
                db, endpoint, user_id, hours_back, exclude_cache
            )
            if not stats:
                stats = {
                    "count": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                    "median_ms": 0.0,
                    "mean_ms": 0.0,
                    "p95_ms": 0.0,
                    "p99_ms": 0.0,
                }
            data_source = "database"
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source. Must be 'memory' or 'database'"
            )
        
        return LatencyStatsResponse(
            success=True,
            message=f"Latency statistics for {endpoint}",
            endpoint=endpoint,
            user_id=user_id,
            stats=stats,
            source=data_source
        )
        
    except Exception as e:
        logger.error(f"Failed to get latency stats for {endpoint}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latency statistics: {str(e)}"
        )

@router.get("/latency/summary", response_model=EndpointSummaryResponse)
async def get_latency_summary(
    source: str = Query("memory", description="Data source: 'memory' or 'database'"),
    hours_back: int = Query(24, description="Hours back to analyze (for database source)"),
    include_cache: bool = Query(True, description="Include cache hits in database stats"),
    db: Session = Depends(get_db)
):
    """
    Get latency summary for all tracked endpoints.
    """
    try:
        if source == "memory":
            # Get stats from in-memory tracker
            endpoints = latency_tracker.get_all_endpoint_stats()
            data_source = "memory"
            logger.info(f"Memory latency summary: {len(endpoints)} endpoints found")
        elif source == "database":
            # Get stats from database
            if include_cache:
                endpoints = LatencyMetricService.get_endpoint_summary(db, hours_back)
            else:
                # Get only non-cache stats
                endpoints = LatencyMetricService.get_endpoint_summary_no_cache(db, hours_back)
            data_source = "database"
            logger.info(f"Database latency summary: {len(endpoints)} endpoints found")
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source. Must be 'memory' or 'database'"
            )
        
        logger.info(f"Latency summary endpoints: {list(endpoints.keys()) if endpoints else 'None'}")
        
        return EndpointSummaryResponse(
            success=True,
            message="Latency summary for all endpoints",
            endpoints=endpoints,
            source=data_source
        )
        
    except Exception as e:
        logger.error(f"Failed to get latency summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve latency summary: {str(e)}"
        )

@router.get("/latency/measurements/{endpoint}")
async def get_recent_measurements(
    endpoint: str,
    user_id: Optional[str] = Query(None, description="Optional user ID filter"),
    hours_back: int = Query(1, description="Hours back to retrieve"),
    limit: int = Query(100, description="Maximum number of measurements"),
    exclude_cache: bool = Query(False, description="Exclude cache hits from results"),
    db: Session = Depends(get_db)
):
    """
    Get recent individual latency measurements for an endpoint.
    """
    try:
        measurements = LatencyMetricService.get_individual_measurements(
            db, endpoint, user_id, hours_back, limit, exclude_cache
        )
        
        return {
            "success": True,
            "message": f"Recent measurements for {endpoint}",
            "endpoint": endpoint,
            "user_id": user_id,
            "measurements": measurements,
            "count": len(measurements),
            "exclude_cache": exclude_cache
        }
        
    except Exception as e:
        logger.error(f"Failed to get measurements for {endpoint}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve measurements: {str(e)}"
        )

@router.post("/latency/clear/{endpoint}")
async def clear_endpoint_stats(
    endpoint: str,
    user_id: Optional[str] = Query(None, description="Optional user ID to clear"),
    source: str = Query("memory", description="Data source to clear: 'memory' or 'database'"),
    db: Session = Depends(get_db)
):
    """
    Clear latency statistics for an endpoint.
    """
    try:
        if source == "memory":
            success = latency_tracker.clear_stats(endpoint, user_id)
            if success:
                message = f"Cleared memory stats for {endpoint}"
            else:
                message = f"Failed to clear memory stats for {endpoint}"
        elif source == "database":
            # For database, we could implement a method to delete records
            # For now, just return not implemented
            raise HTTPException(
                status_code=501,
                detail="Database clearing not implemented yet"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source. Must be 'memory' or 'database'"
            )
        
        return {
            "success": success,
            "message": message,
            "endpoint": endpoint,
            "user_id": user_id,
            "source": source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear stats for {endpoint}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear statistics: {str(e)}"
        )

@router.post("/latency/cleanup")
async def cleanup_old_data(
    days_to_keep: int = Query(7, description="Number of days of data to keep"),
    db: Session = Depends(get_db)
):
    """
    Clean up old latency measurement data from the database.
    """
    try:
        deleted_count = LatencyMetricService.cleanup_old_measurements(db, days_to_keep)
        
        return {
            "success": True,
            "message": f"Cleaned up {deleted_count} old measurements",
            "deleted_count": deleted_count,
            "days_kept": days_to_keep
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup data: {str(e)}"
        )

@router.get("/latency/debug")
async def debug_latency_data():
    """
    Debug endpoint to check what latency data is actually stored.
    """
    try:
        # Check Redis keys
        debug_info = {
            "redis_keys": [],
            "memory_keys": [],
            "sample_data": {}
        }
        
        # Get Redis keys if available
        try:
            from redis_cache.redis_cache import cache
            if hasattr(cache, 'redis_client'):
                keys = cache.redis_client.keys("latency:*")
                debug_info["redis_keys"] = [key.decode('utf-8') if isinstance(key, bytes) else str(key) for key in keys]
                
                # Get sample data for first few keys
                for key in debug_info["redis_keys"][:3]:
                    try:
                        data = cache.get(key)
                        debug_info["sample_data"][key] = {
                            "type": type(data).__name__,
                            "length": len(data) if isinstance(data, (list, str)) else "N/A",
                            "sample": str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                        }
                    except Exception as e:
                        debug_info["sample_data"][key] = f"Error reading: {e}"
        except Exception as e:
            debug_info["redis_error"] = str(e)
        
        # Check in-memory store
        try:
            memory_store = latency_tracker._memory_store
            debug_info["memory_keys"] = list(memory_store.keys())
        except Exception as e:
            debug_info["memory_error"] = str(e)
        
        # Test endpoint discovery
        try:
            endpoints = latency_tracker.get_all_endpoint_stats()
            debug_info["discovered_endpoints"] = list(endpoints.keys())
            debug_info["endpoint_stats"] = endpoints
        except Exception as e:
            debug_info["discovery_error"] = str(e)
        
        return {
            "success": True,
            "message": "Debug information for latency tracking",
            "debug_info": debug_info
        }
        
    except Exception as e:
        logger.error(f"Debug endpoint failed: {e}")
        return {
            "success": False,
            "message": f"Debug failed: {str(e)}"
        }

@router.get("/latency/health")
async def latency_tracking_health():
    """
    Health check for latency tracking system.
    """
    try:
        # Test in-memory tracker
        memory_stats = latency_tracker.get_latency_stats("health-check")
        memory_healthy = True
        
        # Test database connection
        try:
            db = next(get_db())
            db_stats = LatencyMetricService.calculate_stats_from_db(db, "health-check", hours_back=1)
            db_healthy = True
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            db_healthy = False
        finally:
            try:
                db.close()
            except Exception:
                pass
        
        return {
            "success": True,
            "message": "Latency tracking system health check",
            "components": {
                "memory_tracker": {
                    "healthy": memory_healthy,
                    "sample_stats": memory_stats
                },
                "database": {
                    "healthy": db_healthy
                }
            },
            "overall_healthy": memory_healthy and db_healthy
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "message": f"Health check failed: {str(e)}",
            "overall_healthy": False
        }

@router.delete("/latency/clear-all")
async def clear_all_latency_data(
    confirm: bool = Query(False, description="Set to true to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    Clear ALL latency data from both memory and database.
    This is a destructive operation and requires confirmation.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to proceed with deletion"
        )
    
    try:
        # Clear from memory/Redis
        memory_cleared = 0
        known_endpoints = ["enhanced-chat", "auth", "evaluation"]
        
        for endpoint in known_endpoints:
            success = latency_tracker.clear_stats(endpoint)
            if success:
                memory_cleared += 1
        
        # Clear from database
        from models.latency_metric import LatencyMetric
        deleted_count = db.query(LatencyMetric).delete()
        db.commit()
        
        logger.info(f"Cleared all latency data: {memory_cleared} memory endpoints, {deleted_count} DB records")
        
        return {
            "success": True,
            "message": "All latency data cleared successfully",
            "memory_endpoints_cleared": memory_cleared,
            "database_records_deleted": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear all latency data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear latency data: {str(e)}"
        )

@router.delete("/latency/clear-memory")
async def clear_memory_latency_data():
    """
    Clear latency data from memory/Redis only.
    """
    try:
        cleared_count = 0
        known_endpoints = ["enhanced-chat", "auth", "evaluation"]
        
        for endpoint in known_endpoints:
            success = latency_tracker.clear_stats(endpoint)
            if success:
                cleared_count += 1
        
        return {
            "success": True,
            "message": f"Cleared latency data from memory for {cleared_count} endpoints",
            "endpoints_cleared": cleared_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear memory latency data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear memory data: {str(e)}"
        )

@router.delete("/latency/clear-database")
async def clear_database_latency_data(
    confirm: bool = Query(False, description="Set to true to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    Clear latency data from database only.
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to proceed with deletion"
        )
    
    try:
        # Import the model here to avoid circular imports
        from models.latency_metric import LatencyMetric
        
        deleted_count = db.query(LatencyMetric).delete()
        db.commit()
        
        logger.info(f"Cleared {deleted_count} latency records from database")
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} latency records from database",
            "records_deleted": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear database latency data: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear database data: {str(e)}"
        )
