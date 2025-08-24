"""
LLM Factory for Skillsarathi AI - Real GitHub Integration
"""

import logging
from typing import Optional, Dict, Any
from langchain.schema import ChatGeneration, LLMResult, AIMessage, HumanMessage, BaseMessage

logger = logging.getLogger(__name__)

class GitHubLLM:
    """Real GitHub Models API LLM - Non-pydantic implementation"""
    
    def __init__(self, github_token: str, model: str = "gpt-4o"):
        self.github_token = github_token
        self.model = model
        self.api_url = "https://models.inference.ai.azure.com/chat/completions"
        self._llm_type = "github"
    
    async def agenerate(self, messages_list, **kwargs):
        """Generate response using GitHub Models API (async)"""
        import aiohttp
        
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
            
            logger.info(f"Calling GitHub API with {len(api_messages)} messages")
            
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
                        logger.info("GitHub API response received successfully")
                        
                        generation = ChatGeneration(message=AIMessage(content=content))
                        return LLMResult(generations=[[generation]])
                    else:
                        error_text = await response.text()
                        logger.error(f"GitHub API error {response.status}: {error_text}")
                        raise Exception(f"GitHub API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"GitHub LLM error: {e}")
            # Return error response instead of falling back
            generation = ChatGeneration(message=AIMessage(content=f"GitHub AI service error: {str(e)}"))
            return LLMResult(generations=[[generation]])

class SimpleLLM:
    """Simple fallback LLM for testing"""
    
    def __init__(self):
        self._llm_type = "simple"
    
    async def agenerate(self, messages_list, **kwargs):
        """Generate simple response"""
        try:
            messages = messages_list[0] if messages_list else []
            user_input = ""
            
            for msg in messages:
                if hasattr(msg, 'content'):
                    user_input = msg.content
                    break
            
            # Simple response pattern
            response = f"I understand you said: '{user_input}'. I'm here to help you with minimal latency!"
            generation = ChatGeneration(message=AIMessage(content=response))
            return LLMResult(generations=[[generation]])
            
        except Exception as e:
            logger.error(f"Simple LLM error: {e}")
            generation = ChatGeneration(message=AIMessage(content="Error in simple LLM"))
            return LLMResult(generations=[[generation]])

class LLMFactory:
    """Factory class for creating LLM instances"""
    
    def __init__(self):
        pass
    
    def create_llm(self, llm_type: str = "github", **kwargs):
        """Create LLM instance based on configuration"""
        
        # Try GitHub Models API first
        if llm_type == "github":
            try:
                from app.core.config import settings
                if settings.GITHUB_TOKEN:
                    logger.info("Creating GitHub LLM instance")
                    return GitHubLLM(github_token=settings.GITHUB_TOKEN)
                else:
                    logger.warning("No GitHub token found")
            except Exception as e:
                logger.warning(f"Failed to create GitHub LLM: {e}")
        
        # Fallback to simple LLM
        logger.info("Creating Simple LLM fallback")
        return SimpleLLM()

# Global factory instance
llm_factory = LLMFactory()

def get_llm(**kwargs):
    """Get LLM instance with fallback strategy"""
    return llm_factory.create_llm(**kwargs)
