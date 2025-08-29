"""
Production BuddyAgents Backend
=============================

A comprehensive AI multi-agent platform with:
- WebSocket streaming for real-time communication
- Murf AI voice synthesis integration
- Advanced RAG with personalized memory
- GitHub Copilot LLM integration
- Multi-agent system (Mitra, Guru, Parikshak)
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
from app.api.chat_simple import router as chat_router  # Use the working simple chat API
from app.api.documents_simple import router as documents_router  # Simple documents without RAG
from app.api.agents import router as agents_router
from app.api.profiles_simple import router as profiles_router  # Simple profiles without RAG

# WebSocket handler  
from app.websocket_handler import websocket_handler

# Core services
from app.murf_streaming import murf_client
from app.voice_config import get_agent_voice, get_voice_info

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
