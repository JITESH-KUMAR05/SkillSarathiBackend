"""
Production Azure OpenAI Service with Multi-Region Support
Handles Model Router, Sora, GPT-Realtime, and Transcription across dual regions
"""

import asyncio
import logging
import aiohttp
import json
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion
from openai._exceptions import APIError, RateLimitError, APIConnectionError

from app.core.config import get_settings, AgentConfig

logger = logging.getLogger(__name__)
settings = get_settings()


class ModelType(Enum):
    """Enumeration of available model types"""
    CHAT = "chat"
    VIDEO = "video"
    TRANSCRIPTION = "transcription"
    REALTIME = "realtime"


class RegionType(Enum):
    """Enumeration of Azure regions"""
    PRIMARY = "primary"      # East US 2
    SECONDARY = "secondary"  # Sweden Central


class AzureOpenAIService:
    """
    Production-ready Azure OpenAI service with:
    - Dual-region support for high availability
    - Intelligent model routing (GPT-5, GPT-4.1, etc.)
    - Video generation with Sora
    - Real-time audio with GPT-Realtime
    - Advanced transcription with GPT-4o-Transcribe
    - Error handling and fallback mechanisms
    - Performance monitoring and logging
    """
    
    def __init__(self):
        """Initialize Azure OpenAI clients for both regions"""
        
        # Primary client (East US 2) - Main operations
        self.primary_client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key_primary,
            api_version=settings.azure_openai_api_version_chat,
            azure_endpoint=settings.azure_openai_endpoint_primary
        )
        
        # Secondary client (Sweden Central) - GPT-Realtime
        self.secondary_client = AsyncAzureOpenAI(
            api_key=settings.azure_openai_api_key_secondary,
            api_version=settings.azure_openai_api_version_realtime,
            azure_endpoint=settings.azure_openai_endpoint_secondary
        )
        
        # Client configuration
        self.clients = {
            RegionType.PRIMARY: self.primary_client,
            RegionType.SECONDARY: self.secondary_client
        }
        
        # Model deployment mappings
        self.deployments = {
            ModelType.CHAT: settings.model_router_deployment,
            ModelType.VIDEO: settings.sora_deployment,
            ModelType.TRANSCRIPTION: settings.gpt_transcribe_deployment,
            ModelType.REALTIME: settings.gpt_realtime_deployment
        }
        
        # Performance monitoring
        self.request_count = 0
        self.error_count = 0
        self.last_health_check = {}
        
        logger.info("🚀 Azure OpenAI Service initialized with dual-region support")
    
    async def health_check(self, region: RegionType = RegionType.PRIMARY) -> Dict[str, Any]:
        """
        Comprehensive health check for Azure OpenAI services
        
        Args:
            region: Which region to check
            
        Returns:
            Dict with health status and metrics
        """
        client = self.clients[region]
        health_status = {
            "region": region.value,
            "timestamp": datetime.utcnow().isoformat(),
            "healthy": False,
            "services": {},
            "response_time_ms": 0,
            "error": None
        }
        
        start_time = time.time()
        
        try:
            # Test chat model (Model Router)
            chat_response = await client.chat.completions.create(
                model=self.deployments[ModelType.CHAT],
                messages=[{"role": "user", "content": "Health check"}],
                max_tokens=5,
                temperature=0
            )
            
            health_status["services"]["chat"] = {
                "healthy": True,
                "model_selected": getattr(chat_response, 'model', 'unknown'),
                "deployment": self.deployments[ModelType.CHAT]
            }
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            health_status["response_time_ms"] = round(response_time, 2)
            health_status["healthy"] = True
            
            # Update cache
            self.last_health_check[region] = health_status
            
            logger.info(f"✅ Health check passed for {region.value} region in {response_time:.2f}ms")
            
        except Exception as e:
            health_status["error"] = str(e)
            health_status["services"]["chat"] = {"healthy": False, "error": str(e)}
            logger.error(f"❌ Health check failed for {region.value} region: {e}")
        
        return health_status
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        agent_type: str = "mitra",
        stream: bool = False,
        max_tokens: int = 500,
        temperature: float = 0.7,
        region: RegionType = RegionType.PRIMARY
    ) -> Union[AsyncGenerator[str, None], str]:
        """
        Generate chat response using Model Router for intelligent model selection
        
        Args:
            messages: Conversation messages
            agent_type: Type of agent (mitra, guru, parikshak)
            stream: Whether to stream the response
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
            region: Azure region to use
            
        Returns:
            Streaming generator or complete response string
        """
        try:
            # Get agent configuration
            agent_config = AgentConfig.get_agent_config(agent_type)
            
            # Prepare messages with system prompt
            full_messages = [
                {"role": "system", "content": agent_config["system_prompt"]}
            ] + messages
            
            # Select client and deployment
            client = self.clients[region]
            deployment = self.deployments[ModelType.CHAT]
            
            # Log request
            logger.info(f"🎯 Chat request to {agent_type} via {region.value} region")
            self.request_count += 1
            
            # Create chat completion
            response = await client.chat.completions.create(
                model=deployment,
                messages=full_messages,
                max_tokens=min(max_tokens, agent_config.get("max_tokens", 500)),
                temperature=temperature,
                stream=stream
            )
            
            if stream:
                return self._stream_chat_response(response, agent_type, region)
            else:
                content = response.choices[0].message.content
                
                # Log model selection
                selected_model = getattr(response, 'model', 'unknown')
                logger.info(f"🤖 Model Router selected: {selected_model} for {agent_type}")
                
                return content
        
        except Exception as e:
            logger.error(f"❌ Chat generation error: {e}")
            self.error_count += 1
            
            # Try fallback region if primary fails
            if region == RegionType.PRIMARY:
                try:
                    return await self.generate_chat_response(
                        messages, agent_type, stream, max_tokens, temperature, RegionType.SECONDARY
                    )
                except Exception as fallback_error:
                    logger.error(f"❌ Fallback region also failed: {fallback_error}")
            
            return "I'm experiencing technical difficulties. Please try again in a moment."
    
    async def _stream_chat_response(
        self, 
        response: Any, 
        agent_type: str, 
        region: RegionType
    ) -> AsyncGenerator[str, None]:
        """Stream chat response chunks"""
        try:
            selected_model = None
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                
                # Capture model selection info
                if hasattr(chunk, 'model') and not selected_model:
                    selected_model = chunk.model
            
            if selected_model:
                logger.info(f"🤖 Model Router selected: {selected_model} for {agent_type}")
                
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            yield "Error occurred while streaming response."
    
    async def generate_video(
        self,
        prompt: str,
        height: int = 1080,
        width: int = 1920,
        duration: int = 10,
        variants: int = 1,
        region: RegionType = RegionType.PRIMARY
    ) -> Dict[str, Any]:
        """
        Generate video using Sora model
        
        Args:
            prompt: Text description for video generation
            height: Video height in pixels
            width: Video width in pixels  
            duration: Video duration in seconds (max 20)
            variants: Number of video variants to generate
            region: Azure region to use
            
        Returns:
            Dict with job ID and status for video generation
        """
        try:
            # Get endpoint and API key for the region
            if region == RegionType.PRIMARY:
                endpoint = settings.azure_openai_endpoint_primary
                api_key = settings.azure_openai_api_key_primary
            else:
                endpoint = settings.azure_openai_endpoint_secondary
                api_key = settings.azure_openai_api_key_secondary
            
            url = f"{endpoint}openai/v1/video/generations/jobs?api-version={settings.azure_openai_api_version_video}"
            
            headers = {
                "Content-Type": "application/json",
                "Api-key": api_key
            }
            
            # Validate and prepare payload
            duration = min(duration, 20)  # Cap at 20 seconds
            payload = {
                "model": self.deployments[ModelType.VIDEO],
                "prompt": prompt,
                "height": str(height),
                "width": str(width),
                "n_seconds": str(duration),
                "n_variants": str(variants)
            }
            
            logger.info(f"🎬 Starting Sora video generation in {region.value} region")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"✅ Video generation job created: {result.get('id', 'unknown')}")
                        return {
                            "status": "success",
                            "job_id": result.get("id"),
                            "region": region.value,
                            "estimated_completion": f"{duration + 30} seconds",
                            "job_details": result
                        }
                    else:
                        logger.error(f"❌ Video generation failed: {result}")
                        return {
                            "status": "error",
                            "error": result.get("error", "Unknown error"),
                            "region": region.value
                        }
        
        except Exception as e:
            logger.error(f"❌ Video generation error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "region": region.value
            }
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: str = "en",
        region: RegionType = RegionType.PRIMARY
    ) -> Dict[str, Any]:
        """
        Transcribe audio using GPT-4o-Transcribe
        
        Args:
            audio_file_path: Path to audio file
            language: Language code for transcription
            region: Azure region to use
            
        Returns:
            Dict with transcription text and metadata
        """
        try:
            # Get endpoint and API key for the region
            if region == RegionType.PRIMARY:
                endpoint = settings.azure_openai_endpoint_primary
                api_key = settings.azure_openai_api_key_primary
            else:
                endpoint = settings.azure_openai_endpoint_secondary
                api_key = settings.azure_openai_api_key_secondary
            
            url = f"{endpoint}openai/deployments/{self.deployments[ModelType.TRANSCRIPTION]}/audio/transcriptions?api-version={settings.azure_openai_api_version_transcribe}"
            
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            logger.info(f"🎤 Starting audio transcription in {region.value} region")
            
            # Prepare form data
            with open(audio_file_path, 'rb') as audio_file:
                form_data = aiohttp.FormData()
                form_data.add_field('file', audio_file, filename='audio.mp3', content_type='audio/mpeg')
                form_data.add_field('model', self.deployments[ModelType.TRANSCRIPTION])
                form_data.add_field('language', language)
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=form_data) as response:
                        result = await response.json()
                        
                        if response.status == 200:
                            logger.info("✅ Audio transcription completed successfully")
                            return {
                                "status": "success",
                                "transcription": result.get("text", ""),
                                "language": language,
                                "region": region.value,
                                "model": self.deployments[ModelType.TRANSCRIPTION],
                                "metadata": result
                            }
                        else:
                            logger.error(f"❌ Transcription failed: {result}")
                            return {
                                "status": "error",
                                "error": result.get("error", "Unknown error"),
                                "region": region.value
                            }
        
        except Exception as e:
            logger.error(f"❌ Audio transcription error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "region": region.value
            }
    
    async def get_model_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive information about available models and capabilities"""
        return {
            "service_info": {
                "version": "2.0.0",
                "regions": {
                    "primary": {
                        "location": "East US 2",
                        "endpoint": settings.azure_openai_endpoint_primary,
                        "capabilities": ["chat", "video", "transcription"]
                    },
                    "secondary": {
                        "location": "Sweden Central", 
                        "endpoint": settings.azure_openai_endpoint_secondary,
                        "capabilities": ["chat", "realtime", "transcription"]
                    }
                }
            },
            "models": {
                "chat_model": {
                    "deployment": self.deployments[ModelType.CHAT],
                    "description": "Model Router with GPT-5, GPT-4.1, o4-mini auto-selection",
                    "features": [
                        "Automatic model selection based on complexity",
                        "Cost optimization",
                        "Multi-language support",
                        "Agent-specific personas"
                    ],
                    "available_models": ["GPT-5", "GPT-5-mini", "GPT-5-nano", "GPT-4.1", "o4-mini"]
                },
                "video_generation": {
                    "deployment": self.deployments[ModelType.VIDEO],
                    "description": "Sora video generation model",
                    "features": [
                        "Up to 20 seconds duration",
                        "1080p resolution support",
                        "Custom prompts",
                        "Interview scenarios"
                    ],
                    "max_duration": 20,
                    "supported_resolutions": ["1920x1080", "1080x1920", "1080x1080"]
                },
                "transcription": {
                    "deployment": self.deployments[ModelType.TRANSCRIPTION],
                    "description": "GPT-4o-Transcribe with 16k context window",
                    "features": [
                        "16k context window",
                        "Multi-language support",
                        "High accuracy",
                        "Specialized audio datasets"
                    ],
                    "supported_languages": ["en", "hi", "bn", "ta", "te", "gu", "mr", "kn", "ml", "pa"]
                },
                "realtime_audio": {
                    "deployment": self.deployments[ModelType.REALTIME],
                    "description": "GPT-Realtime for speech-to-speech",
                    "features": [
                        "Real-time conversations",
                        "Natural voices",
                        "Function calling support",
                        "Low latency"
                    ],
                    "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                }
            },
            "agents": AgentConfig.AGENTS,
            "performance": {
                "total_requests": self.request_count,
                "error_count": self.error_count,
                "error_rate": f"{(self.error_count / max(self.request_count, 1)) * 100:.2f}%",
                "last_health_check": self.last_health_check
            }
        }
    
    async def get_video_status(self, job_id: str, region: RegionType = RegionType.PRIMARY) -> Dict[str, Any]:
        """
        Check the status of a video generation job
        
        Args:
            job_id: Video generation job ID
            region: Azure region where job was created
            
        Returns:
            Dict with job status and download URL if complete
        """
        try:
            # Get endpoint and API key for the region
            if region == RegionType.PRIMARY:
                endpoint = settings.azure_openai_endpoint_primary
                api_key = settings.azure_openai_api_key_primary
            else:
                endpoint = settings.azure_openai_endpoint_secondary
                api_key = settings.azure_openai_api_key_secondary
            
            url = f"{endpoint}openai/v1/video/generations/jobs/{job_id}?api-version={settings.azure_openai_api_version_video}"
            
            headers = {
                "Api-key": api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return {
                            "status": "success",
                            "job_status": result.get("status", "unknown"),
                            "region": region.value,
                            "job_details": result
                        }
                    else:
                        return {
                            "status": "error",
                            "error": result.get("error", "Job not found"),
                            "region": region.value
                        }
        
        except Exception as e:
            logger.error(f"❌ Video status check error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "region": region.value
            }


# Global service instance
azure_openai_service = AzureOpenAIService()