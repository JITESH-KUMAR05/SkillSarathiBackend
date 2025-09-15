"""
Murf AI Text-to-Speech Service

High-quality voice synthesis using official Murf AI SDK with optimized performance
and caching for minimal latency.
"""

import os
import asyncio
import hashlib
import base64
from typing import Dict, List, Optional, Union, Any, TYPE_CHECKING
from pydantic import BaseModel
from fastapi import HTTPException
import httpx

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

# Available Murf AI Indian and Hindi Voices (REAL working voice IDs from API)
MURF_INDIAN_VOICES = {
    # Native Hindi Voices (best for Hindi conversations)
    "hi-IN-shweta": MurfVoice(
        id="hi-IN-shweta",
        name="Shweta", 
        language="Hindi",
        gender="Female",
        age="Young Adult",
        accent="India",
        description="Native Hindi voice with multiple styles - perfect for natural conversations"
    ),
    "hi-IN-rahul": MurfVoice(
        id="hi-IN-rahul",
        name="Rahul",
        language="Hindi",
        gender="Male", 
        age="Young Adult",
        accent="India",
        description="Native Hindi male voice - clear and professional"
    ),
    "hi-IN-amit": MurfVoice(
        id="hi-IN-amit",
        name="Amit",
        language="Hindi",
        gender="Male",
        age="Young Adult",
        accent="India",
        description="Native Hindi voice - conversational and friendly"
    ),
    
    # Indian-English Voices (excellent for mixed Hindi-English content)
    "en-IN-isha": MurfVoice(
        id="en-IN-isha",
        name="Isha", 
        language="English",
        gender="Female",
        age="Young Adult",
        accent="India",
        description="Professional Indian-English voice with Hindi support"
    ),
    "en-IN-arohi": MurfVoice(
        id="en-IN-arohi",
        name="Arohi",
        language="English",
        gender="Female", 
        age="Young Adult",
        accent="India",
        description="Warm Indian-English voice - great for friendly conversations"
    ),
    
    # Bengali-India Voice (with excellent Hindi support)
    "bn-IN-anwesha": MurfVoice(
        id="bn-IN-anwesha",
        name="Anwesha",
        language="Bengali",
        gender="Female",
        age="Young Adult",
        accent="India",
        description="Bengali-India voice with excellent Hindi conversational support"
    ),
}

# Agent-specific voice mappings with real Hindi voices
AGENT_VOICE_MAPPING = {
    "mitra": {
        "primary": "hi-IN-shweta",  # Native Hindi female voice with multiple styles
        "alternatives": ["en-IN-isha", "bn-IN-anwesha"],
        "tone": "warm"
    },
    "guru": {
        "primary": "hi-IN-rahul",  # Native Hindi male voice for educational content
        "alternatives": ["hi-IN-amit", "en-IN-isha"],
        "tone": "educational"
    },
    "parikshak": {
        "primary": "hi-IN-amit",  # Native Hindi male voice for professional assessment
        "alternatives": ["hi-IN-rahul", "en-IN-isha"], 
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
        voice_cache: Optional['VoiceCache'] = None,
        auto_voice_enabled: bool = False
    ):
        self.api_key = api_key or os.getenv("MURF_API_KEY")
        self.voice_cache = voice_cache
        self.auto_voice_enabled = auto_voice_enabled  # Auto-voice setting
        
        if not self.api_key:
            logger.warning("MURF_API_KEY not found. Voice generation will be disabled.")
            self.client = None
        else:
            self.client = Murf(api_key=self.api_key)
            
        self.default_config = VoiceConfig(voice_id="hi-IN-shweta")  # Default to real Hindi female voice
    
    def set_auto_voice(self, enabled: bool):
        """Enable or disable auto-voice for all responses"""
        self.auto_voice_enabled = enabled
        logger.info(f"Auto-voice {'enabled' if enabled else 'disabled'}")
    
    def is_auto_voice_enabled(self) -> bool:
        """Check if auto-voice is enabled"""
        return self.auto_voice_enabled
        
    def _generate_cache_key(self, text: str, config: VoiceConfig) -> str:
        """Generate cache key for speech generation"""
        content = f"{text}:{config.voice_id}:{config.speed}:{config.pitch}:{config.emphasis}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def get_available_voices_direct_api(self) -> List[Dict[str, Any]]:
        """
        Get list of available Murf voices using direct API call
        (Based on working implementation from reference repositories)
        
        Returns:
            List of voice objects with metadata
        """
        if not self.api_key:
            raise HTTPException(status_code=503, detail="Voice service not configured")
            
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    'api-key': self.api_key,
                }
                
                logger.info("Fetching voices from Murf API...")
                response = await client.get(
                    'https://api.murf.ai/v1/speech/voices',
                    headers=headers,
                    timeout=30.0
                )
                
                logger.info(f"Voices API Response Status: {response.status_code}")
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Voices API Error: {error_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to fetch voices: {response.status_code} {response.reason_phrase}"
                    )
                
                data = response.json()
                logger.info(f"Successfully fetched {len(data.get('voices', []))} voices")
                
                return data.get('voices', [])
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching voices from Murf API")
            raise HTTPException(status_code=504, detail="Timeout fetching voices")
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch available voices")
    
    async def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available Murf voices (fallback to predefined if API fails)
        
        Returns:
            List of voice objects with metadata
        """
        try:
            # Try direct API first
            return await self.get_available_voices_direct_api()
        except Exception as e:
            logger.warning(f"Failed to fetch voices from API: {e}, falling back to predefined voices")
            
            # Fallback to predefined Indian/Hindi voices
            voices_list = []
            for voice_id, voice_obj in MURF_INDIAN_VOICES.items():
                voices_list.append({
                    "id": voice_obj.id,
                    "name": voice_obj.name,
                    "language": voice_obj.language,
                    "gender": voice_obj.gender,
                    "accent": voice_obj.accent,
                    "description": voice_obj.description,
                    "locale": f"{voice_obj.language}-{voice_obj.accent}",
                    "available_styles": ["Conversational", "Professional"]
                })
            
            return voices_list
    
    async def generate_speech(
        self, 
        text: str, 
        voice_id: str = "hi-IN-shweta",  # Default to real Hindi voice
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
                elif isinstance(cached_audio, (bytes, str)):
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
            
            def _generate():
                if not self.client:
                    raise HTTPException(status_code=503, detail="Voice service not configured")
                return self.client.text_to_speech.generate(**generation_params)
                
            response = await loop.run_in_executor(None, _generate)
            
            if encode_as_base64:
                audio_data = response.encoded_audio
                if not audio_data:
                    raise HTTPException(status_code=500, detail="No audio data received from Murf")
                
                # Cache successful generation (store as base64 string)
                if self.voice_cache:
                    await self.voice_cache.cache_generated_speech(text, voice_id, base64.b64decode(audio_data))
                
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
        voice_id: str = "en-IN-isha",
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
            
            def _generate_ssml():
                if not self.client:
                    raise HTTPException(status_code=503, detail="Voice service not configured")
                return self.client.text_to_speech.generate(**generation_params)
                
            response = await loop.run_in_executor(None, _generate_ssml)
            
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
                "primary": MURF_INDIAN_VOICES["en-IN-isha"],
                "alternatives": [MURF_INDIAN_VOICES["en-IN-arohi"]]
            }
            
        mapping = AGENT_VOICE_MAPPING[agent]
        return {
            "primary": MURF_INDIAN_VOICES[mapping["primary"]],
            "alternatives": [MURF_INDIAN_VOICES[vid] for vid in mapping["alternatives"] if vid in MURF_INDIAN_VOICES],
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
            if voice and "hindi" in voice.language.lower():
                sample_text = "नमस्ते! मैं आपका AI साथी हूं। आज मैं आपकी कैसे मदद कर सकती हूं?"
            else:
                sample_text = "Hello! I'm your AI companion. How can I help you today?"
        
        result = await self.generate_speech(
            text=sample_text,
            voice_id=voice_id,
            speed=1.0,
            pitch=1.0,
            encode_as_base64=False
        )
        
        # Ensure we return bytes
        if isinstance(result, str):
            return base64.b64decode(result)
        return result
    
    async def generate_streaming_speech(
        self,
        text: str,
        voice_id: str = "en-IN-isha",
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
        audio_data = await self.generate_speech(
            text=text,
            voice_id=voice_id,
            encode_as_base64=False,
            **kwargs
        )
        
        # Ensure we have bytes
        if isinstance(audio_data, str):
            audio_data = base64.b64decode(audio_data)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech_{voice_id}.mp3",
                "Content-Length": str(len(audio_data))
            }
        )