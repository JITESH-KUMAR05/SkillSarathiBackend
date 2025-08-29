"""
Production Chat API for BuddyAgents
===================================

Simplified, working chat API with voice integration and agent routing.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
import logging

# Import voice and agent systems
from app.murf_streaming_fixed import stream_text_to_speech
from app.voice_config import get_agent_voice, get_voice_info
from app.llm.streaming_llm import StreamingLLMService

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class ChatMessage(BaseModel):
    message: str
    agent_type: str = "mitra"
    user_id: str = "default"
    voice_enabled: bool = False

class ChatResponse(BaseModel):
    response: str
    agent_type: str
    voice_id: str
    voice_info: Dict[str, Any]
    timestamp: str
    audio_available: bool = False

class AgentInfo(BaseModel):
    agent_type: str
    voice_id: str
    voice_name: str
    description: str
    language: str

# Initialize LLM service
llm_service = StreamingLLMService()

# Agent configurations
AGENT_CONFIGS = {
    "mitra": {
        "name": "Mitra (मित्र)",
        "description": "Your friendly AI companion for emotional support and daily conversations",
        "personality": "warm, caring, empathetic, uses Hindi phrases naturally",
        "system_prompt": """You are Mitra (मित्र), a warm and caring AI friend for Indian users. 
        You provide emotional support, listen to problems, and offer friendly advice. 
        Speak in a mix of Hindi and English naturally. Be empathetic and understanding."""
    },
    "guru": {
        "name": "Guru (गुरु)",
        "description": "Your learning mentor for education and skill development",
        "personality": "knowledgeable, patient, encouraging, educational",
        "system_prompt": """You are Guru (गुरु), an AI learning mentor specializing in education and skill development for Indian students. 
        Help with studies, career guidance, and learning new skills. Be patient, encouraging, and provide structured learning advice."""
    },
    "parikshak": {
        "name": "Parikshak (परीक्षक)",
        "description": "Your interview coach and technical assessor",
        "personality": "professional, analytical, constructive, thorough",
        "system_prompt": """You are Parikshak (परीक्षक), an AI interview coach and technical assessor. 
        Help with interview preparation, conduct mock interviews, and provide technical assessments. 
        Be professional, provide constructive feedback, and help improve interview skills."""
    }
}

@router.post("/send", response_model=ChatResponse)
async def send_chat_message(message_data: ChatMessage, background_tasks: BackgroundTasks):
    """Send a message to an AI agent and get response with optional voice"""
    
    try:
        # Validate agent type
        if message_data.agent_type not in AGENT_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {message_data.agent_type}")
        
        # Get agent configuration
        agent_config = AGENT_CONFIGS[message_data.agent_type]
        voice_id = get_agent_voice(message_data.agent_type)
        voice_info = get_voice_info(voice_id)
        
        logger.info(f"💬 Chat request: {message_data.agent_type} from user {message_data.user_id}")
        
        # Generate response using LLM
        system_prompt = agent_config["system_prompt"]
        user_message = f"User: {message_data.message}"
        
        try:
            # Get response from LLM service
            response_text = await llm_service.generate_response(
                prompt=user_message,
                system_prompt=system_prompt,
                max_tokens=500
            )
            
            if not response_text:
                response_text = f"Hello! I'm {agent_config['name']} and I'm here to help you."
                
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            # Fallback response
            response_text = f"Hello! I'm {agent_config['name']}. {agent_config['description']} How can I help you today?"
        
        # Create response
        chat_response = ChatResponse(
            response=response_text,
            agent_type=message_data.agent_type,
            voice_id=voice_id,
            voice_info={
                "name": voice_info["name"],
                "language": voice_info["language"],
                "gender": voice_info["gender"]
            },
            timestamp=datetime.now().isoformat(),
            audio_available=message_data.voice_enabled
        )
        
        # Generate voice audio if requested
        if message_data.voice_enabled:
            background_tasks.add_task(
                generate_voice_audio,
                response_text,
                message_data.agent_type,
                message_data.user_id
            )
        
        logger.info(f"✅ Response generated for {message_data.agent_type}")
        return chat_response
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents", response_model=list[AgentInfo])
async def get_available_agents():
    """Get list of available agents with their voice information"""
    
    agents = []
    for agent_type, config in AGENT_CONFIGS.items():
        voice_id = get_agent_voice(agent_type)
        voice_info = get_voice_info(voice_id)
        
        agents.append(AgentInfo(
            agent_type=agent_type,
            voice_id=voice_id,
            voice_name=voice_info["name"],
            description=config["description"],
            language=voice_info["language"]
        ))
    
    return agents

class VoiceRequest(BaseModel):
    text: str
    agent_type: str = "mitra"
    user_id: str = "default"

@router.post("/voice/generate")
async def generate_voice_only(voice_request: VoiceRequest):
    """Generate voice audio for given text and return audio data"""
    
    try:
        if voice_request.agent_type not in AGENT_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {voice_request.agent_type}")
        
        # Generate voice audio
        audio_chunks = []
        async for chunk in stream_text_to_speech(voice_request.text, voice_request.agent_type, voice_request.user_id):
            audio_chunks.append(chunk)
        
        if audio_chunks:
            audio_data = b''.join(audio_chunks)
            
            # Return the actual audio data as binary response
            return Response(
                content=audio_data,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f"attachment; filename=voice_{voice_request.agent_type}.wav",
                    "X-Voice-Agent": voice_request.agent_type,
                    "X-Voice-ID": get_agent_voice(voice_request.agent_type),
                    "X-Voice-Size": str(len(audio_data))
                }
            )
        else:
            raise HTTPException(status_code=500, detail="No audio generated")
            
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/info")
async def get_voice_info_only(voice_request: VoiceRequest):
    """Get voice generation info without audio data"""
    
    try:
        if voice_request.agent_type not in AGENT_CONFIGS:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {voice_request.agent_type}")
        
        # Generate voice audio (but only return metadata)
        audio_chunks = []
        async for chunk in stream_text_to_speech(voice_request.text, voice_request.agent_type, voice_request.user_id):
            audio_chunks.append(chunk)
        
        if audio_chunks:
            audio_data = b''.join(audio_chunks)
            return {
                "status": "success",
                "audio_size": len(audio_data),
                "voice_id": get_agent_voice(voice_request.agent_type),
                "message": f"Voice generated by {get_voice_info(get_agent_voice(voice_request.agent_type))['name']}"
            }
        else:
            raise HTTPException(status_code=500, detail="No audio generated")
            
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def chat_health_check():
    """Health check for chat API"""
    
    return {
        "status": "healthy",
        "agents_available": len(AGENT_CONFIGS),
        "voice_system": "active",
        "llm_service": "active"
    }

async def generate_voice_audio(text: str, agent_type: str, user_id: str):
    """Background task to generate voice audio"""
    try:
        logger.info(f"🎵 Generating voice audio for {agent_type}")
        
        chunk_count = 0
        async for chunk in stream_text_to_speech(text, agent_type, user_id):
            chunk_count += 1
        
        logger.info(f"✅ Voice generation completed: {chunk_count} chunks for {agent_type}")
        
    except Exception as e:
        logger.error(f"❌ Background voice generation error: {e}")

# Simple message compatibility endpoint
@router.post("/simple")
async def simple_chat(message: str, agent: str = "mitra"):
    """Simple chat endpoint for frontend compatibility"""
    
    chat_request = ChatMessage(
        message=message,
        agent_type=agent,
        user_id="simple_user",
        voice_enabled=False
    )
    
    response = await send_chat_message(chat_request, BackgroundTasks())
    return {"response": response.response, "agent": response.agent_type}
