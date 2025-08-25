import psutil
import time
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

app_start_time = time.time()

@router.get("/health")
async def health_check():
    """Comprehensive health check for AWS ALB"""
    try:
        # Check system resources
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent(interval=0.1)
        disk_percent = psutil.disk_usage('/').percent

        # Check vector store
        vector_store_healthy = await _check_vector_store()

        # Overall health status
        healthy = (
            memory_percent < 90 and
            cpu_percent < 90 and
            disk_percent < 90 and
            vector_store_healthy
        )

        status_code = 200 if healthy else 503

        health_data = {
            "status": "healthy" if healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(time.time() - app_start_time),
            "system": {
                "memory_percent": round(memory_percent, 2),
                "cpu_percent": round(cpu_percent, 2),
                "disk_percent": round(disk_percent, 2)
            },
            "services": {
                "vector_store": "healthy" if vector_store_healthy else "unhealthy"
            }
        }
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
@router.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check if all critical services are ready
        vector_store_ready = await _check_vector_store()
        
        if not vector_store_ready:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "vector_store_not_ready"}
            )
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)}
        )
    
@router.get("/health/live")
async def liveness_check():
    """Kubernetes-style liveness probe - simple check"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - app_start_time)
    }

@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus-style metrics endpoint"""
    try:
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent()
        disk = psutil.disk_usage('/')
        
        # Check vector store status
        vector_store_status = 1 if await _check_vector_store() else 0
        
        metrics = [
            f"# HELP system_memory_usage_percent Current memory usage percentage",
            f"# TYPE system_memory_usage_percent gauge",
            f"system_memory_usage_percent {memory.percent}",
            f"",
            f"# HELP system_cpu_usage_percent Current CPU usage percentage",
            f"# TYPE system_cpu_usage_percent gauge", 
            f"system_cpu_usage_percent {cpu_percent}",
            f"",
            f"# HELP system_disk_usage_percent Current disk usage percentage",
            f"# TYPE system_disk_usage_percent gauge",
            f"system_disk_usage_percent {disk.percent}",
            f"",
            f"# HELP app_uptime_seconds Application uptime in seconds",
            f"# TYPE app_uptime_seconds counter",
            f"app_uptime_seconds {int(time.time() - app_start_time)}",
            f"",
            f"# HELP vector_store_status Vector store health status (1=healthy, 0=unhealthy)",
            f"# TYPE vector_store_status gauge",
            f"vector_store_status {vector_store_status}",
        ]
        
        return Response(
            content="\n".join(metrics),
            media_type="text/plain"
        )
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")
    
@router.get("/version")
async def version_info():
    """Application version and build information"""
    import os
    
    return {
        "version": "1.0.0",
        "build_time": os.getenv("BUILD_TIME", "unknown"),
        "git_commit": os.getenv("GIT_COMMIT", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": os.getenv("PYTHON_VERSION", "unknown")
    }

async def _check_vector_store() -> bool:
    """Internal function to check vector store health"""
    try:
        from chain.loader import vectorstore
        # Simple test query with timeout
        test_docs = vectorstore.similarity_search("test health check", k=1)
        return True
    except Exception as e:
        logger.warning(f"Vector store health check failed: {e}")
        return False