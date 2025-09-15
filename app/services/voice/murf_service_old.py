"""
Murf AI Text-to-Speech Service

High-quality voice synthesis using official Murf AI SDK with optimized performance
and caching for minimal latency.
"""

import os
import asyncio
import hashlib
from typing import Dict, List, Optional, Union, Any, TYPE_CHECKING
from pydantic import BaseModel
from fastapi import HTTPException
import httpx
import base64

if TYPE_CHECKING:
    from .voice_cache import VoiceCache
from fastapi.responses import StreamingResponse
import io
import logging

# Import official Murf SDK
from murf import Murf

logger = logging.getLogger(__name__)

class VoiceConfig(BaseModel):
    """Configuration for voice generation"""
    voice_id: str
    speed: float = 1.0
    pitch: float = 1.0
    emphasis: str = "normal"
    pause_duration: float = 0.3
    audio_format: str = "mp3"
    bitrate: int = 128

class MurfVoice(BaseModel):
    """Murf AI voice model"""
    id: str
    name: str
    language: str
    gender: str
    age: str
    accent: str
    description: str
    sample_url: Optional[str] = None

# Available Murf AI Indian Voices (using proper Murf voice IDs)
MURF_INDIAN_VOICES = {
    # Hindi Voices
    "hi-IN-aditi": MurfVoice(
        id="hi-IN-aditi",
        name="Aditi", 
        language="Hindi",
        gender="Female",
        age="Young Adult",
        accent="Indian",
        description="Warm, friendly Hindi voice perfect for Mitra agent"
    ),
    "hi-IN-kabir": MurfVoice(
        id="hi-IN-kabir",
        name="Kabir",
        language="Hindi", 
        gender="Male",
        age="Young Adult",
        accent="Indian",
        description="Professional, clear Hindi voice ideal for Guru agent"
    ),
    "hi-IN-radhika": MurfVoice(
        id="hi-IN-radhika",
        name="Radhika",
        language="Hindi",
        gender="Female", 
        age="Young Adult",
        accent="Indian",
        description="Authoritative Hindi voice suitable for Parikshak agent"
    ),
    
    # English-India Voices
    "en-IN-alisha": MurfVoice(
        id="en-IN-alisha",
        name="Alisha",
        language="English-India",
        gender="Female",
        age="Young Adult", 
        accent="Indian English",
        description="Natural Indian English for professional conversations"
    ),
    "en-IN-arnav": MurfVoice(
        id="en-IN-arnav", 
        name="Arnav",
        language="English-India",
        gender="Male",
        age="Young Adult",
        accent="Indian English",
        description="Clear, confident Indian English voice"
    ),
    "en-IN-priya": MurfVoice(
        id="en-IN-priya",
        name="Priya", 
        language="English-India",
        gender="Female",
        age="Young Adult",
        accent="Indian English", 
        description="Friendly, approachable Indian English voice"
    )
}

# Agent-specific voice mappings with proper Murf voice IDs
AGENT_VOICE_MAPPING = {
    "mitra": {
        "primary": "hi-IN-aditi",
        "alternatives": ["en-IN-priya", "hi-IN-radhika"],
        "tone": "warm"
    },
    "guru": {
        "primary": "en-IN-arnav", 
        "alternatives": ["hi-IN-kabir", "en-IN-alisha"],
        "tone": "educational"
    },
    "parikshak": {
        "primary": "en-IN-alisha",
        "alternatives": ["en-IN-arnav", "hi-IN-kabir"], 
        "tone": "professional"
    }
}

class MurfVoiceService:
    """
    Murf AI Voice Service using official SDK for high-quality text-to-speech generation
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        voice_cache: Optional['VoiceCache'] = None
    ):
        self.api_key = api_key or os.getenv("MURF_API_KEY")
        self.voice_cache = voice_cache
        
        if not self.api_key:
            logger.warning("MURF_API_KEY not found. Voice generation will be disabled.")
            self.client = None
        else:
            self.client = Murf(api_key=self.api_key)
            
        self.default_config = VoiceConfig(voice_id="hi-IN-aditi")
        
    def _generate_cache_key(self, text: str, config: VoiceConfig) -> str:
        """Generate cache key for speech generation"""
        content = f"{text}:{config.voice_id}:{config.speed}:{config.pitch}:{config.emphasis}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available Murf voices
        
        Returns:
            List of voice objects with metadata
        """
        if not self.client:
            raise HTTPException(status_code=503, detail="Voice service not configured")
            
        try:
            # Run in thread pool since Murf SDK is synchronous
            loop = asyncio.get_event_loop()
            voices = await loop.run_in_executor(None, self.client.text_to_speech.get_voices)
            return voices
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch available voices")
    
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str = "hi-IN-aditi",
        speed: float = 1.0,
        pitch: float = 1.0, 
        emphasis: str = "normal",
        agent: Optional[str] = None,
        format: str = "mp3",
        encode_as_base64: bool = True
    ) -> Union[bytes, str]:
        """
        Generate high-quality speech using official Murf AI SDK
        
        Args:
            text: Text to convert to speech
            voice_id: Murf AI voice identifier
            speed: Speech speed (0.5 to 2.0)
            pitch: Voice pitch (-50 to 50)
            emphasis: Emphasis level (none, reduced, moderate, strong)
            agent: Agent context for voice optimization
            format: Audio format (mp3, wav, flac)
            encode_as_base64: Return base64 encoded audio instead of URL
            
        Returns:
            Audio data as bytes or base64 string
        """
        if not self.client:
            raise HTTPException(status_code=503, detail="Voice service not configured")
        
        # Optimize voice selection for agent
        if agent and agent in AGENT_VOICE_MAPPING:
            agent_config = AGENT_VOICE_MAPPING[agent]
            if voice_id == "auto":
                voice_id = agent_config["primary"]
                
        config = VoiceConfig(
            voice_id=voice_id,
            speed=speed,
            pitch=pitch,
            emphasis=emphasis,
            audio_format=format
        )
        
        # Check cache first
        if self.voice_cache:
            cached_audio = await self.voice_cache.get_cached_speech(text, voice_id)
            if cached_audio:
                logger.info(f"Retrieved cached speech for voice {voice_id}")
                if isinstance(cached_audio, dict) and "audio_data" in cached_audio:
                    return cached_audio["audio_data"]
                return cached_audio

        try:
            # Prepare Murf API request parameters
            generation_params = {
                "text": text,
                "voice_id": voice_id,
                "format": format.upper(),
                "encode_as_base_64": encode_as_base64
            }
            
            # Add optional parameters only if they're not default values
            if speed != 1.0:
                generation_params["rate"] = int((speed - 1.0) * 50)  # Convert to Murf rate (-50 to 50)
            if pitch != 1.0:
                generation_params["pitch"] = int((pitch - 1.0) * 50)  # Convert to Murf pitch (-50 to 50)
            
            logger.info(f"Generating speech with Murf AI: voice={voice_id}, length={len(text)}")
            
            # Run generation in thread pool since Murf SDK is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.text_to_speech.generate(**generation_params)
            )
            
            if encode_as_base64:
                audio_data = response.encoded_audio
                if not audio_data:
                    raise HTTPException(status_code=500, detail="No audio data received from Murf")
                
                # Cache successful generation
                if self.voice_cache:
                    await self.voice_cache.cache_generated_speech(text, voice_id, audio_data)
                
                logger.info(f"Successfully generated speech: base64 length={len(audio_data)}")
                return audio_data
            else:
                # Download audio from URL and return bytes
                audio_url = response.audio_file
                if not audio_url:
                    raise HTTPException(status_code=500, detail="No audio URL received from Murf")
                
                async with httpx.AsyncClient() as client:
                    audio_response = await client.get(audio_url)
                    if audio_response.status_code != 200:
                        raise HTTPException(status_code=500, detail="Failed to download audio from Murf")
                    
                    audio_bytes = audio_response.content
                    
                    # Cache successful generation
                    if self.voice_cache:
                        await self.voice_cache.cache_generated_speech(text, voice_id, audio_bytes)
                    
                    logger.info(f"Successfully generated speech: {len(audio_bytes)} bytes")
                    return audio_bytes
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in speech generation: {e}")
            raise HTTPException(status_code=500, detail=f"Internal voice service error: {str(e)}")
    
    async def generate_speech_with_ssml(
        self, 
        ssml: str, 
        voice_id: str = "hi-IN-aditi",
        format: str = "mp3",
        encode_as_base64: bool = True
    ) -> Union[bytes, str]:
        """
        Generate speech with SSML markup for advanced control
        
        Args:
            ssml: SSML markup text
            voice_id: Murf AI voice identifier
            format: Audio format (mp3, wav, flac)
            encode_as_base64: Return base64 encoded audio instead of URL
            
        Returns:
            Audio data as bytes or base64 string
        """
        if not self.client:
            raise HTTPException(status_code=503, detail="Voice service not configured")
        
        try:
            generation_params = {
                "text": ssml,  # Murf handles SSML automatically
                "voice_id": voice_id,
                "format": format.upper(),
                "encode_as_base_64": encode_as_base64
            }
            
            logger.info(f"Generating SSML speech with Murf AI: voice={voice_id}")
            
            # Run generation in thread pool since Murf SDK is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.text_to_speech.generate(**generation_params)
            )
            
            if encode_as_base64:
                audio_data = response.encoded_audio
                if not audio_data:
                    raise HTTPException(status_code=500, detail="No audio data received from Murf")
                return audio_data
            else:
                audio_url = response.audio_file
                if not audio_url:
                    raise HTTPException(status_code=500, detail="No audio URL received from Murf")
                
                async with httpx.AsyncClient() as client:
                    audio_response = await client.get(audio_url)
                    if audio_response.status_code != 200:
                        raise HTTPException(status_code=500, detail="Failed to download audio from Murf")
                    
                    return audio_response.content
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SSML speech generation: {e}")
            raise HTTPException(status_code=500, detail=f"Internal voice service error: {str(e)}")
            
            async with self.session.post(
                f"{self.base_url}/speech/ssml",
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"SSML speech generation failed: {error_text}"
                    )
                
                return await response.read()
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error in SSML speech generation: {e}")
            raise HTTPException(status_code=503, detail="Voice service temporarily unavailable")
    
    async def get_available_voices(self, language: Optional[str] = None) -> List[MurfVoice]:
        """
        Get available Indian voices from Murf AI
        
        Args:
            language: Filter by language (Hindi, English-India)
            
        Returns:
            List of available voices
        """
        voices = list(MURF_INDIAN_VOICES.values())
        
        if language:
            voices = [v for v in voices if v.language.lower() == language.lower()]
            
        return voices
    
    async def get_agent_voices(self, agent: str) -> Dict[str, Any]:
        """
        Get recommended voices for specific agent
        
        Args:
            agent: Agent identifier (mitra, guru, parikshak)
            
        Returns:
            Dictionary with primary and alternative voices
        """
        if agent not in AGENT_VOICE_MAPPING:
            return {
                "primary": MURF_INDIAN_VOICES["aditi"],
                "alternatives": [MURF_INDIAN_VOICES["priya"]]
            }
            
        mapping = AGENT_VOICE_MAPPING[agent]
        return {
            "primary": MURF_INDIAN_VOICES[mapping["primary"]],
            "alternatives": [MURF_INDIAN_VOICES[vid] for vid in mapping["alternatives"]],
            "tone": mapping["tone"]
        }
    
    async def preview_voice(
        self, 
        voice_id: str, 
        sample_text: Optional[str] = None
    ) -> bytes:
        """
        Generate voice preview with sample text
        
        Args:
            voice_id: Voice to preview
            sample_text: Custom sample text (optional)
            
        Returns:
            Audio preview as bytes
        """
        if not sample_text:
            voice = MURF_INDIAN_VOICES.get(voice_id)
            if voice:
                if voice.language == "Hindi":
                    sample_text = "नमस्ते! मैं आपका AI साथी हूं। आज मैं आपकी कैसे मदद कर सकती हूं?"
                else:
                    sample_text = "Hello! I'm your AI companion. How can I help you today?"
            else:
                sample_text = "Hello! This is a voice preview."
        
        return await self.generate_speech(
            text=sample_text,
            voice_id=voice_id,
            speed=1.0,
            pitch=1.0
        )
    
    async def generate_streaming_speech(
        self,
        text: str,
        voice_id: str = "aditi",
        **kwargs
    ) -> StreamingResponse:
        """
        Generate speech and return as streaming response for immediate playback
        
        Args:
            text: Text to convert
            voice_id: Voice identifier
            **kwargs: Additional voice parameters
            
        Returns:
            StreamingResponse with audio data
        """
        audio_data = await self.generate_speech(text, voice_id, **kwargs)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "Cache-Control": "public, max-age=3600"
            }
        )
    
    def get_voice_info(self, voice_id: str) -> Optional[MurfVoice]:
        """Get information about a specific voice"""
        return MURF_INDIAN_VOICES.get(voice_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Murf AI service health"""
        if not self.api_key:
            return {"status": "disabled", "reason": "API key not configured"}
            
        try:
            await self._ensure_session()
            assert self.session is not None, "Session should be initialized"
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    return {"status": "healthy", "voices_available": len(MURF_INDIAN_VOICES)}
                else:
                    return {"status": "unhealthy", "status_code": response.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def configure_agent_voice(self, agent: str, voice_config: Dict[str, Any]):
        """
        Configure voice settings for a specific agent
        
        Args:
            agent: Agent name (mitra, guru, parikshak)
            voice_config: Voice configuration dictionary
        """
        try:
            # This method can be used to update agent voice mappings dynamically
            # For now, we'll just log the configuration
            logger.info(f"Voice configuration for {agent}: {voice_config}")
            
        except Exception as e:
            logger.error(f"Failed to configure voice for {agent}: {e}")