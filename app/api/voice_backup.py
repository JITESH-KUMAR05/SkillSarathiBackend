"""
Voice API Routes - Simplified Implementation
"""

import logging
import base64
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

# Import our working Murf service
from ..services.voice.murf_service import MurfVoiceService

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

# Router setup
router = APIRouter(tags=["voice"])

# Initialize Murf service
murf_service = MurfVoiceService()

@router.post("/tts")
async def text_to_speech(request: TextToSpeechRequest):
    """Generate speech using Murf AI"""
    try:
        logger.info(f"🎤 TTS request for {request.agent}: {request.text[:50]}...")
        
        # Validate request
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Generate speech using the working Murf service
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent,
            encode_as_base64=False  # Get bytes directly
        )
        
        if not audio_data:
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
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@router.get("/voices")
async def get_voices():
    """Get available voices"""
    try:
        voices = await murf_service.get_available_voices()
        return {"voices": voices}
    except Exception as e:
        logger.error(f"❌ Get voices failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_voice(request: VoiceTestRequest = VoiceTestRequest()):
    """Test voice endpoint"""
    try:
        logger.info(f"🧪 Testing voice for {request.agent}")
        
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent,
            encode_as_base64=False
        )
        
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=test_{request.agent}.mp3"
            }
        )
    except Exception as e:
        logger.error(f"❌ Voice test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def voice_health():
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
async def text_to_speech(
    request: TextToSpeechRequest,
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Convert text to speech using agent voice
    """
    try:
        # Validate request
        if not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if request.agent not in ["mitra", "guru", "parikshak"]:
            raise HTTPException(status_code=400, detail="Invalid agent specified")
        
        # Generate speech
        murf_service = voice_manager.get_murf_service()
        if not murf_service:
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent
        )
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Optimize audio if needed
        audio_optimizer = voice_manager.get_audio_optimizer()
        if audio_optimizer:
            optimized_audio, metrics = await audio_optimizer.optimize_audio(
                audio_data,
                quality_preset=request.quality
            )
            
            response = TextToSpeechResponse(
                success=True,
                audio_data=base64.b64encode(optimized_audio).decode('utf-8'),
                duration_ms=metrics.duration_ms,
                file_size=metrics.file_size_bytes,
                format=metrics.format
            )
        else:
            response = TextToSpeechResponse(
                success=True,
                audio_data=base64.b64encode(audio_data).decode('utf-8'),
                file_size=len(audio_data),
                format=request.format
            )
        
        logger.info(f"Generated speech for user {current_user.get('user_id', 'unknown')}: {len(request.text)} chars")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        return TextToSpeechResponse(
            success=False,
            error=str(e)
        )

@router.post("/tts/stream")
async def text_to_speech_stream(
    request: TextToSpeechRequest,
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Stream text-to-speech audio in chunks
    """
    try:
        # Generate speech
        murf_service = voice_manager.get_murf_service()
        if not murf_service:
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        audio_data = await murf_service.generate_speech(
            text=request.text,
            agent=request.agent
        )
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate speech")
        
        # Create audio chunks for streaming
        audio_optimizer = voice_manager.get_audio_optimizer()
        if audio_optimizer:
            chunks = await audio_optimizer.create_audio_chunks(
                audio_data,
                chunk_duration_ms=1000  # 1 second chunks
            )
        else:
            chunks = [audio_data]
        
        async def generate_chunks():
            for chunk in chunks:
                yield chunk
                await asyncio.sleep(0.05)  # Small delay for smooth streaming
        
        return StreamingResponse(
            generate_chunks(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Speech-to-Text Endpoints

@router.post("/stt", response_model=SpeechToTextResponse)
async def speech_to_text(
    audio_file: UploadFile = File(...),
    language: str = Form("hi-IN"),
    enable_commands: bool = Form(True),
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Convert speech audio to text
    """
    try:
        # Validate file
        if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
            raise HTTPException(status_code=400, detail="Invalid audio file")
        
        # Read audio data
        audio_data = await audio_file.read()
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Get speech recognition service
        speech_service = voice_manager.get_speech_service()
        if not speech_service:
            raise HTTPException(status_code=503, detail="Speech recognition service unavailable")
        
        # Transcribe audio
        transcription_result = None
        async for result in speech_service.transcribe_audio_stream(audio_data, language):
            if result.text:
                transcription_result = result
                break
        
        if not transcription_result:
            return SpeechToTextResponse(
                success=False,
                error="No speech detected in audio"
            )
        
        # Process voice commands if enabled
        commands = []
        if enable_commands and transcription_result.text:
            voice_processor = voice_manager.get_voice_processor()
            if voice_processor:
                command_list = await voice_processor.process_voice_command(
                    transcription_result.text,
                    language=language,
                    confidence=transcription_result.confidence
                )
                commands = [cmd.model_dump() for cmd in command_list]
        
        response = SpeechToTextResponse(
            success=True,
            transcription=transcription_result.text,
            confidence=transcription_result.confidence,
            language=transcription_result.language,
            commands=commands
        )
        
        logger.info(f"Transcribed audio for user {current_user.get('user_id', 'unknown')}: '{transcription_result.text}'")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        return SpeechToTextResponse(
            success=False,
            error=str(e)
        )

# Voice Command Processing

@router.post("/commands", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Process voice command from text
    """
    try:
        voice_processor = voice_manager.get_voice_processor()
        if not voice_processor:
            raise HTTPException(status_code=503, detail="Voice command processor unavailable")
        
        # Process commands
        commands = await voice_processor.process_voice_command(
            request.text,
            language=request.language,
            confidence=request.confidence
        )
        
        # Get command suggestions
        suggestions = await voice_processor.get_command_suggestions(
            current_agent=request.agent_context,
            language=request.language
        )
        
        # Validate commands
        valid_commands = []
        for cmd in commands:
            if await voice_processor.validate_command(cmd):
                valid_commands.append(cmd.model_dump())
        
        response = VoiceCommandResponse(
            success=True,
            commands=valid_commands,
            suggested_responses=[s["text"] for s in suggestions[:5]],
            action_required=any(cmd.get("command_type") == "agent_switch" for cmd in valid_commands)
        )
        
        logger.info(f"Processed {len(valid_commands)} voice commands for user {current_user.get('user_id', 'unknown')}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice command processing error: {e}")
        return VoiceCommandResponse(
            success=False,
            error=str(e)
        )

# Voice Streaming WebSocket

@router.websocket("/stream/{session_id}")
async def voice_stream_websocket(
    websocket: WebSocket,
    session_id: str,
    agent: str = "mitra",
    voice_manager: VoiceServiceManager = Depends(get_voice_services)
):
    """
    WebSocket endpoint for real-time voice streaming
    """
    try:
        # Get streaming service
        streaming_service = voice_manager.get_streaming_service()
        if not streaming_service:
            await websocket.close(code=1003, reason="Voice streaming not available")
            return
        
        # Validate session ID
        if not session_id or len(session_id) < 8:
            await websocket.close(code=1003, reason="Invalid session ID")
            return
        
        # For now, use session_id as user_id (in production, extract from auth)
        user_id = session_id
        
        # Handle WebSocket connection
        await streaming_service.handle_websocket_connection(
            websocket=websocket,
            session_id=session_id,
            user_id=user_id,
            agent=agent
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

# Health and Status Endpoints

@router.get("/health", response_model=VoiceHealthResponse)
async def voice_health():
    """
    Get voice services health status
    """
    try:
        voice_manager = await get_voice_manager()
        health_info = await voice_manager.get_service_health()
        
        return VoiceHealthResponse(
            healthy=health_info["initialized"],
            services=health_info["services"],
            timestamp=health_info["timestamp"],
            error=health_info.get("initialization_error")
        )
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return VoiceHealthResponse(
            healthy=False,
            services={},
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )

@router.get("/voices")
async def get_available_voices(
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Get list of available voices
    """
    try:
        murf_service = voice_manager.get_murf_service()
        if not murf_service:
            raise HTTPException(status_code=503, detail="Voice service unavailable")
        
        voices = await murf_service.get_available_voices()
        
        return {
            "success": True,
            "voices": voices,
            "agent_mappings": {
                "mitra": {"primary": "aditi", "backup": "priya"},
                "guru": {"primary": "arnav", "backup": "kabir"},
                "parikshak": {"primary": "alisha", "backup": "radhika"}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get voices error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voices/preview")
async def preview_voice(
    voice_id: str = Form(...),
    sample_text: str = Form("नमस्ते, यह आवाज़ का नमूना है।"),
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Preview a voice with sample text
    """
    try:
        murf_service = voice_manager.get_murf_service()
        if not murf_service:
            raise HTTPException(status_code=503, detail="Voice service unavailable")
        
        # Generate preview
        audio_data = await murf_service.preview_voice(voice_id, sample_text)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="Failed to generate voice preview")
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"inline; filename=preview_{voice_id}.mp3"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Session Management

@router.get("/sessions/{session_id}")
async def get_session_stats(
    session_id: str,
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Get voice session statistics
    """
    try:
        streaming_service = voice_manager.get_streaming_service()
        if not streaming_service:
            raise HTTPException(status_code=503, detail="Streaming service unavailable")
        
        stats = await streaming_service.get_session_stats(session_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "session": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats")
async def get_cache_stats(
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Get voice cache statistics
    """
    try:
        voice_cache = voice_manager.get_voice_cache()
        if not voice_cache:
            raise HTTPException(status_code=503, detail="Voice cache unavailable")
        
        stats = await voice_cache.get_cache_stats()
        
        return {
            "success": True,
            "cache": stats
        }
        
    except Exception as e:
        logger.error(f"Get cache stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Configuration endpoints

@router.get("/config")
async def get_voice_config(
    voice_manager: VoiceServiceManager = Depends(get_voice_services),
    current_user: dict = Depends(AuthenticationService.get_current_user)
):
    """
    Get voice service configuration
    """
    try:
        config = voice_manager.config
        
        return {
            "success": True,
            "config": {
                "default_language": config.default_language,
                "default_quality": config.default_quality,
                "cache_enabled": config.cache_enabled,
                "streaming_enabled": config.streaming_enabled,
                "agent_voices": config.agent_voices,
                "services_available": {
                    "murf": bool(config.murf_api_key),
                    "azure_speech": bool(config.azure_speech_key),
                    "google_speech": bool(config.google_credentials_path)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Get config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))