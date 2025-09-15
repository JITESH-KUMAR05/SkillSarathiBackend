"""
Production BuddyAgents Backend API
==================================

A comprehensive AI multi-agent platform with:
- Dual-region Azure OpenAI with Model Router (GPT-5, GPT-4.1)
- Sora video generation for interview scenarios
- GPT-Realtime for speech-to-speech conversations  
- GPT-4o-Transcribe for advanced audio processing
- Multi-agent system (Mitra, Guru, Parikshak)
- Enterprise security with authentication and rate limiting
- WebSocket streaming for real-time communication
- Production monitoring and health checks
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Configuration and security
from app.core.config import get_settings, AgentConfig
from app.core.security import SecurityMiddleware, limiter

# Database setup
from app.database.base import engine, Base
from app.database.models import User, Document, Conversation

# API routes
from app.api.auth import router as auth_router
from app.api.chat_router import router as chat_router
from app.api.voice_router import router as voice_router
from app.api.video_router import router as video_router
from app.api.user_router import router as user_router

# Services
from app.services.azure_openai_service import azure_openai_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('buddyagents.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks"""
    
    # Startup
    logger.info("🚀 Starting BuddyAgents Platform...")
    
    try:
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized successfully")
        
        # Health check Azure OpenAI services
        primary_health = await azure_openai_service.health_check()
        if primary_health["healthy"]:
            logger.info("✅ Azure OpenAI Primary region (East US 2) healthy")
        else:
            logger.warning("⚠️ Azure OpenAI Primary region health check failed")
        
        secondary_health = await azure_openai_service.health_check(region="secondary")
        if secondary_health["healthy"]:
            logger.info("✅ Azure OpenAI Secondary region (Sweden Central) healthy")
        else:
            logger.warning("⚠️ Azure OpenAI Secondary region health check failed")
        
        # Log available agents
        agents = AgentConfig.get_all_agents()
        logger.info(f"✅ Available agents: {', '.join(agents)}")
        
        logger.info("🎉 BuddyAgents Platform started successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down BuddyAgents Platform...")
    logger.info("✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="BuddyAgents Platform API",
    description="Production-ready AI multi-agent platform for Indian users",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add trusted host middleware for production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.buddyagents.com"]
    )

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Check Azure OpenAI services
        primary_health = await azure_openai_service.health_check()
        secondary_health = await azure_openai_service.health_check(region="secondary")
        
        # Check database
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            db_healthy = True
        except Exception:
            db_healthy = False
        
        overall_health = (
            primary_health["healthy"] and 
            secondary_health["healthy"] and 
            db_healthy
        )
        
        return {
            "status": "healthy" if overall_health else "degraded",
            "timestamp": primary_health["timestamp"],
            "services": {
                "azure_openai_primary": primary_health,
                "azure_openai_secondary": secondary_health,
                "database": {"healthy": db_healthy},
                "agents": {
                    "available": AgentConfig.get_all_agents(),
                    "count": len(AgentConfig.get_all_agents())
                }
            },
            "version": "2.0.0",
            "environment": "production" if not settings.debug else "development"
        }
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": "2025-09-14T00:00:00Z"
            }
        )

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(voice_router, prefix="/api/voice", tags=["Voice"])
app.include_router(video_router, prefix="/api/video", tags=["Video"])
app.include_router(user_router, prefix="/api/user", tags=["User Management"])

# Serve static files
app.mount("/static", StaticFiles(directory="uploads"), name="static")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "BuddyAgents Platform API",
        "version": "2.0.0",
        "description": "Production-ready AI multi-agent platform",
        "features": [
            "Model Router with GPT-5 and GPT-4.1",
            "Sora video generation",
            "GPT-Realtime speech-to-speech",
            "GPT-4o-Transcribe audio processing",
            "Multi-agent system (Mitra, Guru, Parikshak)",
            "Enterprise security and rate limiting"
        ],
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.debug:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )
    }
        )


if __name__ == "__main__":
    """Run the application"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    
    # Startup
    logger.info("🚀 Starting BuddyAgents Backend...")
    
    try:
        # Initialize database
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized")
        
        # Validate Murf API setup
        murf_api_key = os.getenv("MURF_API_KEY")
        if murf_api_key and murf_api_key != "your_murf_api_key_here":
            logger.info("✅ Murf AI API validated")
            
            # Test all agent voices
            for agent in ["mitra", "guru", "parikshak"]:
                voice_config = get_agent_voice(agent)
                voice_id = voice_config["voice_id"]
                logger.info(f"✅ {agent.title()} voice: {voice_config['description']} ({voice_config['language']})")
        else:
            logger.warning("⚠️ Murf AI setup validation failed - check MURF_API_KEY")
        
        logger.info("🎉 BuddyAgents Backend ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down BuddyAgents Backend...")

# Initialize FastAPI app
app = FastAPI(
    title="BuddyAgents API",
    description="Multi-agent AI companion platform for India",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(chat_router, prefix="/chat-simple", tags=["Simple Chat"])  # Also mount at /chat-simple
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(profiles_router, prefix="/api/profiles", tags=["Profiles"])
app.include_router(ai_features_router, tags=["Advanced AI Features"])  # Model Router, Sora, Transcription

# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat and voice streaming"""
    await websocket_handler.handle_connection(websocket, user_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "BuddyAgents Backend",
        "version": "1.0.0",
        "features": [
            "multi_agent_chat",
            "voice_synthesis", 
            "websocket_streaming",
            "rag_system"
        ]
    }

@app.get("/agents")
async def get_agents():
    """Get available agents"""
    return {
        "agents": [
            {
                "id": "mitra",
                "name": "Mitra (मित्र)",
                "emoji": "🤗",
                "description": "Your caring friend for emotional support",
                "color": "#FF6B6B",
                "role": "friend",
                "voice": "shweta"
            },
            {
                "id": "guru",
                "name": "Guru (गुरु)",
                "emoji": "🎓", 
                "description": "Your learning mentor for growth",
                "color": "#4ECDC4",
                "role": "mentor",
                "voice": "eashwar"
            },
            {
                "id": "parikshak",
                "name": "Parikshak (परीक्षक)",
                "emoji": "💼",
                "description": "Your interview coach for career success", 
                "color": "#45B7D1",
                "role": "coach",
                "voice": "isha"
            }
        ]
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "🙏 Welcome to BuddyAgents API",
        "agents": ["mitra", "guru", "parikshak"],
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat/",
            "websocket": "/ws/{user_id}",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
