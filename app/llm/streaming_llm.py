"""
Streaming LLM implementation that supports WebSocket streaming for minimal latency
"""

import asyncio
import logging
from typing import Dict, Any, List, AsyncIterator, Optional, Callable
from langchain.chat_models.base import BaseChatModel
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.callbacks.manager import CallbackManagerForLLMRun

logger = logging.getLogger(__name__)

class WebSocketStreamingCallbackHandler(BaseCallbackHandler):
    """Callback handler for streaming LLM responses via WebSocket"""
    
    def __init__(self, websocket_sender: Callable[[str], None]):
        """
        Initialize the callback handler
        
        Args:
            websocket_sender: Callable that sends a message via WebSocket
        """
        self.websocket_sender = websocket_sender
        self.full_response = []
        self.streaming = True
        
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when LLM produces a new token"""
        if not token or not self.streaming:
            return
            
        self.full_response.append(token)
        
        # Send token via WebSocket
        await self.websocket_sender({
            "type": "token",
            "content": token,
            "is_final": False
        })
    
    async def on_llm_end(self, response: Any, **kwargs) -> None:
        """Called when LLM generation ends"""
        # Send final message indicating stream is complete
        await self.websocket_sender({
            "type": "token",
            "content": "",
            "is_final": True,
            "full_response": "".join(self.full_response)
        })
        self.streaming = False
        
    async def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called when LLM encounters an error"""
        await self.websocket_sender({
            "type": "error",
            "content": f"LLM Error: {str(error)}"
        })
        self.streaming = False

class StreamingLLMWrapper:
    """Wrapper that adds streaming capabilities to any LLM"""
    
    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        
    async def stream_chat(
        self,
        messages: List[BaseMessage],
        websocket_sender: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Stream LLM responses via WebSocket for minimal latency
        
        Args:
            messages: List of messages in the conversation
            websocket_sender: Function to send messages via WebSocket
            
        Returns:
            The complete response as a string
        """
        try:
            # Create callback handler for streaming
            streaming_handler = WebSocketStreamingCallbackHandler(websocket_sender)
            
            # Stream response tokens
            response = await self.llm.agenerate(
                [messages],
                callbacks=[streaming_handler]
            )
            
            # Return full response
            if response.generations and response.generations[0]:
                return response.generations[0][0].text
            return ""
            
        except Exception as e:
            logger.error(f"Error in streaming LLM: {e}")
            await websocket_sender({
                "type": "error",
                "content": f"Error generating response: {str(e)}"
            })
            return ""
