"""
Voice API Routes - Simplified Implementation
"""

import logging
import base64
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Import our working Murf service
from ..services.voice.murf_service import MurfVoiceService
from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Request Models
class TextToSpeechRequest(BaseModel):
    """Text-to-speech request"""
    text: str = Field(..., description="Text to convert to speech", max_length=5000)
    agent: str = Field("mitra", description="Agent voice to use")
    voice_id: Optional[str] = Field(None, description="Specific voice ID to use")

class VoiceTestRequest(BaseModel):
    """Voice test request"""
    text: str = Field("Hello! This is a voice test from BuddyAgents.", description="Test text")
    agent: str = Field("mitra", description="Agent to test")

class AutoVoiceRequest(BaseModel):
    """Auto-voice configuration request"""
    enabled: bool = Field(..., description="Enable or disable auto-voice")

class AutoVoiceResponse(BaseModel):
    """Auto-voice configuration response"""
    enabled: bool
    message: str

# Router setup
router = APIRouter(tags=["voice"])

# Global auto-voice state (persistent across requests)
_global_auto_voice_enabled = False

def get_auto_voice_state() -> bool:
    """Get global auto-voice state"""
    return _global_auto_voice_enabled

def set_auto_voice_state(enabled: bool) -> bool:
    """Set global auto-voice state"""
    global _global_auto_voice_enabled
    _global_auto_voice_enabled = enabled
    logger.info(f"Global auto-voice state changed to: {enabled}")
    return _global_auto_voice_enabled

def get_murf_service():
    """Get initialized Murf service with API key from settings"""
    settings = get_settings()
    service = MurfVoiceService(api_key=settings.murf_api_key)
    # Set the service auto-voice state to match global state
    service.set_auto_voice(get_auto_voice_state())
    return service

@router.post("/tts")
async def text_to_speech(request: TextToSpeechRequest, murf_service: MurfVoiceService = Depends(get_murf_service)):
    """Generate speech using Murf AI"""
    try:
        logger.info(f"🎤 TTS request for {request.agent}: {request.text[:50]}...")
        
        # Validate request
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Debug: Check if murf_service is initialized
        logger.info(f"🔍 Murf service client: {murf_service.client is not None}")
        
        # Generate speech using the working Murf service
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent,
            encode_as_base64=False  # Get bytes directly
        )
        
        if not audio_data:
            logger.error("❌ No audio data returned from Murf service")
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Convert to bytes if needed
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)
        
        logger.info(f"✅ Generated speech: {len(audio_data)} bytes")
        
        # Return audio as response
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=voice_{request.agent}.mp3",
                "X-Voice-Agent": request.agent,
                "X-Audio-Length": str(len(audio_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ TTS failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@router.get("/voices")
async def get_voices(murf_service: MurfVoiceService = Depends(get_murf_service)):
    """Get available voices"""
    try:
        voices = await murf_service.get_available_voices()
        return {"voices": voices}
    except Exception as e:
        logger.error(f"❌ Get voices failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_voice(request: VoiceTestRequest, murf_service: MurfVoiceService = Depends(get_murf_service)):
    """Test voice generation"""
    try:
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent,
            encode_as_base64=False
        )
        
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)
            
        return Response(
            content=audio_data,
            media_type="audio/mpeg"
        )
    except Exception as e:
        logger.error(f"❌ Voice test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def voice_health(murf_service: MurfVoiceService = Depends(get_murf_service)):
    """Voice services health check"""
    try:
        # Check if Murf API key is configured
        api_key = os.getenv("MURF_API_KEY")
        if not api_key:
            return {"healthy": False, "error": "MURF_API_KEY not configured"}
        
        # Try to get voices to test API connectivity
        voices = await murf_service.get_available_voices()
        
        return {
            "healthy": True,
            "murf_configured": True,
            "available_voices": len(voices),
            "timestamp": "2024-12-19T10:30:00Z"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": "2024-12-19T10:30:00Z"
        }

@router.get("/test-simple")
async def test_simple(murf_service: MurfVoiceService = Depends(get_murf_service)):
    """Simple test endpoint without parameters"""
    try:
        logger.info("🧪 Simple voice test")
        
        audio_data = await murf_service.generate_speech(
            text="Hello! This is a simple voice test from BuddyAgents.",
            agent="mitra",
            encode_as_base64=False
        )
        
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=simple_test.mp3"
            }
        )
    except Exception as e:
        logger.error(f"❌ Simple test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/auto-voice/enable", response_model=AutoVoiceResponse)
async def enable_auto_voice(request: AutoVoiceRequest):
    """Enable or disable auto-voice for all responses"""
    try:
        # Update global state
        set_auto_voice_state(request.enabled)
        
        return AutoVoiceResponse(
            enabled=request.enabled,
            message=f"Auto-voice {'enabled' if request.enabled else 'disabled'} successfully"
        )
    except Exception as e:
        logger.error(f"❌ Auto-voice configuration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auto-voice/status", response_model=AutoVoiceResponse)
async def get_auto_voice_status():
    """Get current auto-voice status"""
    try:
        enabled = get_auto_voice_state()
        
        return AutoVoiceResponse(
            enabled=enabled,
            message=f"Auto-voice is {'enabled' if enabled else 'disabled'}"
        )
    except Exception as e:
        logger.error(f"❌ Auto-voice status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))