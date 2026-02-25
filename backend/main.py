from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import time
import os
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

load_dotenv()

from redis_cache.redis_cache import cache 
from routes.enhanced_chat import router as enhanced_chat_router
from routes.evaluation import router as evaluation_router
from routes.auth import router as auth_router
from routes.eval_dashboard import router as eval_dashboard
from routes.latency_metrics import router as latency_metrics_router
from routes.cache_management import router as cache_management_router
from chain.retriever import enhanced_retriever

from config.settings import settings
from config.database import get_db, db_manager
from middleware.cost_monitoring_middleware import CostMonitoringMiddleware

os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.langsmith_api_key and not os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = f"ai-legal-assistant-{settings.environment}"

app = FastAPI(
    title="AI Legal Assistant",
        description="AI-powered legal document analysis and Q&A system",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if os.getenv("ENVIRONMENT") == "development" else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Default Vite dev port
        "http://127.0.0.1:5173"   # Default Vite dev port with 127.0.0.1
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(CostMonitoringMiddleware)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request (production-safe)
    logger.info(f"🚀 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"✅ {response.status_code} - {process_time:.4f}s")
    
    return response

app.include_router(auth_router, prefix="/api", tags=["authentication"])
app.include_router(enhanced_chat_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api", tags=["evaluation"])
app.include_router(eval_dashboard, prefix="/api", tags=["evaluation-dashboard"])
app.include_router(latency_metrics_router, prefix="/api", tags=["latency-metrics"])
app.include_router(cache_management_router, prefix="/api", tags=["cache-management"])

@app.on_event("startup")
async def load_sbert_reranker():
    if enhanced_retriever:
        print("🔄 Loading SBERT reranker model at startup...")
        enhanced_retriever._ensure_reranker_loaded()
        if getattr(enhanced_retriever, "_reranker_model", None) is not None:
            print("✅ SBERT reranker loaded successfully.")
        else:
            print("⚠️  SBERT reranker could not be loaded.")
    else:
        print("⚠️  Enhanced retriever not available; SBERT reranker not loaded.")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected errors gracefully"""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error" if settings.is_production else str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # Detect if running under debugger
    is_debugging = hasattr(sys, 'gettrace') and sys.gettrace() is not None
    
    uvicorn.run(
        "main:app" if not is_debugging else app,  # Use app object when debugging
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development" and not is_debugging  # Disable reload when debugging
    )