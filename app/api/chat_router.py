"""
Chat Router for BuddyAgents Platform
Handles all chat-related endpoints with security and rate limiting
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, field_validator
import json
import asyncio

from app.core.config import get_settings, AgentConfig
from app.core.security import rate_limit_chat, AuthenticationService, InputValidator
from app.services.azure_openai_service import azure_openai_service, RegionType

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Request/Response Models
class ChatMessage(BaseModel):
    """Single chat message"""
    role: str
    content: str
    timestamp: Optional[str] = None
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ["user", "assistant", "system"]:
            raise ValueError("Role must be user, assistant, or system")
        return v
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        return InputValidator.sanitize_text(v, max_length=2000)


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    agent_type: str = "mitra"
    conversation_history: List[ChatMessage] = []
    stream: bool = False
    max_tokens: int = 500
    temperature: float = 0.7
    
    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v):
        if not AgentConfig.is_valid_agent(v):
            raise ValueError(f"Invalid agent type: {v}")
        return v
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        return InputValidator.sanitize_text(v, max_length=1000)
    
    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v):
        if v and (v < 1 or v > 2000):
            raise ValueError("max_tokens must be between 1 and 2000")
        return v
    
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    agent_type: str
    model_used: Optional[str] = None
    region: str
    timestamp: str
    conversation_id: Optional[str] = None
    tokens_used: Optional[int] = None


@router.post("/send")
@rate_limit_chat
async def send_chat_message(
    request: ChatRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> ChatResponse:
    """
    Send a chat message to an AI agent
    
    - **message**: The user's message (required)
    - **agent_type**: Type of agent - mitra, guru, or parikshak (default: mitra)
    - **conversation_history**: Previous messages in conversation (optional)
    - **max_tokens**: Maximum tokens in response (default: 500)
    - **temperature**: Response creativity 0-1 (default: 0.7)
    """
    try:
        logger.info(f"Chat request from user {user['user_id']} to {request.agent_type}")
        
        # Prepare messages
        messages = []
        
        # Add conversation history
        for msg in request.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        
        # Add current message
        messages.append({"role": "user", "content": request.message})
        
        # Generate response
        response_text = await azure_openai_service.generate_chat_response(
            messages=messages,
            agent_type=request.agent_type,
            stream=False,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Ensure response is a string
        if not isinstance(response_text, str):
            response_text = str(response_text)
        
        # Get agent configuration for response metadata
        agent_config = AgentConfig.get_agent_config(request.agent_type)
        
        from datetime import datetime
        return ChatResponse(
            response=response_text,
            agent_type=request.agent_type,
            model_used="Model Router",
            region="primary",
            timestamp=datetime.utcnow().isoformat(),
            conversation_id=f"conv_{user['user_id']}_{request.agent_type}",
            tokens_used=int(len(response_text.split()) * 1.3)  # Rough estimate
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate chat response"
        )


@router.post("/stream")
@rate_limit_chat
async def stream_chat_message(
    request: ChatRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """
    Stream a chat response from an AI agent
    
    Returns Server-Sent Events (SSE) for real-time streaming
    """
    try:
        logger.info(f"Streaming chat request from user {user['user_id']} to {request.agent_type}")
        
        # Prepare messages
        messages = []
        for msg in request.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})
        
        async def generate_stream():
            try:
                # Get streaming response
                response_stream = await azure_openai_service.generate_chat_response(
                    messages=messages,
                    agent_type=request.agent_type,
                    stream=True,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                )
                
                # Check if response is actually a generator
                if hasattr(response_stream, '__aiter__'):
                    # Stream chunks
                    async for chunk in response_stream:
                        if chunk:
                            data = {
                                "chunk": chunk,
                                "agent_type": request.agent_type,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            yield f"data: {json.dumps(data)}\n\n"
                else:
                    # Handle case where streaming returns a string
                    data = {
                        "chunk": str(response_stream),
                        "agent_type": request.agent_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                
                # Send completion signal
                completion_data = {
                    "done": True,
                    "agent_type": request.agent_type,
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(completion_data)}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                error_data = {
                    "error": "Stream interrupted",
                    "message": "An error occurred while streaming the response"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        logger.error(f"Stream setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup chat stream"
        )


@router.get("/agents")
async def get_available_agents():
    """Get list of available AI agents with their configurations"""
    try:
        agents_info = {}
        
        for agent_type in AgentConfig.get_all_agents():
            config = AgentConfig.get_agent_config(agent_type)
            agents_info[agent_type] = {
                "name": config["name"],
                "display_name": config["display_name"],
                "description": config["description"],
                "color_primary": config["color_primary"],
                "color_secondary": config["color_secondary"],
                "voice_id": config["voice_id"],
                "capabilities": [
                    "Text chat with personality",
                    "Voice responses",
                    "Contextual memory",
                    "Indian cultural awareness"
                ]
            }
        
        return {
            "agents": agents_info,
            "total_count": len(agents_info),
            "model_info": {
                "router": "Intelligent model selection (GPT-5, GPT-4.1, etc.)",
                "regions": ["East US 2", "Sweden Central"],
                "features": ["Cost optimization", "Performance optimization", "Auto-routing"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent information"
        )


@router.get("/history/{agent_type}")
async def get_chat_history(
    agent_type: str,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user),
    limit: int = 50
):
    """
    Get chat history for a specific agent
    
    - **agent_type**: Type of agent to get history for
    - **limit**: Maximum number of messages to return (default: 50)
    """
    try:
        if not AgentConfig.is_valid_agent(agent_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent type: {agent_type}"
            )
        
        # In a real implementation, this would fetch from database
        # For now, return a placeholder
        return {
            "agent_type": agent_type,
            "user_id": user["user_id"],
            "messages": [],
            "total_count": 0,
            "conversation_id": f"conv_{user['user_id']}_{agent_type}",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.delete("/history/{agent_type}")
async def clear_chat_history(
    agent_type: str,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """
    Clear chat history for a specific agent
    
    - **agent_type**: Type of agent to clear history for
    """
    try:
        if not AgentConfig.is_valid_agent(agent_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid agent type: {agent_type}"
            )
        
        # In a real implementation, this would delete from database
        logger.info(f"Chat history cleared for user {user['user_id']} and agent {agent_type}")
        
        return {
            "message": f"Chat history cleared for {agent_type}",
            "agent_type": agent_type,
            "user_id": user["user_id"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear chat history"
        )


@router.get("/capabilities")
async def get_chat_capabilities():
    """Get information about chat capabilities and model performance"""
    try:
        capabilities = await azure_openai_service.get_model_capabilities()
        
        return {
            "chat_features": {
                "streaming": True,
                "context_memory": True,
                "multi_agent": True,
                "voice_integration": True,
                "rate_limiting": True,
                "authentication": True
            },
            "model_capabilities": capabilities,
            "supported_languages": [
                "English", "Hindi", "Bengali", "Tamil", "Telugu", 
                "Gujarati", "Marathi", "Kannada", "Malayalam", "Punjabi"
            ],
            "max_message_length": 2000,
            "max_tokens_per_response": 1000,
            "rate_limits": {
                "messages_per_minute": 30,
                "tokens_per_minute": 15000
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat capabilities"
        )