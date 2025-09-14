"""
Murf AI Text-to-Speech Service

High-quality voice synthesis using Murf AI API with optimized performance
and caching for minimal latency.
"""

import os
import asyncio
import aiohttp
import json
import hashlib
from typing import Dict, List, Optional, Union, Any, TYPE_CHECKING
from pydantic import BaseModel
from fastapi import HTTPException

if TYPE_CHECKING:
    from .voice_cache import VoiceCache
from fastapi.responses import StreamingResponse
import io
import logging

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

# Available Murf AI Indian Voices
MURF_INDIAN_VOICES = {
    # Hindi Voices
    "aditi": MurfVoice(
        id="aditi",
        name="Aditi", 
        language="Hindi",
        gender="Female",
        age="Young Adult",
        accent="Indian",
        description="Warm, friendly Hindi voice perfect for Mitra agent"
    ),
    "kabir": MurfVoice(
        id="kabir",
        name="Kabir",
        language="Hindi", 
        gender="Male",
        age="Young Adult",
        accent="Indian",
        description="Professional, clear Hindi voice ideal for Guru agent"
    ),
    "radhika": MurfVoice(
        id="radhika",
        name="Radhika",
        language="Hindi",
        gender="Female", 
        age="Young Adult",
        accent="Indian",
        description="Authoritative Hindi voice suitable for Parikshak agent"
    ),
    
    # English-India Voices
    "alisha": MurfVoice(
        id="alisha",
        name="Alisha",
        language="English-India",
        gender="Female",
        age="Young Adult", 
        accent="Indian English",
        description="Natural Indian English for professional conversations"
    ),
    "arnav": MurfVoice(
        id="arnav", 
        name="Arnav",
        language="English-India",
        gender="Male",
        age="Young Adult",
        accent="Indian English",
        description="Clear, confident Indian English voice"
    ),
    "priya": MurfVoice(
        id="priya",
        name="Priya", 
        language="English-India",
        gender="Female",
        age="Young Adult",
        accent="Indian English", 
        description="Friendly, approachable Indian English voice"
    )
}

# Agent-specific voice mappings
AGENT_VOICE_MAPPING = {
    "mitra": {
        "primary": "aditi",
        "alternatives": ["priya", "radhika"],
        "tone": "warm"
    },
    "guru": {
        "primary": "arnav", 
        "alternatives": ["kabir", "alisha"],
        "tone": "educational"
    },
    "parikshak": {
        "primary": "alisha",
        "alternatives": ["arnav", "kabir"], 
        "tone": "professional"
    }
}

class MurfVoiceService:
    """
    Murf AI Voice Service for high-quality text-to-speech generation
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        voice_cache: Optional['VoiceCache'] = None
    ):
        self.api_key = api_key or os.getenv("MURF_API_KEY")
        self.base_url = base_url or os.getenv("MURF_API_URL", "https://api.murf.ai/v1")
        self.webhook_secret = os.getenv("MURF_WEBHOOK_SECRET")
        self.voice_cache = voice_cache
        
        if not self.api_key:
            logger.warning("MURF_API_KEY not found. Voice generation will be disabled.")
            
        self.session: Optional[aiohttp.ClientSession] = None
        self.default_config = VoiceConfig(voice_id="aditi")
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure session is initialized"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    def _generate_cache_key(self, text: str, config: VoiceConfig) -> str:
        """Generate cache key for speech generation"""
        content = f"{text}:{config.voice_id}:{config.speed}:{config.pitch}:{config.emphasis}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str = "aditi",
        speed: float = 1.0,
        pitch: float = 1.0, 
        emphasis: str = "normal",
        agent: Optional[str] = None
    ) -> bytes:
        """
        Generate high-quality speech using Murf AI
        
        Args:
            text: Text to convert to speech
            voice_id: Murf AI voice identifier
            speed: Speech speed (0.5 to 2.0)
            pitch: Voice pitch (-20 to 20)
            emphasis: Emphasis level (none, reduced, moderate, strong)
            agent: Agent context for voice optimization
            
        Returns:
            Audio data as bytes
        """
        if not self.api_key:
            raise HTTPException(status_code=503, detail="Voice service not configured")
            
        await self._ensure_session()
        assert self.session is not None, "Session should be initialized"
        
        # Optimize voice selection for agent
        if agent and agent in AGENT_VOICE_MAPPING:
            agent_config = AGENT_VOICE_MAPPING[agent]
            if voice_id == "auto":
                voice_id = agent_config["primary"]
                
        config = VoiceConfig(
            voice_id=voice_id,
            speed=speed,
            pitch=pitch,
            emphasis=emphasis
        )
        
        # Check cache first
        from .voice_cache import VoiceCache
        cache = VoiceCache()
        cached_audio = await cache.get_cached_speech(text, voice_id)
        if cached_audio:
            logger.info(f"Retrieved cached speech for voice {voice_id}")
            return cached_audio
        
        try:
            payload = {
                "text": text,
                "voice_id": voice_id,
                "speed": speed,
                "pitch": pitch,
                "emphasis": emphasis,
                "format": config.audio_format,
                "bitrate": config.bitrate,
                "optimize_streaming": True
            }
            
            logger.info(f"Generating speech with Murf AI: voice={voice_id}, length={len(text)}")
            
            async with self.session.post(
                f"{self.base_url}/speech",
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Murf AI API error: {response.status} - {error_text}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Voice generation failed: {error_text}"
                    )
                
                audio_data = await response.read()
                
                # Cache successful generation
                await cache.cache_generated_speech(text, voice_id, audio_data)
                
                logger.info(f"Successfully generated speech: {len(audio_data)} bytes")
                return audio_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error in speech generation: {e}")
            raise HTTPException(status_code=503, detail="Voice service temporarily unavailable")
        except Exception as e:
            logger.error(f"Unexpected error in speech generation: {e}")
            raise HTTPException(status_code=500, detail="Internal voice service error")
    
    async def generate_speech_with_ssml(
        self, 
        ssml: str, 
        voice_id: str = "aditi"
    ) -> bytes:
        """
        Generate speech with SSML markup for advanced control
        
        Args:
            ssml: SSML markup text
            voice_id: Murf AI voice identifier
            
        Returns:
            Audio data as bytes
        """
        if not self.api_key:
            raise HTTPException(status_code=503, detail="Voice service not configured")
            
        await self._ensure_session()
        assert self.session is not None, "Session should be initialized"
        
        try:
            payload = {
                "ssml": ssml,
                "voice_id": voice_id,
                "format": "mp3",
                "bitrate": 128
            }
            
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