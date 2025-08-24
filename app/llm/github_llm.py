"""
GitHub-based LLM implementation to access GPT-4o via GitHub Copilot API
This module provides a fallback when OpenAI or Azure OpenAI keys are not available
"""

import os
import json
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Union
from pydantic import Field
from langchain.chat_models.base import BaseChatModel
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage, LLMResult, ChatGeneration
from langchain.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)

class GitHubLLM(BaseChatModel):
    """
    LangChain-compatible LLM that uses GitHub Copilot API to access GPT-4o
    """
    
    github_token: str = Field(...)
    model: str = Field(default="gpt-4o")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=1024)
    streaming: bool = Field(default=False)
    api_url: str = Field(default="https://api.githubcopilot.com/chat/completions")
        
    @property
    def _llm_type(self) -> str:
        return "github-copilot"
    
    async def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to GitHub Copilot API format"""
        prompt_messages = []
        
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt_messages.append({"role": "system", "content": message.content})
            elif isinstance(message, HumanMessage):
                prompt_messages.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                prompt_messages.append({"role": "assistant", "content": message.content})
        
        return prompt_messages
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate a response using GitHub Copilot API"""
        try:
            prompt_messages = await self._convert_messages_to_prompt(messages)
            
            payload = {
                "model": self.model,
                "messages": prompt_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": self.streaming,
            }
            
            if stop:
                payload["stop"] = stop
            
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "BuddyAgents/1.0",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=30  # 30 second timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"GitHub Copilot API error: {response.status} - {error_text}")
                        raise ValueError(f"API call failed with status {response.status}")
                    
                    # Handle streaming if enabled
                    if self.streaming:
                        # Placeholder for streaming implementation
                        # Will need to implement stream handling logic
                        pass
                    else:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        if run_manager:
                            run_manager.on_llm_new_token(content)
                        
                        generation = ChatGeneration(message=AIMessage(content=content))
                        return LLMResult(generations=[[generation]])
                        
        except Exception as e:
            logger.error(f"Error generating response with GitHub Copilot: {e}")
            raise

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Synchronous wrapper for async generation (required by BaseChatModel)"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._agenerate(messages, stop, run_manager, **kwargs)
        )
