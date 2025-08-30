import psutil
import time
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from datetime import datetime
from typing import Dict, Any

from services import openai_service

logger = logging.getLogger(__name__)
router = APIRouter()

app_start_time = time.time()
    
@router.get("/health/ready")
async def readiness_check():
    """Kubernetes-style readiness probe with subsystem statuses."""
    checks = {}
    # existing vector store check (keeps same logic)
    try:
        vector_ok = await _check_vector_store()
        checks["vector_store"] = "ok" if vector_ok else "unavailable"
    except Exception as e:
        logger.warning(f"Vector store health check failed: {e}")
        checks["vector_store"] = "error"

    # OpenAI check (non-blocking, lightweight)
    try:
        openai_ok = await openai_service.ping()
        checks["openai"] = "ok" if openai_ok else "degraded"
    except Exception as e:
        logger.warning(f"OpenAI health check raised: {e}")
        checks["openai"] = "error"

    # Basic system checks
    memory_percent = psutil.virtual_memory().percent
    cpu_percent = psutil.cpu_percent(interval=0.1)
    system_ok = memory_percent < 95 and cpu_percent < 95
    checks["system"] = "ok" if system_ok else "degraded"

    # Overall readiness: degraded if any critical subsystem is unavailable
    if checks.get("vector_store") != "ok":
        status = "unready"
        code = 503
    else:
        # allow degraded openai to still be considered ready (app can serve cached / non-AI endpoints)
        status = "ready"
        code = 200

    payload = {
        "status": status,
        "subsystems": checks,
        "timestamp": datetime.utcnow().isoformat()
    }

    return JSONResponse(status_code=code, content=payload)

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