"""
Fixed LLM Factory for Skillsarathi AI - Working Real AI Integration
"""

import logging
import os
from typing import Optional
from langchain.schema import ChatGeneration, LLMResult, AIMessage, HumanMessage, BaseMessage
import aiohttp

logger = logging.getLogger(__name__)

class WorkingGitHubLLM:
    """Working GitHub Models API LLM implementation"""
    
    def __init__(self, github_token: str, model: str = "gpt-4o"):
        self.github_token = github_token
        self.model = model
        self.api_url = "https://models.inference.ai.azure.com/chat/completions"
        self._llm_type = "github"
    
    async def agenerate(self, messages_list, **kwargs):
        """Generate response using GitHub Models API"""
        try:
            # Get first message list
            messages = messages_list[0] if messages_list else []
            
            # Convert messages to API format
            api_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    if msg.__class__.__name__ == 'HumanMessage':
                        api_messages.append({"role": "user", "content": msg.content})
                    elif msg.__class__.__name__ == 'AIMessage':
                        api_messages.append({"role": "assistant", "content": msg.content})
                else:
                    api_messages.append({"role": "user", "content": str(msg)})
            
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            logger.info(f"🚀 Calling GitHub API for real AI response")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        logger.info("✅ Real AI response generated successfully")
                        
                        generation = ChatGeneration(message=AIMessage(content=content))
                        return LLMResult(generations=[[generation]])
                    else:
                        error_text = await response.text()
                        logger.error(f"GitHub API error {response.status}: {error_text}")
                        generation = ChatGeneration(message=AIMessage(content=f"AI service error: {error_text}"))
                        return LLMResult(generations=[[generation]])
                        
        except Exception as e:
            logger.error(f"GitHub LLM error: {e}")
            generation = ChatGeneration(message=AIMessage(content=f"Sorry, I'm having trouble: {str(e)}"))
            return LLMResult(generations=[[generation]])

class SimpleLLM:
    """Simple fallback LLM for testing only"""
    
    def __init__(self):
        self._llm_type = "simple"
    
    async def agenerate(self, messages_list, **kwargs):
        """Generate simple fallback response"""
        try:
            messages = messages_list[0] if messages_list else []
            user_input = ""
            
            for msg in messages:
                if hasattr(msg, 'content'):
                    user_input = msg.content
                    break
            
            # Note: This should only be used as fallback
            response = f"⚠️ FALLBACK MODE: Real AI is unavailable. You said: '{user_input}'"
            generation = ChatGeneration(message=AIMessage(content=response))
            return LLMResult(generations=[[generation]])
            
        except Exception as e:
            logger.error(f"Simple LLM error: {e}")
            generation = ChatGeneration(message=AIMessage(content="Error in fallback system"))
            return LLMResult(generations=[[generation]])

class LLMFactory:
    """Factory class for creating working LLM instances"""
    
    def __init__(self):
        pass
    
    def create_llm(self, llm_type: str = "github", **kwargs):
        """Create working LLM instance"""
        
        # Try GitHub Models API first (REAL AI)
        if llm_type == "github":
            try:
                from app.core.config import settings
                if settings.GITHUB_TOKEN:
                    logger.info("🚀 Creating REAL GitHub LLM (no fallback)")
                    return WorkingGitHubLLM(github_token=settings.GITHUB_TOKEN)
                else:
                    logger.error("❌ No GitHub token - CANNOT USE REAL AI")
            except Exception as e:
                logger.error(f"❌ Failed to create GitHub LLM: {e}")
        
        # Only fallback if absolutely necessary
        logger.warning("⚠️ Using Simple LLM fallback - NOT REAL AI")
        return SimpleLLM()

# Global factory instance
llm_factory = LLMFactory()

def get_llm(**kwargs):
    """Get working LLM instance with real AI"""
    return llm_factory.create_llm(**kwargs)
