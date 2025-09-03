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
from routes.health import router as health_router
from routes.enhanced_chat import router as enhanced_chat_router
from routes.evaluation import router as evaluation_router
from routes.auth import router as auth_router
from routes.rerank_weights import router as rerank_weights_router
from routes.eval_dashboard import router as eval_dashboard
from config.settings import settings
from config.database import get_db, db_manager
from middleware.rate_limit_middleware import RateLimitMiddleware
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
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(
    RateLimitMiddleware,
    skip_paths=["/docs", "/redoc", "/openapi.json", "/health/live"]  # Skip docs and basic health
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

app.include_router(health_router)
app.include_router(auth_router, prefix="/api", tags=["authentication"])
app.include_router(enhanced_chat_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api", tags=["evaluation"])
app.include_router(rerank_weights_router, prefix="/api", tags=["rerank-weights"])
app.include_router(eval_dashboard, prefix="/api", tags=["evaluation-dashboard"])

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
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )