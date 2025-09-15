"""
Voice Services Module

This module provides comprehensive voice services including:
- Murf AI text-to-speech integration
- Speech recognition services
- Voice command processing
- Audio optimization and caching
- Real-time voice streaming
- Service management and initialization
"""

import logging
import os
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

from .murf_service import MurfVoiceService, VoiceConfig
from .speech_recognition import SpeechRecognitionService, SpeechConfig
from .voice_processor import VoiceCommandProcessor
from .audio_optimizer import AudioOptimizer, AudioConfig
from .voice_cache import VoiceCache
from .voice_streaming import VoiceStreamingService, ConnectionManager

logger = logging.getLogger(__name__)

class VoiceServiceConfig:
    """Voice services configuration"""
    
    def __init__(self):
        # Murf AI Configuration
        self.murf_api_key = os.getenv("MURF_AI_API_KEY", "")
        self.murf_base_url = os.getenv("MURF_BASE_URL", "https://api.murf.ai/v1")
        
        # Azure Speech Configuration
        self.azure_speech_key = os.getenv("AZURE_SPEECH_KEY", "")
        self.azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        # Google Cloud Speech Configuration
        self.google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        
        # Redis Configuration for caching
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Voice Service Settings
        self.default_language = os.getenv("DEFAULT_VOICE_LANGUAGE", "hi-IN")
        self.default_quality = os.getenv("DEFAULT_AUDIO_QUALITY", "good")
        self.cache_enabled = os.getenv("VOICE_CACHE_ENABLED", "true").lower() == "true"
        self.streaming_enabled = os.getenv("VOICE_STREAMING_ENABLED", "true").lower() == "true"
        
        # Performance Settings
        self.max_concurrent_requests = int(os.getenv("MAX_VOICE_REQUESTS", "10"))
        self.request_timeout = int(os.getenv("VOICE_REQUEST_TIMEOUT", "30"))
        self.cache_ttl_hours = int(os.getenv("VOICE_CACHE_TTL_HOURS", "24"))
        
        # Agent Voice Mappings
        self.agent_voices = {
            "mitra": {
                "primary": "aditi",
                "backup": "priya", 
                "language": "hi-IN",
                "emotion": "empathetic"
            },
            "guru": {
                "primary": "arnav",
                "backup": "kabir",
                "language": "hi-IN", 
                "emotion": "professional"
            },
            "parikshak": {
                "primary": "alisha",
                "backup": "radhika",
                "language": "hi-IN",
                "emotion": "formal"
            }
        }

class VoiceServiceManager:
    """
    Central manager for all voice services
    """
    
    def __init__(self, config: Optional[VoiceServiceConfig] = None):
        self.config = config or VoiceServiceConfig()
        
        # Service instances
        self.murf_service: Optional[MurfVoiceService] = None
        self.speech_service: Optional[SpeechRecognitionService] = None
        self.voice_processor: Optional[VoiceCommandProcessor] = None
        self.audio_optimizer: Optional[AudioOptimizer] = None
        self.voice_cache: Optional[VoiceCache] = None
        self.streaming_service: Optional[VoiceStreamingService] = None
        
        # Service state
        self.is_initialized = False
        self.initialization_error = None
        
    async def initialize(self) -> bool:
        """
        Initialize all voice services
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing voice services...")
            
            # Initialize core services
            await self._initialize_cache()
            await self._initialize_audio_optimizer()
            await self._initialize_voice_processor()
            await self._initialize_murf_service()
            await self._initialize_speech_service()
            
            # Initialize streaming service if enabled
            if self.config.streaming_enabled:
                await self._initialize_streaming_service()
            
            # Validate services
            await self._validate_services()
            
            self.is_initialized = True
            logger.info("Voice services initialized successfully")
            return True
            
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"Voice services initialization failed: {e}")
            return False
    
    async def _initialize_cache(self):
        """Initialize voice cache service"""
        try:
            self.voice_cache = VoiceCache(
                redis_url=self.config.redis_url if self.config.cache_enabled else None,
                ttl_hours=self.config.cache_ttl_hours
            )
            
            # Test cache connection
            await self.voice_cache.get_cache_stats()
            logger.info("Voice cache initialized")
            
        except Exception as e:
            logger.warning(f"Voice cache initialization failed: {e}")
            # Create fallback in-memory cache
            self.voice_cache = VoiceCache(redis_url=None)
    
    async def _initialize_audio_optimizer(self):
        """Initialize audio optimization service"""
        try:
            self.audio_optimizer = AudioOptimizer()
            logger.info("Audio optimizer initialized")
            
        except Exception as e:
            logger.error(f"Audio optimizer initialization failed: {e}")
            raise
    
    async def _initialize_voice_processor(self):
        """Initialize voice command processor"""
        try:
            self.voice_processor = VoiceCommandProcessor()
            logger.info("Voice command processor initialized")
            
        except Exception as e:
            logger.error(f"Voice processor initialization failed: {e}")
            raise
    
    async def _initialize_murf_service(self):
        """Initialize Murf AI service"""
        try:
            if not self.config.murf_api_key:
                logger.warning("Murf AI API key not provided - TTS will be limited")
            
            self.murf_service = MurfVoiceService(
                api_key=self.config.murf_api_key,
                base_url=self.config.murf_base_url,
                voice_cache=self.voice_cache
            )
            
            # Configure agent voices
            for agent, voice_config in self.config.agent_voices.items():
                await self.murf_service.configure_agent_voice(agent, voice_config)
            
            logger.info("Murf AI service initialized")
            
        except Exception as e:
            logger.error(f"Murf service initialization failed: {e}")
            raise
    
    async def _initialize_speech_service(self):
        """Initialize speech recognition service"""
        try:
            # Determine available providers
            providers = []
            
            if self.config.azure_speech_key:
                providers.append("azure")
            
            if self.config.google_credentials_path and os.path.exists(self.config.google_credentials_path):
                providers.append("google")
            
            if not providers:
                logger.warning("No speech recognition providers configured")
                providers = ["azure"]  # Fallback
            
            speech_config = SpeechConfig(
                azure_key=self.config.azure_speech_key,
                azure_region=self.config.azure_speech_region,
                google_credentials_path=self.config.google_credentials_path,
                default_language=self.config.default_language,
                providers=providers
            )
            
            self.speech_service = SpeechRecognitionService(speech_config)
            logger.info(f"Speech recognition initialized with providers: {providers}")
            
        except Exception as e:
            logger.error(f"Speech service initialization failed: {e}")
            raise
    
    async def _initialize_streaming_service(self):
        """Initialize voice streaming service"""
        try:
            if not all([self.murf_service, self.speech_service, self.voice_processor, self.audio_optimizer]):
                raise ValueError("Core services not initialized for streaming")
            
            self.streaming_service = VoiceStreamingService(
                murf_service=self.murf_service,
                speech_service=self.speech_service,
                voice_processor=self.voice_processor,
                audio_optimizer=self.audio_optimizer
            )
            
            logger.info("Voice streaming service initialized")
            
        except Exception as e:
            logger.error(f"Streaming service initialization failed: {e}")
            raise
    
    async def _validate_services(self):
        """Validate that all services are working correctly"""
        try:
            # Test voice generation
            if self.murf_service and self.config.murf_api_key:
                test_audio = await self.murf_service.generate_speech(
                    text="Test",
                    agent="mitra"
                )
                if test_audio:
                    logger.info("Murf service validation successful")
                else:
                    logger.warning("Murf service validation failed")
            
            # Test speech recognition
            if self.speech_service:
                # Note: Can't easily test without audio data
                logger.info("Speech service available for testing")
            
            # Test voice processing
            if self.voice_processor:
                test_commands = await self.voice_processor.process_voice_command(
                    "नमस्ते मित्र",
                    language="hi-IN",
                    confidence=0.9
                )
                if test_commands:
                    logger.info("Voice processor validation successful")
            
        except Exception as e:
            logger.warning(f"Service validation error: {e}")
    
    # Service Access Methods
    
    def get_murf_service(self) -> Optional[MurfVoiceService]:
        """Get Murf AI TTS service"""
        return self.murf_service
    
    def get_speech_service(self) -> Optional[SpeechRecognitionService]:
        """Get speech recognition service"""
        return self.speech_service
    
    def get_voice_processor(self) -> Optional[VoiceCommandProcessor]:
        """Get voice command processor"""
        return self.voice_processor
    
    def get_audio_optimizer(self) -> Optional[AudioOptimizer]:
        """Get audio optimizer"""
        return self.audio_optimizer
    
    def get_voice_cache(self) -> Optional[VoiceCache]:
        """Get voice cache service"""
        return self.voice_cache
    
    def get_streaming_service(self) -> Optional[VoiceStreamingService]:
        """Get voice streaming service"""
        return self.streaming_service
    
    async def shutdown(self):
        """Shutdown all voice services"""
        try:
            logger.info("Shutting down voice services...")
            
            if self.streaming_service:
                await self.streaming_service.shutdown()
            
            if self.voice_cache:
                await self.voice_cache.close()
            
            self.is_initialized = False
            logger.info("Voice services shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during voice services shutdown: {e}")

# Global voice service manager instance
_voice_manager: Optional[VoiceServiceManager] = None

async def get_voice_manager() -> VoiceServiceManager:
    """
    Get the global voice service manager instance
    
    Returns:
        VoiceServiceManager instance
    """
    global _voice_manager
    
    if _voice_manager is None:
        _voice_manager = VoiceServiceManager()
        await _voice_manager.initialize()
    
    return _voice_manager

async def initialize_voice_services(config: Optional[VoiceServiceConfig] = None) -> VoiceServiceManager:
    """
    Initialize voice services with optional configuration
    
    Args:
        config: Voice service configuration
        
    Returns:
        Initialized VoiceServiceManager
    """
    global _voice_manager
    
    _voice_manager = VoiceServiceManager(config)
    success = await _voice_manager.initialize()
    
    if not success:
        logger.error("Failed to initialize voice services")
        raise RuntimeError(f"Voice services initialization failed: {_voice_manager.initialization_error}")
    
    return _voice_manager

async def shutdown_voice_services():
    """Shutdown global voice services"""
    global _voice_manager
    
    if _voice_manager:
        await _voice_manager.shutdown()
        _voice_manager = None

__all__ = [
    'MurfVoiceService',
    'SpeechRecognitionService', 
    'VoiceCommandProcessor',
    'AudioOptimizer',
    'VoiceCache',
    'VoiceStreamingService',
    'ConnectionManager',
    'VoiceServiceConfig',
    'VoiceServiceManager',
    'get_voice_manager',
    'initialize_voice_services',
    'shutdown_voice_services'
]