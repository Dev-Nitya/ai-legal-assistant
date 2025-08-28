from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import time
import os
from datetime import datetime

load_dotenv()

from routes.health import router as health_router
from routes.enhanced_chat import router as enhanced_chat_router
from routes.evaluation import router as evaluation_router
from routes.auth import router as auth_router
from config.settings import settings
from middleware.rate_limit_middleware import RateLimitMiddleware
from middleware.request_size_middleware import RequestSizeMiddleware
from middleware.request_timeout_middleware import TimeoutProtectionMiddleware
from middleware.cost_monitoring_middleware import CostMonitoringMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.langsmith_api_key:
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
    RequestSizeMiddleware,
    max_content_kb=100,  # 100KB max content
    max_headers_kb=10    # 10KB max headers
)
app.add_middleware(TimeoutProtectionMiddleware, timeout_seconds=30)
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

@app.get("/")
async def root():
    return {
        "message": "AI Legal Assistant API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics", 
            "chat": "/api/chat",
            "docs": "/docs" if os.getenv("ENVIRONMENT") != "production" else "disabled"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT") == "development"
    )