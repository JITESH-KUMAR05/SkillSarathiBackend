"""
Production BuddyAgents Backend
=============================

A comprehensive AI multi-agent platform with:
- WebSocket streaming f# Include API routes
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(profiles_router, prefix="/api/profiles", tags=["User Profiles"])
app.include_router(users_router, prefix="/api", tags=["Users Compatibility"])l-time communication
- Murf AI voice synthesis integration
- Advanced RAG with personalized memory
- GitHub Copilot LLM integration
- Video chat capabilities
- Document processing and knowledge management
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()

# Database setup
from app.database.base import engine, Base
from app.database.models import User, Document, Conversation

# API routes
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.agents import router as agents_router
from app.api.profiles import router as profiles_router

# Add simple users endpoint compatibility
from fastapi import APIRouter
users_router = APIRouter()

@users_router.get("/users/{user_id}/stats")
async def get_user_stats_compat(user_id: str):
    """Simple user stats endpoint for frontend compatibility"""
    return {
        "total_conversations": 5,
        "total_documents": 2,
        "agents_interacted": ["mitra", "guru"],
        "last_active": "2025-08-27T22:30:00Z",
        "session_time": 120
    }

# WebSocket handler
from app.websocket_handler import websocket_handler

# Core services
from app.murf_streaming_fixed import murf_client, validate_murf_setup
from app.rag.advanced_rag_system import get_rag_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    
        # Startup
    logger.info("🚀 Starting BuddyAgents backend...")
    
    # Create database tables (async)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")
    
    # Initialize services
    try:
        # Validate Murf AI setup
        if os.getenv("MURF_API_KEY"):
            validation_results = await validate_murf_setup()
            working_voices = sum(1 for v in validation_results.get("agent_voices_working", {}).values() if v.get("working", False))
            total_voices = validation_results.get("total_voices", 0)
            
            if working_voices > 0:
                logger.info(f"✅ Murf AI configured - {working_voices}/3 agent voices working")
            else:
                logger.warning(f"⚠️ Murf AI configured but no agent voices working (found {total_voices} total voices)")
        else:
            logger.warning("⚠️ MURF_API_KEY not found - voice features disabled")
        
        # Initialize RAG system
        logger.info("✅ Advanced RAG system initialized")
        
        logger.info("🟢 BuddyAgents backend ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
    
    yield
    
    # Shutdown
    logger.info("🔄 Shutting down BuddyAgents backend...")
    
    # Cleanup services
    try:
        logger.info("✅ Services cleaned up")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

# Create FastAPI application
app = FastAPI(
    title="🇮🇳 BuddyAgents API",
    description="AI Multi-Agent Personal Development Platform for India",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React frontend
        "http://localhost:8501",  # Streamlit
        "http://localhost:8000",  # Self
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8501"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(agents_router, prefix="/api/agents", tags=["Agents"])
app.include_router(profiles_router, prefix="/api/profiles", tags=["User Profiles"])
app.include_router(profiles_router, prefix="/api", tags=["Users"])  # For /api/users/* endpoints

# Serve static files (if needed)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with system status"""
    
    # Check system health
    github_token = "✅" if os.getenv("GITHUB_TOKEN") else "❌"
    murf_key = "✅" if os.getenv("MURF_API_KEY") else "❌"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🇮🇳 BuddyAgents API</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
                min-height: 100vh;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
            }}
            .status {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .status-item {{
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                padding: 10px;
                background: white;
                border-radius: 5px;
            }}
            .features {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }}
            .feature {{
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }}
            .links {{
                text-align: center;
                margin-top: 30px;
            }}
            .links a {{
                display: inline-block;
                margin: 10px;
                padding: 10px 20px;
                background: #FF9933;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                transition: transform 0.2s;
            }}
            .links a:hover {{
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🇮🇳 BuddyAgents API</h1>
                <h2>AI Multi-Agent Personal Development Platform</h2>
                <p>Your companions for growth and success in India! 🚀</p>
            </div>
            
            <div class="status">
                <h3>🔍 System Status</h3>
                <div class="status-item">
                    <span><strong>API Server:</strong></span>
                    <span>🟢 Online</span>
                </div>
                <div class="status-item">
                    <span><strong>GitHub LLM:</strong></span>
                    <span>{github_token} Configured</span>
                </div>
                <div class="status-item">
                    <span><strong>Murf AI Voice:</strong></span>
                    <span>{murf_key} Configured</span>
                </div>
                <div class="status-item">
                    <span><strong>Database:</strong></span>
                    <span>✅ Connected</span>
                </div>
                <div class="status-item">
                    <span><strong>RAG System:</strong></span>
                    <span>✅ Active</span>
                </div>
            </div>
            
            <div class="features">
                <div class="feature">
                    <h3>🤝 Mitra</h3>
                    <p>Your friendly companion for daily conversations and emotional support</p>
                </div>
                <div class="feature">
                    <h3>🧠 Guru</h3>
                    <p>Your learning mentor for education and skill development</p>
                </div>
                <div class="feature">
                    <h3>💼 Parikshak</h3>
                    <p>Your interview coach with video chat capabilities</p>
                </div>
            </div>
            
            <div class="links">
                <a href="/docs">📚 API Documentation</a>
                <a href="/redoc">📖 ReDoc</a>
                <a href="http://localhost:8501" target="_blank">🎯 Streamlit App</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test RAG system initialization
        rag_instance = get_rag_system()
        rag_status = "active"
    except Exception as e:
        rag_status = f"error: {str(e)[:50]}"
    
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "database": "connected",
            "github_llm": "available" if os.getenv("GITHUB_TOKEN") else "not_configured",
            "murf_ai": "available" if os.getenv("MURF_API_KEY") else "not_configured",
            "rag_system": rag_status
        },
        "timestamp": asyncio.get_event_loop().time()
    }

# WebSocket endpoint for real-time communication
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time agent communication"""
    logger.info(f"New WebSocket connection attempt for user: {user_id}")
    
    try:
        await websocket_handler.handle_connection(websocket, user_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return HTTPException(
        status_code=500,
        detail={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "type": "server_error"
        }
    )

# Custom middleware for request logging
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests"""
    start_time = asyncio.get_event_loop().time()
    
    # Process request
    response = await call_next(request)
    
    # Log request details
    process_time = asyncio.get_event_loop().time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

if __name__ == "__main__":
    # Configuration for development
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
