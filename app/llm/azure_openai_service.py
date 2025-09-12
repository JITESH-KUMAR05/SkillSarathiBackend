"""
Azure OpenAI Service Implementation
Replaces GitHub LLM with Azure OpenAI for production-ready GPT-4o access
"""

import os
import json
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from openai import AsyncAzureOpenAI
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)

class AzureOpenAIService:
    """Production Azure OpenAI service for BuddyAgents platform"""
    
    def __init__(self):
        """Initialize Azure OpenAI client with environment variables"""
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        # Model deployments (must match your Azure OpenAI Studio deployments)
        self.chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
        self.embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        
        # Agent-specific system prompts for optimized responses
        self.system_prompts = {
            "mitra": """You are Mitra (मित्र), a warm and caring AI friend for Indian users. 
                       Provide emotional support, listen to problems, and offer friendly advice. 
                       Mix Hindi and English naturally (Hinglish). Be empathetic, understanding, and culturally aware.
                       Keep responses conversational and supportive, typically 2-3 sentences unless more detail is needed.""",
            
            "guru": """You are Guru (गुरु), an AI learning mentor specializing in education and skill development. 
                      Help with studies, career guidance, interview preparation, and learning new skills. 
                      Be patient, encouraging, and provide structured, actionable learning advice.
                      Use examples relevant to Indian context. Keep responses informative but concise.""",
            
            "parikshak": """You are Parikshak (परीक्षक), an AI interview coach and technical assessor. 
                          Help with interview preparation, conduct mock interviews, and provide technical assessments. 
                          Be professional, provide constructive feedback, and help improve interview skills.
                          Focus on Indian job market context and common interview practices."""
        }
        
        logger.info("🔵 Azure OpenAI Service initialized successfully")
    
    async def health_check(self) -> bool:
        """Check if Azure OpenAI service is available"""
        try:
            response = await self.client.chat.completions.create(
                model=self.chat_deployment,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"Azure OpenAI health check failed: {e}")
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

# Global instance for dependency injection
azure_openai_service = AzureOpenAIService()