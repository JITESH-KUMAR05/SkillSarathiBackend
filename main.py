#!/usr/bin/env python3
"""
BuddyAgents Backend Server
Main entry point for the FastAPI application with GitHub token fallback and streaming support.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

import uvicorn
from app.main import app
from app.database import init_db

async def startup():
    """Initialize the application"""
    print("🚀 Starting BuddyAgents Backend...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    print("✅ BuddyAgents Backend is ready!")
    print("📡 Server will start on http://0.0.0.0:8000")
    print("📚 API docs available at http://0.0.0.0:8000/docs")
    print("🔧 WebSocket streaming enabled for minimal latency")
    print("🔑 GitHub token fallback configured for LLM access")

def main():
    """Main entry point"""
    # Run startup
    asyncio.run(startup())
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],
        log_level="info"
    )

if __name__ == "__main__":
    main()
