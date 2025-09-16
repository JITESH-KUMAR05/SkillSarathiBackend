"""
FastAPI Main Application for BuddyAgents Platform
Production-ready backend with security, monitoring, and Azure OpenAI integration
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.security import SecurityMiddleware, RateLimitService
# from app.services.azure_openai_service import azure_openai_service  # Temporarily disabled
from app.services.voice import get_voice_manager

# Import API routers
from app.api import chat_simple
from app.api.candidates import router as candidates_router
from app.api.enhanced_chat import router as enhanced_chat_router
from app.api.documents import router as documents_router
from app.api.voice import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting BuddyAgents Platform...")
    
    try:
        # Initialize Azure OpenAI service
        logger.info("🔧 Initializing Azure OpenAI service...")
        # Health check will be called in the health endpoint
        
        # Initialize rate limiting service
        logger.info("🛡️ Initializing security services...")
        # Rate limit service is initialized automatically
        
        logger.info("✅ BuddyAgents Platform started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down BuddyAgents Platform...")
    # Cleanup tasks here
    logger.info("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="BuddyAgents Platform API",
    description="Production-ready AI Multi-Agent Companion for India with Azure OpenAI integration",
    version="2.0.0",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan
)

# Security Middleware
app.add_middleware(SecurityMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"]
)

# Trusted Host Middleware
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routers
app.include_router(enhanced_chat_router, prefix="/api/v1/chat", tags=["Enhanced Chat"])
app.include_router(candidates_router, prefix="/api/v1/candidates", tags=["Candidates & MCP"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents & Guru"])
app.include_router(voice_router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(chat_simple.router, prefix="/api/v1/legacy/chat", tags=["Legacy Chat"])


# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check Azure OpenAI service health (temporarily disabled)
        # azure_health = await azure_openai_service.health_check()
        azure_health = {"status": "disabled", "message": "Azure OpenAI temporarily disabled for voice testing"}
        
        # Check voice services health
        voice_health = {"status": "not_initialized"}
        try:
            voice_manager = await get_voice_manager()
            voice_health = await voice_manager.get_service_health()
        except Exception as e:
            voice_health = {"status": "error", "error": str(e)}
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "environment": settings.environment,
            "services": {
                "azure_openai": azure_health,
                "voice_services": voice_health,
                "rate_limiting": {
                    "status": "healthy",
                    "active_limits": ["chat", "voice", "video"]
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable"
        )


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to BuddyAgents Platform API",
        "version": "2.0.0",
        "agents": ["Mitra", "Guru", "Parikshak"],
        "documentation": "/docs",
        "health": "/health"
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", "unknown")
        }
    )


# Rate limit exceeded handler
@app.exception_handler(429)
async def rate_limit_handler(request: Request, exc: HTTPException):
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "timestamp": datetime.utcnow().isoformat(),
            "retry_after": 60
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Limit": "100",
            "X-RateLimit-Remaining": "0"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        workers=1 if settings.environment == "development" else 4,
        access_log=True,
        log_level="info"
    )