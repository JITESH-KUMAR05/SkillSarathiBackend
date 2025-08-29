"""
Streaming LLM Service for BuddyAgents
====================================

Simple streaming LLM service with WebSocket support
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
import json
import aiohttp
import os

logger = logging.getLogger(__name__)

class StreamingLLMService:
    """Service for streaming LLM responses with WebSocket support"""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.base_url = "https://models.inference.ai.azure.com/chat/completions"
        
    async def stream_response(
        self, 
        message: str, 
        agent_type: str = "mitra",
        websocket_sender: Optional[Callable] = None
    ) -> str:
        """Stream LLM response with optional WebSocket streaming"""
        
        try:
            if not self.github_token:
                return self._get_fallback_response(message, agent_type)
            
            # Create agent-specific system prompt
            system_prompt = self._get_agent_prompt(agent_type)
            
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    else:
                        logger.error(f"LLM API error: {response.status}")
                        return self._get_fallback_response(message, agent_type)
                        
        except Exception as e:
            logger.error(f"Streaming LLM error: {e}")
            return self._get_fallback_response(message, agent_type)
    
    def _get_agent_prompt(self, agent_type: str) -> str:
        """Get system prompt for specific agent"""
        
        prompts = {
            "mitra": """You are Mitra, a warm and empathetic AI friend from India. You're like a caring companion who:
- Speaks with warmth and understanding
- Provides emotional support and encouragement
- Shares wisdom through personal anecdotes and cultural references
- Uses occasional Hindi words naturally (with English explanations)
- Focuses on mental wellbeing and life balance
- Celebrates Indian values of friendship and community

Be conversational, caring, and culturally aware. Keep responses concise but heartfelt.""",
            
            "guru": """You are Guru, a wise AI teacher and mentor from India. You embody the traditional guru-shishya relationship with:
- Deep knowledge across multiple subjects
- Patient and encouraging teaching style
- Ability to break down complex concepts simply
- Focus on practical learning and skill development
- Integration of traditional Indian wisdom with modern knowledge
- Emphasis on character building alongside academic growth

Be knowledgeable, patient, and inspiring. Provide clear explanations with practical examples.""",
            
            "parikshak": """You are Parikshak, a professional AI interview coach and assessor from India. You are:
- Professional yet supportive in demeanor
- Expert in various interview formats and industries
- Skilled at providing constructive feedback
- Knowledgeable about Indian job market and global opportunities
- Focused on building confidence and communication skills
- Experienced in both technical and behavioral interviews

Be professional, encouraging, and provide actionable advice. Help candidates improve systematically."""
        }
        
        return prompts.get(agent_type, prompts["mitra"])
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """Generate a single response (non-streaming) - wrapper around stream_response"""
        
        try:
            if not self.github_token:
                return self._get_fallback_response(prompt, "mitra")
            
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": "gpt-4o",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return content if content else self._get_fallback_response(prompt, "mitra")
                    else:
                        logger.error(f"LLM API error: {response.status}")
                        return self._get_fallback_response(prompt, "mitra")
                        
        except Exception as e:
            logger.error(f"Generate response error: {e}")
            return self._get_fallback_response(prompt, "mitra")

    def _get_fallback_response(self, message: str, agent_type: str) -> str:
        """Get fallback response when LLM is unavailable"""
        
        fallbacks = {
            "mitra": f"🤗 Dear friend, I hear what you're saying about '{message}'. While I'd love to give you a more thoughtful response, I'm having some technical difficulties right now. But please know that I'm here for you, and your feelings matter. Can you tell me more about what's on your mind?",
            
            "guru": f"🧠 My dear student, you've raised an interesting point about '{message}'. Although I'm experiencing some technical challenges at the moment, I believe learning never stops. Let's think about this together - what specific aspect would you like to explore further? Your curiosity is the first step to wisdom.",
            
            "parikshak": f"💼 Thank you for that question about '{message}'. While I'm having some technical difficulties accessing my full knowledge base right now, I can tell this is important for your professional development. Let's work with what we have - can you elaborate on the specific context or challenge you're facing?"
        }
        
        return fallbacks.get(agent_type, fallbacks["mitra"])

# Legacy compatibility
StreamingLLMWrapper = StreamingLLMService
