"""
Simple WebSocket Handler for Skillsarathi AI with minimal latency
"""

import asyncio
import json
import logging
from typing import Dict, Any
from datetime import datetime
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

class WebSocketManager:
    """WebSocket manager with streaming support for minimal latency"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new WebSocket client"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.user_contexts[client_id] = {
                "connected_at": datetime.now(),
                "message_count": 0,
                "name": "User"
            }
            
            # Send welcome message
            welcome_msg = {
                "type": "system",
                "message": "Welcome to Skillsarathi AI! I'm ready to help you with minimal latency.",
                "timestamp": datetime.now().isoformat(),
                "client_id": client_id
            }
            
            await self.send_message(welcome_msg, client_id)
            logger.info(f"Client {client_id} connected")
            
        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
            self.disconnect(client_id)
    
    def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.user_contexts:
            del self.user_contexts[client_id]
        logger.info(f"Client {client_id} disconnected")
    
    async def send_message(self, message: Dict[str, Any], client_id: str):
        """Send message to specific client"""
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_text(json.dumps(message))
                else:
                    self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Send message error for {client_id}: {e}")
            self.disconnect(client_id)
    
    async def stream_response(self, text: str, client_id: str):
        """Stream response word by word for minimal latency"""
        try:
            if client_id not in self.active_connections:
                return
                
            # Send start indicator
            await self.send_message({
                "type": "stream_start",
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
            # Stream words with minimal delay for maximum responsiveness
            words = text.split()
            for i, word in enumerate(words):
                if client_id not in self.active_connections:
                    break
                    
                await self.send_message({
                    "type": "token",
                    "token": word + " ",
                    "is_final": i == len(words) - 1,
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                
                # Ultra-minimal delay for streaming effect (adjustable for latency)
                await asyncio.sleep(0.01)
            
            # Send completion
            await self.send_message({
                "type": "stream_end",
                "full_text": text,
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
        except Exception as e:
            logger.error(f"Streaming error for {client_id}: {e}")
    
    async def handle_message(self, data: Dict[str, Any], client_id: str):
        """Handle incoming message from client"""
        try:
            message = data.get("message", "")
            if not message.strip():
                return
            
            # Update activity
            if client_id in self.user_contexts:
                self.user_contexts[client_id]["message_count"] += 1
            
            # Send typing indicator
            await self.send_message({
                "type": "typing",
                "timestamp": datetime.now().isoformat()
            }, client_id)
            
            # Simple response generation for minimal latency
            try:
                # Check if we have GitHub token for real AI
                from app.core.config import settings
                
                if settings.GITHUB_TOKEN:
                    # Try GitHub LLM
                    try:
                        import aiohttp
                        
                        headers = {
                            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                        }
                        
                        payload = {
                            "model": "gpt-4o",
                            "messages": [{"role": "user", "content": message}],
                            "temperature": 0.7,
                            "max_tokens": 150  # Keep responses short for low latency
                        }
                        
                        timeout = aiohttp.ClientTimeout(total=5)  # 5 second timeout for low latency
                        
                        async with aiohttp.ClientSession(timeout=timeout) as session:
                            async with session.post(
                                "https://models.inference.ai.azure.com/chat/completions",
                                headers=headers,
                                json=payload
                            ) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                                    
                                    if response_text:
                                        await self.stream_response(response_text.strip(), client_id)
                                        return
                    except Exception as e:
                        logger.warning(f"GitHub LLM error: {e}")
                
                # Fallback to simple responses for testing
                simple_responses = [
                    f"I understand you said: '{message}'. I'm here to help!",
                    f"Thanks for your message: '{message}'. How can I assist you further?",
                    f"That's interesting! You mentioned: '{message}'. Tell me more.",
                    f"I see you're talking about: '{message}'. I'm ready to help with minimal latency!"
                ]
                
                import random
                response_text = random.choice(simple_responses)
                await self.stream_response(response_text, client_id)
                
            except Exception as e:
                logger.error(f"LLM error: {e}")
                await self.stream_response(
                    "I'm having trouble processing your request. Please try again.", 
                    client_id
                )
            
        except Exception as e:
            logger.error(f"Message handling error for {client_id}: {e}")

# Global WebSocket manager
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    client_id = str(uuid.uuid4())
    
    try:
        await websocket_manager.connect(websocket, client_id)
        
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                await websocket_manager.handle_message(message_data, client_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
    
    finally:
        websocket_manager.disconnect(client_id)
