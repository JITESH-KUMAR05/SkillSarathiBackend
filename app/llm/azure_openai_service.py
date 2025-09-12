"""
Azure OpenAI Service Implementation with Advanced Model Router
Supports GPT-5, Sora video generation, realtime audio, and transcription
"""

import os
import json
import asyncio
import logging
import aiohttp
import base64
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncAzureOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Production Azure OpenAI service with advanced model routing for BuddyAgents platform"""
    
    def __init__(self):
        """Initialize Azure OpenAI client with environment variables"""
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Advanced model deployments with routing capabilities
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "buddyagents-model-router")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        # Specialized model deployments
        self.sora_deployment = os.getenv("AZURE_SORA_DEPLOYMENT", "sora-buddyagents")
        self.realtime_deployment = os.getenv("AZURE_REALTIME_DEPLOYMENT", "gpt-realtime-buddyagents")
        self.transcribe_deployment = os.getenv("AZURE_TRANSCRIBE_DEPLOYMENT", "gpt-4o-transcribe-buddyagents")
        
        # Azure endpoint and API key for advanced features
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        # Agent-specific system prompts optimized for model router
        self.system_prompts = {
            "mitra": """You are Mitra (मित्र), a warm and caring AI friend for Indian users. 
                       Provide emotional support, listen to problems, and offer friendly advice. 
                       Mix Hindi and English naturally (Hinglish). Be empathetic, understanding, and culturally aware.
                       Keep responses conversational and supportive, typically 2-3 sentences unless more detail is needed.
                       The model router will automatically select the best model (GPT-5-nano for simple chats, GPT-5 for complex emotional guidance).""",
            
            "guru": """You are Guru (गुरु), an AI learning mentor specializing in education and skill development. 
                      Help with studies, career guidance, interview preparation, and learning new skills. 
                      Be patient, encouraging, and provide structured, actionable learning advice.
                      Use examples relevant to Indian context. Keep responses informative but comprehensive.
                      The model router will select GPT-5 for complex teaching scenarios, GPT-4.1 for coding tutorials.""",
            
            "parikshak": """You are Parikshak (परीक्षक), an AI interview coach and technical assessor. 
                          Help with interview preparation, conduct mock interviews, and provide technical assessments. 
                          Be professional, provide constructive feedback, and help improve interview skills.
                          Focus on Indian job market context and common interview practices.
                          The model router will use GPT-4.1 for technical assessments, GPT-5 for behavioral coaching."""
        }
        
        logger.info("� Advanced Azure OpenAI Service initialized with Model Router, Sora, and Realtime capabilities")
    
    async def health_check(self) -> bool:
        """Check if Azure OpenAI service is available"""
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            logger.info(f"✅ Model Router Health Check - Selected Model: {response.model}")
            return True
        except Exception as e:
            logger.error(f"❌ Azure OpenAI health check failed: {e}")
            return False
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]],
        agent_type: str = "mitra",
        stream: bool = False,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from Azure OpenAI
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            agent_type: Type of agent (mitra, guru, parikshak)
            stream: Whether to stream the response
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
        """
        try:
            # Add agent-specific system prompt
            system_prompt = self.system_prompts.get(agent_type, self.system_prompts["mitra"])
            full_messages = [
                {"role": "system", "content": system_prompt},
                *messages
            ]
            
            if stream:
                # Streaming response for real-time UX
                async with self.client.chat.completions.create(
                    model=self.chat_deployment,
                    messages=full_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                ) as response:
                    async for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                    
                    # Log which model was actually used by the router
                    try:
                        if hasattr(response, 'model'):
                            logger.info(f"🎯 Model Router selected: {response.model} for {agent_type}")
                    except:
                        pass
            else:
                # Non-streaming response
                response = await self.client.chat.completions.create(
                    model=self.chat_deployment,
                    messages=full_messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                if response.choices:
                    yield response.choices[0].message.content
                    
        except Exception as e:
            error_msg = f"Azure OpenAI error: {str(e)}"
            logger.error(error_msg)
            yield "I'm experiencing technical difficulties. Please try again in a moment."
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for RAG system"""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_deployment,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return []
    
    def convert_langchain_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to Azure OpenAI format"""
        converted = []
        for message in messages:
            if isinstance(message, SystemMessage):
                converted.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                converted.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                converted.append({"role": "assistant", "content": message.content})
        return converted
    
    async def generate_video(
        self, 
        prompt: str, 
        height: int = 1080, 
        width: int = 1080, 
        duration: int = 5,
        variants: int = 1
    ) -> Dict[str, Any]:
        """
        Generate video using Sora model
        
        Args:
            prompt: Text description for video generation
            height: Video height in pixels
            width: Video width in pixels  
            duration: Video duration in seconds
            variants: Number of video variants to generate
            
        Returns:
            Dict with job ID and status for video generation
        """
        try:
            url = f"{self.endpoint}openai/v1/video/generations/jobs?api-version=preview"
            
            headers = {
                "Content-Type": "application/json",
                "Api-key": self.api_key
            }
            
            payload = {
                "model": "sora",
                "prompt": prompt,
                "height": str(height),
                "width": str(width),
                "n_seconds": str(duration),
                "n_variants": str(variants)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    result = await response.json()
                    logger.info(f"🎬 Sora video generation started: {result}")
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Sora video generation error: {e}")
            return {"error": str(e)}
    
    async def transcribe_audio(self, audio_file_path: str, language: str = "en") -> Dict[str, Any]:
        """
        Transcribe audio using GPT-4o-Transcribe
        
        Args:
            audio_file_path: Path to audio file
            language: Language code for transcription
            
        Returns:
            Dict with transcription text and metadata
        """
        try:
            url = f"{self.endpoint}openai/deployments/{self.transcribe_deployment}/audio/transcriptions?api-version=2025-03-01-preview"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Read audio file
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (audio_file_path, audio_file, 'audio/mpeg'),
                }
                data = {
                    'model': 'gpt-4o-transcribe',
                    'language': language
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=data) as response:
                        result = await response.json()
                        logger.info(f"🎤 Audio transcription completed")
                        return result
                        
        except Exception as e:
            logger.error(f"❌ Audio transcription error: {e}")
            return {"error": str(e)}
    
    async def realtime_audio_chat(
        self, 
        audio_input: bytes, 
        agent_type: str = "mitra",
        voice: str = "alloy"
    ) -> bytes:
        """
        Handle realtime audio conversation using GPT-Realtime
        
        Args:
            audio_input: Input audio bytes
            agent_type: Type of agent for personality
            voice: Voice type for response
            
        Returns:
            Audio response bytes
        """
        try:
            # This would integrate with the GPT-Realtime API
            # For now, return a placeholder implementation
            logger.info(f"🎙️ Realtime audio chat initiated for {agent_type}")
            
            # In production, implement WebSocket connection to GPT-Realtime
            # For MVP, use transcription + chat + TTS pipeline
            
            # 1. Transcribe input audio
            # 2. Generate chat response  
            # 3. Convert to speech with Murf AI
            
            return b"placeholder_audio_response"
            
        except Exception as e:
            logger.error(f"❌ Realtime audio error: {e}")
            return b""
    
    async def get_model_capabilities(self) -> Dict[str, Any]:
        """Get information about available models and their capabilities"""
        return {
            "chat_model": self.chat_deployment,
            "capabilities": {
                "model_router": {
                    "available_models": ["GPT-5", "GPT-5-mini", "GPT-5-nano", "GPT-4.1", "o4-mini"],
                    "auto_routing": True,
                    "cost_optimization": True
                },
                "video_generation": {
                    "model": self.sora_deployment,
                    "max_duration": 20,
                    "max_resolution": "1080p"
                },
                "audio_transcription": {
                    "model": self.transcribe_deployment,
                    "context_window": "16k",
                    "languages": ["en", "hi", "bn", "ta", "te", "gu", "mr", "kn", "ml", "pa"]
                },
                "realtime_audio": {
                    "model": self.realtime_deployment,
                    "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                    "function_calling": True
                }
            }
        }

# Global instance for dependency injection
azure_openai_service = AzureOpenAIService()