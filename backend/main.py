from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import logging
import time
import os
from datetime import datetime

from routes.health import router as health_router
from routes.enhanced_chat import router as enhanced_chat_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Legal Assistant",
        description="AI-powered legal document analysis and Q&A system",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None)

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
     allow_origins=["*"] if os.getenv("ENVIRONMENT") == "development" else [
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],  # Allow all headers
)

app.include_router(health_router)
app.include_router(enhanced_chat_router, prefix="/api")

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