"""FastAPI application for AI Multi-Agent Companion Platform with WebSocket streaming."""

from fastapi import FastAPI, HTTPException, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import uuid

from app.rag.enhanced_rag_system import enhanced_rag_system
from app.websocket_handler import websocket_endpoint, websocket_manager
from app.api import auth as auth_api
from app.api import agents as agents_api
from app.api import chat as chat_api
from app.api import documents as documents_api
from app.api import profiles as profiles_api
from app.api.routes import enhanced_chat as enhanced_chat_api
from app.auth.dependencies import get_current_active_user
from app.database.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("🚀 Starting AI Multi-Agent Companion Platform...")
    print("✅ Enhanced RAG system loaded")
    print("✅ Platform ready to serve!")
    
    yield
    
    # Shutdown
    print("👋 Shutting down platform...")


# Create FastAPI application
app = FastAPI(
    title="AI Multi-Agent Companion for India",
    description="Sophisticated AI companion platform with three specialized agents",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production via settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_api.router, prefix="/auth", tags=["auth"])
app.include_router(profiles_api.router, prefix="/api/profiles", tags=["profiles"])
app.include_router(agents_api.router, prefix="/api/agents", tags=["agents"])
app.include_router(chat_api.router, prefix="/api/chat", tags=["chat"])
app.include_router(documents_api.router, prefix="/api/documents", tags=["documents"])
app.include_router(enhanced_chat_api.router, prefix="/api", tags=["enhanced-chat"])


@app.get("/")
async def root():
    """Root endpoint with platform information"""
    return {
        "message": "Welcome to AI Multi-Agent Companion for India! 🇮🇳",
        "platform": "AI Multi-Agent Companion",
        "version": "1.0.0",
        "agents": {
            "mitra": "🤝 Companion - Personal friend and emotional support",
            "guru": "🎓 Mentor - Career guidance and skill development", 
            "parikshak": "💼 Interviewer - Interview preparation and practice"
        },
        "features": [
            "Bilingual support (English/Hindi)",
            "Indian cultural context awareness", 
            "Personalized user profiling",
            "Shared knowledge base",
            "Real-time conversation streaming"
        ],
        "status": "ready"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Quick test of RAG system
        test_result = await enhanced_rag_system.search_shared_knowledge(
            query="test health check",
            k=1
        )
        
        return {
            "status": "healthy",
            "rag_system": "operational",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/agents")
async def list_agents():
    """List available agents and their capabilities"""
    return {
        "agents": [
            {
                "id": "mitra",
                "name": "Mitra (Companion)",
                "type": "companion",
                "description": "Personal friend and emotional support agent",
                "capabilities": [
                    "Personal conversation and emotional support",
                    "Cultural context and Indian communication patterns",
                    "Family and relationship discussions",
                    "Lifestyle and hobby conversations",
                    "Bilingual support (English/Hindi)",
                    "Festival and cultural event discussions"
                ],
                "personality": "Warm, empathetic, culturally aware"
            },
            {
                "id": "guru", 
                "name": "Guru (Mentor)",
                "type": "mentor",
                "description": "Professional development and career guidance agent",
                "capabilities": [
                    "Career guidance and planning",
                    "Technical concept explanations",
                    "Skill development recommendations", 
                    "Resume and LinkedIn optimization",
                    "Indian job market insights",
                    "Learning path creation",
                    "Professional communication coaching"
                ],
                "personality": "Authoritative yet encouraging, patient"
            },
            {
                "id": "parikshak",
                "name": "Parikshak (Interviewer)", 
                "type": "interview",
                "description": "Interview preparation and professional assessment agent",
                "capabilities": [
                    "Mock technical interviews",
                    "Behavioral interview practice",
                    "Communication skills assessment",
                    "Performance feedback and scoring",
                    "Company-specific interview prep",
                    "Real-time interview simulation",
                    "Improvement recommendations"
                ],
                "personality": "Professional, adaptable, constructively critical"
            }
        ]
    }


@app.get("/knowledge/search")
async def search_knowledge(query: str, category: Optional[str] = None, limit: int = 5):
    """Search the shared knowledge base"""
    try:
        results = await enhanced_rag_system.search_shared_knowledge(
            query=query,
            category=category,
            k=limit
        )
        
        return {
            "query": query,
            "category": category,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.post("/chat")
async def direct_chat(message: dict):
    """Direct chat endpoint for Streamlit interface"""
    try:
        user_message = message.get("message", "")
        agent_type = message.get("agent", "companion")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Import LLM factory here to avoid circular imports
        from app.llm.llm_factory import get_llm
        
        # Get real LLM instance
        llm = get_llm()
        
        # Agent-specific system prompts
        agent_prompts = {
            "companion": """You are Sakhi, a warm and caring AI companion designed for Indian users. 
You provide emotional support, friendly conversation, and cultural understanding. 
Respond with empathy, warmth, and cultural sensitivity. Keep responses conversational and supportive.""",
            
            "mentor": """You are Guru, a wise AI mentor focused on career development and learning for Indian professionals.
You provide educational guidance, career advice, and skill development recommendations.
Be knowledgeable, encouraging, and provide practical advice relevant to the Indian context.""",
            
            "interview": """You are Parikshak, an AI interview coach specializing in Indian job market preparation.
You help with interview practice, behavioral questions, and professional development.
Be professional, constructive, and provide actionable feedback for interview improvement."""
        }
        
        system_prompt = agent_prompts.get(agent_type, agent_prompts["companion"])
        
        # Create conversation context
        conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Get AI response using the real LLM
        try:
            ai_response = await llm.generate_response(conversation)
            
            return {
                "response": ai_response,
                "agent": agent_type,
                "timestamp": "2024-01-01T00:00:00Z",
                "real_ai": True
            }
            
        except Exception as llm_error:
            # Fallback response if LLM fails
            fallback_responses = {
                "companion": f"I understand you're sharing something important with me. While I'm having some technical issues, I want you to know I'm here for you. You mentioned: '{user_message[:100]}...' - let's talk more about this.",
                "mentor": f"Thank you for your question about '{user_message[:100]}...' - I'm experiencing some technical difficulties, but I'm committed to helping you grow and learn. Let me try to address your concern.",
                "interview": f"I see you're working on interview preparation with '{user_message[:100]}...' - while I'm having some connectivity issues, practice is key to improvement. Let's continue working together."
            }
            
            return {
                "response": fallback_responses.get(agent_type, "I'm experiencing technical issues but I'm here to help you."),
                "agent": agent_type,
                "timestamp": "2024-01-01T00:00:00Z",
                "real_ai": False,
                "error": str(llm_error)
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@app.post("/demo/chat")
async def demo_chat(message: dict):
    """Demo endpoint for testing chat functionality"""
    try:
        user_message = message.get("content", "")
        if not user_message:
            raise HTTPException(status_code=400, detail="Message content is required")
        
        # Simple demo response based on keywords
        response = "Thank you for your message! "
        
        if any(word in user_message.lower() for word in ["career", "job", "work"]):
            response += "I'm Guru, your mentor. I'd be happy to help with your career goals!"
        elif any(word in user_message.lower() for word in ["interview", "practice", "prepare"]):
            response += "I'm Parikshak, your interview coach. Let's practice and improve your skills!"
        else:
            response += "I'm Mitra, your companion. How are you feeling today?"
        
        return {
            "response": response,
            "agent_type": "demo",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


# Update the WebSocket endpoint to use port 8000
@app.websocket("/ws")
async def websocket_stream(websocket: WebSocket):
    """WebSocket endpoint for minimal latency streaming"""
    await websocket_endpoint(websocket)


@app.get("/ws/health")
async def websocket_health():
    """WebSocket health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(websocket_manager.active_connections),
        "streaming_enabled": True,
        "murf_integration": True
    }


@app.get("/auth/me")
async def auth_me(current_user: User = Depends(get_current_active_user)):
    """Return current authenticated user profile"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0", 
        port=8000,
        reload=True
    )
