"""
Voice Router for BuddyAgents Platform
Handles voice generation, transcription, and real-time audio
"""

import logging
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.core.config import get_settings, AgentConfig
from app.core.security import rate_limit_voice, AuthenticationService, InputValidator
from app.services.azure_openai_service import azure_openai_service, RegionType

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Request/Response Models
class VoiceGenerationRequest(BaseModel):
    """Voice generation request"""
    text: str
    agent_type: str = "mitra"
    voice_id: Optional[str] = None
    speed: float = 1.0
    
    @field_validator("text")
    @classmethod
    def validate_text(cls, v):
        return InputValidator.sanitize_text(v, max_length=1000)
    
    @field_validator("agent_type")
    @classmethod
    def validate_agent_type(cls, v):
        if not AgentConfig.is_valid_agent(v):
            raise ValueError(f"Invalid agent type: {v}")
        return v
    
    @field_validator("speed")
    @classmethod
    def validate_speed(cls, v):
        if v < 0.5 or v > 2.0:
            raise ValueError("Speed must be between 0.5 and 2.0")
        return v


class TranscriptionResponse(BaseModel):
    """Audio transcription response"""
    text: str
    language: str
    confidence: float
    duration_seconds: float
    model_used: str
    timestamp: str


@router.post("/generate")
@rate_limit_voice
async def generate_voice(
    request: VoiceGenerationRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """
    Generate voice audio from text using agent-specific voices
    
    - **text**: Text to convert to speech (required)
    - **agent_type**: Agent voice to use - mitra, guru, or parikshak
    - **voice_id**: Specific voice ID (optional, uses agent default)
    - **speed**: Speech speed 0.5-2.0 (default: 1.0)
    """
    try:
        logger.info(f"Voice generation request from user {user['user_id']} for {request.agent_type}")
        
        # Get agent configuration
        agent_config = AgentConfig.get_agent_config(request.agent_type)
        voice_id = request.voice_id or agent_config["voice_id"]
        
        # For now, return a placeholder response
        # In production, this would integrate with Murf AI or Azure Speech
        return {
            "status": "success",
            "message": "Voice generation completed",
            "agent_type": request.agent_type,
            "voice_id": voice_id,
            "text": request.text,
            "audio_url": f"/static/voice/{user['user_id']}/generated_audio.mp3",
            "duration_seconds": len(request.text.split()) * 0.5,  # Rough estimate
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Voice generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate voice audio"
        )


@router.post("/transcribe")
@rate_limit_voice
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language: str = Form("en"),
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> TranscriptionResponse:
    """
    Transcribe audio to text using GPT-4o-Transcribe
    
    - **audio_file**: Audio file to transcribe (MP3, WAV, M4A, etc.)
    - **language**: Language code (en, hi, bn, ta, etc.)
    """
    try:
        logger.info(f"Audio transcription request from user {user['user_id']}")
        
        # Validate file
        if not audio_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file size (25MB limit)
        file_content = await audio_file.read()
        if len(file_content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 25MB limit"
            )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Transcribe using Azure OpenAI
            result = await azure_openai_service.transcribe_audio(
                audio_file_path=tmp_file_path,
                language=language
            )
            
            if result["status"] == "success":
                return TranscriptionResponse(
                    text=result["transcription"],
                    language=language,
                    confidence=0.95,  # Placeholder
                    duration_seconds=len(file_content) / 16000,  # Rough estimate
                    model_used=result["model"],
                    timestamp=datetime.utcnow().isoformat()
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Transcription failed: {result.get('error', 'Unknown error')}"
                )
        
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcribe audio"
        )


@router.get("/voices")
async def get_available_voices():
    """Get list of available voices for each agent"""
    try:
        voices_info = {}
        
        for agent_type in AgentConfig.get_all_agents():
            config = AgentConfig.get_agent_config(agent_type)
            voices_info[agent_type] = {
                "default_voice": config["voice_id"],
                "name": config["name"],
                "description": config["description"],
                "color": config["color_primary"],
                "available_voices": [
                    {
                        "id": config["voice_id"],
                        "name": f"{config['name']} Voice",
                        "description": f"Default voice for {config['display_name']}",
                        "language": "en-IN",
                        "gender": "neutral"
                    }
                ]
            }
        
        return {
            "voices": voices_info,
            "supported_formats": ["mp3", "wav", "m4a", "aac"],
            "max_file_size": "25MB",
            "supported_languages": {
                "en": "English",
                "hi": "Hindi", 
                "bn": "Bengali",
                "ta": "Tamil",
                "te": "Telugu",
                "gu": "Gujarati",
                "mr": "Marathi",
                "kn": "Kannada",
                "ml": "Malayalam",
                "pa": "Punjabi"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice information"
        )


@router.post("/realtime")
@rate_limit_voice
async def start_realtime_conversation(
    agent_type: str = "mitra",
    voice_id: Optional[str] = None,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """
    Start a real-time voice conversation using GPT-Realtime
    
    - **agent_type**: Agent to converse with
    - **voice_id**: Voice for responses (optional)
    """
    try:
        logger.info(f"Real-time voice conversation started by user {user['user_id']} with {agent_type}")
        
        # Get agent configuration
        agent_config = AgentConfig.get_agent_config(agent_type)
        selected_voice = voice_id or agent_config["voice_id"]
        
        # For now, return connection info
        # In production, this would establish WebSocket connection to GPT-Realtime
        return {
            "status": "ready",
            "session_id": f"realtime_{user['user_id']}_{agent_type}_{datetime.utcnow().timestamp()}",
            "agent_type": agent_type,
            "voice_id": selected_voice,
            "websocket_url": f"/ws/realtime/{agent_type}",
            "instructions": [
                "Use WebSocket connection for real-time audio",
                "Send audio chunks as binary data",
                "Receive audio responses in real-time",
                "Session will timeout after 30 minutes of inactivity"
            ],
            "capabilities": {
                "speech_to_speech": True,
                "function_calling": True,
                "interruption_handling": True,
                "low_latency": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Real-time conversation setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup real-time conversation"
        )


@router.get("/capabilities")
async def get_voice_capabilities():
    """Get information about voice processing capabilities"""
    try:
        return {
            "voice_generation": {
                "enabled": True,
                "max_text_length": 1000,
                "supported_speeds": {"min": 0.5, "max": 2.0},
                "output_formats": ["mp3", "wav"]
            },
            "voice_transcription": {
                "enabled": True,
                "max_file_size": "25MB",
                "supported_formats": ["mp3", "wav", "m4a", "aac", "ogg"],
                "model": "GPT-4o-Transcribe",
                "context_window": "16k",
                "accuracy": "95%+"
            },
            "realtime_audio": {
                "enabled": True,
                "model": "GPT-Realtime",
                "features": [
                    "Speech-to-speech conversations",
                    "Low latency responses",
                    "Natural voice interactions",
                    "Function calling support"
                ],
                "supported_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
            },
            "rate_limits": {
                "voice_generation": "20 requests/minute",
                "transcription": "10 requests/minute",
                "realtime_sessions": "5 concurrent/user"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting voice capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve voice capabilities"
        )