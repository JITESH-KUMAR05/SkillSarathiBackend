"""
Speech Recognition Service

Real-time speech-to-text using Azure Speech Services or Google Cloud Speech-to-Text
with support for Hindi and English languages.
"""

import os
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from pydantic import BaseModel
import aiohttp
import base64
import io

logger = logging.getLogger(__name__)

class SpeechConfig(BaseModel):
    """Speech recognition configuration"""
    azure_key: Optional[str] = None
    azure_region: str = "eastus"
    google_credentials_path: Optional[str] = None
    default_language: str = "hi-IN"
    providers: List[str] = ["azure"]  # Available providers
    enable_continuous: bool = True
    enable_interim_results: bool = True
    confidence_threshold: float = 0.5

class TranscriptionResult(BaseModel):
    """Speech transcription result"""
    text: str
    confidence: float
    language: str
    is_final: bool = True
    alternatives: List[str] = []
    timestamp: Optional[float] = None

class SpeechRecognitionService:
    """
    Speech Recognition Service with support for multiple providers
    """
    
    def __init__(self, config: Optional[SpeechConfig] = None):
        self.config = config or SpeechConfig()
        
        # Azure Speech Services configuration
        self.azure_speech_key = self.config.azure_key or os.getenv("AZURE_SPEECH_KEY")
        self.azure_speech_region = self.config.azure_region or os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        # Google Cloud Speech configuration
        self.google_api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
        
        # Determine which service to use
        self.provider = self._determine_provider()
        
        # Supported languages
        self.supported_languages = {
            "hi-IN": "Hindi (India)",
            "en-IN": "English (India)", 
            "en-US": "English (US)",
            "hi": "Hindi",
            "en": "English"
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _determine_provider(self) -> str:
        """Determine which speech service to use based on available credentials"""
        if self.azure_speech_key:
            return "azure"
        elif self.google_api_key:
            return "google"
        else:
            logger.warning("No speech recognition service configured")
            return "none"
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def transcribe_audio_stream(
        self,
        audio_stream: bytes,
        language: str = "hi-IN",
        continuous: bool = False
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        Real-time audio transcription
        
        Args:
            audio_stream: Audio data as bytes
            language: Language code (hi-IN, en-IN, etc.)
            continuous: Whether to use continuous recognition
            
        Yields:
            TranscriptionResult objects
        """
        if self.provider == "azure":
            async for result in self._transcribe_azure_stream(audio_stream, language, continuous):
                yield result
        elif self.provider == "google":
            async for result in self._transcribe_google_stream(audio_stream, language):
                yield result
        else:
            # Fallback/mock implementation
            yield TranscriptionResult(
                text="Speech recognition not available",
                confidence=0.0,
                language=language,
                is_final=True
            )
    
    async def _transcribe_azure_stream(
        self,
        audio_stream: bytes,
        language: str,
        continuous: bool
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Azure Speech Services transcription"""
        await self._ensure_session()
        assert self.session is not None, "Session should be initialized"
        
        try:
            # Azure Speech Services API endpoint
            endpoint = f"https://{self.azure_speech_region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
            
            headers = {
                "Ocp-Apim-Subscription-Key": self.azure_speech_key,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                "Accept": "application/json"
            }
            
            params = {
                "language": language,
                "format": "detailed",
                "profanity": "raw"
            }
            
            async with self.session.post(
                endpoint,
                headers=headers,
                params=params,
                data=audio_stream
            ) as response:
                
                if response.status == 200:
                    result_data = await response.json()
                    
                    if result_data.get("RecognitionStatus") == "Success":
                        best_result = result_data["NBest"][0]
                        
                        yield TranscriptionResult(
                            text=best_result["Display"],
                            confidence=best_result["Confidence"],
                            language=language,
                            is_final=True,
                            alternatives=[item["Display"] for item in result_data["NBest"][1:]]
                        )
                    else:
                        logger.warning(f"Azure Speech recognition failed: {result_data}")
                else:
                    logger.error(f"Azure Speech API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Azure Speech transcription error: {e}")
    
    async def _transcribe_google_stream(
        self,
        audio_stream: bytes,
        language: str
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """Google Cloud Speech-to-Text transcription"""
        await self._ensure_session()
        assert self.session is not None, "Session should be initialized"
        
        try:
            endpoint = f"https://speech.googleapis.com/v1/speech:recognize?key={self.google_api_key}"
            
            # Encode audio to base64
            audio_base64 = base64.b64encode(audio_stream).decode('utf-8')
            
            payload = {
                "config": {
                    "encoding": "WEBM_OPUS",
                    "sampleRateHertz": 16000,
                    "languageCode": language,
                    "enableAutomaticPunctuation": True,
                    "alternativeLanguageCodes": ["hi-IN", "en-IN"] if language.startswith("hi") else ["en-IN"]
                },
                "audio": {
                    "content": audio_base64
                }
            }
            
            async with self.session.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result_data = await response.json()
                    
                    if "results" in result_data and result_data["results"]:
                        best_result = result_data["results"][0]
                        alternative = best_result["alternatives"][0]
                        
                        yield TranscriptionResult(
                            text=alternative["transcript"],
                            confidence=alternative.get("confidence", 0.0),
                            language=language,
                            is_final=True,
                            alternatives=[alt["transcript"] for alt in best_result["alternatives"][1:]]
                        )
                else:
                    logger.error(f"Google Speech API error: {response.status}")
                    
        except Exception as e:
            logger.error(f"Google Speech transcription error: {e}")
    
    async def transcribe_audio_file(
        self,
        audio_data: bytes,
        language: str = "hi-IN",
        audio_format: str = "wav"
    ) -> TranscriptionResult:
        """
        Transcribe uploaded audio file
        
        Args:
            audio_data: Audio file data
            language: Language code
            audio_format: Audio format (wav, mp3, etc.)
            
        Returns:
            TranscriptionResult
        """
        # Convert to stream and get first result
        async for result in self.transcribe_audio_stream(audio_data, language):
            return result
            
        # Fallback if no results
        return TranscriptionResult(
            text="",
            confidence=0.0,
            language=language,
            is_final=True
        )
    
    async def detect_language(self, audio_data: bytes) -> str:
        """
        Detect language from audio sample
        
        Args:
            audio_data: Audio data bytes
            
        Returns:
            Detected language code
        """
        # Try transcribing with multiple languages and pick best result
        languages_to_try = ["hi-IN", "en-IN", "en-US"]
        best_result = None
        best_confidence = 0.0
        
        for lang in languages_to_try:
            try:
                result = await self.transcribe_audio_file(audio_data, lang)
                if result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_result = lang
            except Exception as e:
                logger.warning(f"Language detection failed for {lang}: {e}")
                continue
        
        return best_result or "hi-IN"
    
    async def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return self.supported_languages
    
    async def validate_audio_format(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Validate audio format and provide recommendations
        
        Args:
            audio_data: Audio data to validate
            
        Returns:
            Validation result with recommendations
        """
        result = {
            "valid": False,
            "format": "unknown",
            "sample_rate": None,
            "channels": None,
            "duration": None,
            "recommendations": []
        }
        
        try:
            # Basic audio validation
            if len(audio_data) < 1000:  # Very small file
                result["recommendations"].append("Audio file too small, minimum 1 second required")
                return result
            
            if len(audio_data) > 10 * 1024 * 1024:  # 10MB limit
                result["recommendations"].append("Audio file too large, maximum 10MB allowed")
                return result
            
            # Check for common audio headers
            if audio_data.startswith(b'RIFF'):
                result["format"] = "wav"
                result["valid"] = True
            elif audio_data.startswith(b'ID3') or audio_data[0:2] == b'\xff\xfb':
                result["format"] = "mp3" 
                result["valid"] = True
            elif audio_data.startswith(b'OggS'):
                result["format"] = "ogg"
                result["valid"] = True
            elif audio_data.startswith(b'fLaC'):
                result["format"] = "flac"
                result["valid"] = True
            
            if result["valid"]:
                result["recommendations"].append("Audio format supported")
            else:
                result["recommendations"].append("Convert to WAV, MP3, or OGG format")
                result["recommendations"].append("Use 16kHz sample rate for best results")
                result["recommendations"].append("Mono channel recommended")
            
        except Exception as e:
            logger.error(f"Audio validation error: {e}")
            result["recommendations"].append("Audio file validation failed")
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """Check speech recognition service health"""
        return {
            "provider": self.provider,
            "available": self.provider != "none",
            "supported_languages": len(self.supported_languages),
            "azure_configured": bool(self.azure_speech_key),
            "google_configured": bool(self.google_api_key)
        }