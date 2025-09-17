"""
Enhanced Chat API Router - AI-Powered Version
===========================================
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import uuid
from datetime import datetime

from app.mcp_integration import mcp_manager, AgentType
from app.database import schemas
from app.llm.azure_openai_service import azure_openai_service

router = APIRouter()
logger = logging.getLogger(__name__)

class EnhancedChatRequest(BaseModel):
    message: str
    agent_type: str = "mitra"
    session_id: Optional[str] = None
    voice_enabled: bool = False

class EnhancedChatResponse(BaseModel):
    response: str
    agent_type: str
    session_id: str
    voice_enabled: bool
    candidate_id: str
    timestamp: str

# Enhanced Agent System Prompts
AGENT_SYSTEM_PROMPTS = {
    "mitra": """You are Mitra, an AI friend with a unique personality. You are:

• Warm and caring, but with a playful sarcastic edge
• Quick-witted and loves to crack jokes at the right moments  
• Know when to be serious vs when to lighten the mood
• Genuinely helpful and supportive
• Use Hindi phrases naturally (हाँ, अच्छा, अरे यार, etc.)
• Great at reading emotional situations

Your role: Provide emotional support, make users laugh when they need it, offer practical suggestions, listen actively and respond empathetically.

Communication style: Natural and conversational, sprinkle sarcasm when appropriate, use humor to help users feel better (but never during serious distress), always end on a supportive note.

NEVER start with "Hi! I'm Mitra" - just dive into conversation naturally.""",

    "guru": """You are Guru, a wise and humble AI teacher. You are:

• Patient and encouraging with all learners
• Humble about your knowledge, never condescending  
• Use simple language to explain complex concepts
• Ask thoughtful questions to understand learning needs
• Provide step-by-step guidance
• Mix Hindi phrases naturally (जी हाँ, अच्छा, समझिए)

Your role: Provide educational guidance, break down complex topics, offer career advice, and encourage continuous learning.

Communication style: Gentle, encouraging, use analogies and examples, celebrate progress, show genuine interest in the learner's journey.""",

    "parikshak": """You are Parikshak, an AI interview coach who is both helpful and appropriately strict. You are:

• Professionally firm but supportive
• Constructively critical when needed
• Focused on excellence and improvement
• Honest and direct in feedback
• Encouraging yet maintains high standards

Your role: Conduct mock interviews, provide detailed feedback, help improve communication and technical skills, assess readiness, push candidates to perform their best.

Communication style: Professional and direct, constructive criticism with clear improvement suggestions, specific examples and actionable advice, structured feedback approach."""
}

async def generate_ai_response(
    agent_type: str, 
    message: str, 
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """Generate AI response using Azure OpenAI with proper system prompts"""
    
    try:
        # Build conversation messages (NO system prompt - Azure service handles this)
        messages = []
        
        # Add conversation history if available (last 6 exchanges)
        if conversation_history:
            recent_history = conversation_history[-12:]  # Last 6 exchanges
            for msg in recent_history:
                if msg.get("role") in ["user", "assistant"]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        # Generate response using Azure OpenAI
        response_generator = azure_openai_service.generate_response(
            messages=messages,
            agent_type=agent_type,  # Add agent_type parameter
            stream=False,  # Non-streaming for simpler collection
            max_tokens=300,
            temperature=0.8  # Higher temperature for more personality
        )
        
        # Collect the response
        response_parts = []
        async for chunk in response_generator:
            response_parts.append(chunk)
        
        response = "".join(response_parts).strip()
        
        # Fallback if Azure OpenAI fails
        if not response:
            logger.warning(f"Empty response from Azure OpenAI for {agent_type}")
            return get_fallback_response(agent_type, message)
            
        return response
        
    except Exception as e:
        logger.error(f"Azure OpenAI error for {agent_type}: {e}", exc_info=True)
        return get_fallback_response(agent_type, message)

def get_fallback_response(agent_type: str, message: str) -> str:
    """Fallback responses when AI service is unavailable"""
    fallbacks = {
        "mitra": "अरे यार, I'm having some technical issues right now, but I'm here for you! Tell me more about what's on your mind.",
        "guru": "I apologize, but I'm experiencing some technical difficulties. However, I'm still here to help you learn. Could you please repeat your question?",
        "parikshak": "There seems to be a technical issue on my end. Let's continue with your preparation - please rephrase your question and I'll do my best to help."
    }
    return fallbacks.get(agent_type, "I'm experiencing some technical difficulties, but I'm here to help. Please try again.")

@router.post("/enhanced", response_model=EnhancedChatResponse)
async def enhanced_chat(request: EnhancedChatRequest):
    """AI-Powered Enhanced chat with proper Azure OpenAI integration"""
    try:
        # Validate agent type
        agent_map = {
            "mitra": AgentType.MITRA,
            "guru": AgentType.GURU, 
            "parikshak": AgentType.PARIKSHAK
        }
        
        agent_type = agent_map.get(request.agent_type.lower(), AgentType.MITRA)
        
        # Generate a temporary candidate ID for testing
        candidate_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Handle session management
        session_id = request.session_id
        conversation_history = []
        
        if session_id:
            # Try to get existing conversation history
            try:
                history = await mcp_manager.get_conversation_history(session_id, limit=6)
                conversation_history = [
                    {"role": msg.role, "content": msg.content} 
                    for msg in history
                ]
            except Exception as e:
                logger.warning(f"Could not get conversation history: {e}")
        else:
            # Create new session
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # Generate AI response using Azure OpenAI
        agent_response = await generate_ai_response(
            request.agent_type.lower(), 
            request.message, 
            conversation_history
        )
        
        # Try to store conversation in MCP (optional)
        try:
            await mcp_manager.add_message(
                session_id=session_id,
                role="user",
                content=request.message,
                agent_type=agent_type
            )
            await mcp_manager.add_message(
                session_id=session_id,
                role="assistant", 
                content=agent_response,
                agent_type=agent_type
            )
        except Exception as e:
            logger.warning(f"Could not store conversation: {e}")
        
        return EnhancedChatResponse(
            response=agent_response,
            agent_type=request.agent_type,
            session_id=session_id,
            voice_enabled=request.voice_enabled,
            candidate_id=candidate_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Enhanced chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enhanced chat error: {str(e)}"
        )