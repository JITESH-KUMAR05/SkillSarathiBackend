"""
Enhanced LLM Factory for Skillsarathi AI with GitHub integration
"""

from typing import Any, Optional, Union
import logging
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.chat_models.base import BaseChatModel

logger = logging.getLogger(__name__)

class SimpleLLM(BaseChatModel):
    """Simple LLM for testing with minimal latency"""
    
    def __init__(self):
        super().__init__()
        
    @property
    def _llm_type(self) -> str:
        return "simple"
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate a simple response"""
        if messages:
            last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            response = f"I understand you said: '{last_message}'. I'm here to help you with minimal latency!"
        else:
            response = "Hello! I'm ready to assist you."
        
        from langchain.schema import ChatGeneration, LLMResult
        generation = ChatGeneration(message=AIMessage(content=response))
        return LLMResult(generations=[[generation]])
    
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """Async generate for minimal latency"""
        # Convert messages to proper format
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, str):
                formatted_messages.append(HumanMessage(content=msg))
            else:
                formatted_messages.append(msg)
        
        return self._generate(formatted_messages, stop, None, **kwargs)

class GitHubLLM(BaseChatModel):
    """GitHub Models API LLM with real API integration"""
    
    def __init__(self, github_token: str, model: str = "gpt-4o"):
        super().__init__()
        self.github_token = github_token
        self.model = model
        self.api_url = "https://models.inference.ai.azure.com/chat/completions"
    
    @property
    def _llm_type(self) -> str:
        return "github"
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """Generate response using GitHub Models API"""
        import requests
        
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if isinstance(msg, HumanMessage):
                    api_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
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
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                from langchain.schema import ChatGeneration, LLMResult
                generation = ChatGeneration(message=AIMessage(content=content))
                return LLMResult(generations=[[generation]])
            else:
                logger.error(f"GitHub API error: {response.status_code}")
                raise Exception(f"API error: {response.status_code}")
        except Exception as e:
            logger.error(f"GitHub LLM error: {e}")
            # Fallback response
            from langchain.schema import ChatGeneration, LLMResult
            generation = ChatGeneration(message=AIMessage(content="I'm experiencing issues with the AI service. Please try again."))
            return LLMResult(generations=[[generation]])
    
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        """Async generate for real-time performance"""
        import aiohttp
        
        # Convert messages to API format
        api_messages = []
        for msg in messages:
            if hasattr(msg, 'content'):
                if isinstance(msg, HumanMessage):
                    api_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
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
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        from langchain.schema import ChatGeneration, LLMResult
                        generation = ChatGeneration(message=AIMessage(content=content))
                        return LLMResult(generations=[[generation]])
                    else:
                        logger.error(f"GitHub API error: {response.status}")
                        raise Exception(f"API error: {response.status}")
        except Exception as e:
            logger.error(f"GitHub LLM async error: {e}")
            # Fallback response
            from langchain.schema import ChatGeneration, LLMResult
            generation = ChatGeneration(message=AIMessage(content="I'm experiencing issues with the AI service. Please try again."))
            return LLMResult(generations=[[generation]])

class LLMFactory:
    """Factory class for creating different LLM instances"""
    
    def __init__(self):
        pass
    
    def create_llm(self, llm_type: str = "github", **kwargs) -> BaseChatModel:
        """Create LLM instance based on configuration"""
        
        # Try GitHub Models API first
        if llm_type == "github":
            try:
                from app.core.config import settings
                if settings.GITHUB_TOKEN:
                    logger.info("Using GitHub Models API")
                    return GitHubLLM(github_token=settings.GITHUB_TOKEN)
                else:
                    logger.warning("No GitHub token found")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub LLM: {e}")
        
        # Fallback to simple LLM
        logger.info("Using Simple LLM fallback")
        return SimpleLLM()

# Global factory instance
llm_factory = LLMFactory()

def get_llm(**kwargs) -> BaseChatModel:
    """Get LLM instance with fallback strategy for minimal latency"""
    return llm_factory.create_llm(**kwargs)
