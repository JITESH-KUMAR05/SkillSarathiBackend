"""
Production WebSocket Handler for BuddyAgents
============================================

Handles real-time communication between client and agents with:
- Audio streaming capabilities (Murf AI integration)
- Video chat support preparation
- Multi-agent conversation management
- Session persistence and context tracking
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.agent_orchestrator import AgentOrchestrator
from app.murf_streaming import murf_client
from app.llm.streaming_llm import StreamingLLMService

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages active WebSocket connections with session tracking"""
    
    def __init__(self):
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [connection_ids]
        
    async def connect(self, websocket: WebSocket, user_id: str) -> str:
        """Connect a new WebSocket and return connection ID"""
        connection_id = str(uuid.uuid4())
        
        await websocket.accept()
        
        # Store connection with metadata
        self.active_connections[connection_id] = {
            "websocket": websocket,
            "user_id": user_id,
            "connected_at": datetime.now().isoformat(),
            "current_agent": "mitra",  # Default agent
            "context_history": [],
            "audio_session_id": None,
            "video_session_id": None
        }
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(connection_id)
        
        logger.info(f"✅ New WebSocket connection: {connection_id} for user {user_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """Disconnect and cleanup connection"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            user_id = connection["user_id"]
            
            # Remove from user sessions
            if user_id in self.user_sessions:
                self.user_sessions[user_id] = [
                    cid for cid in self.user_sessions[user_id] 
                    if cid != connection_id
                ]
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            del self.active_connections[connection_id]
            logger.info(f"❌ WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            websocket = connection["websocket"]
            
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
    
    async def send_to_user(self, message: str, user_id: str):
        """Send message to all connections of a user"""
        if user_id in self.user_sessions:
            for connection_id in self.user_sessions[user_id]:
                await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        for connection_id in self.active_connections:
            await self.send_personal_message(message, connection_id)
    
    async def send_audio_chunk(self, audio_data: bytes, connection_id: str):
        """Send audio chunk to specific connection"""
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            websocket = connection["websocket"]
            
            if websocket.client_state == WebSocketState.CONNECTED:
                # Send audio as binary message
                await websocket.send_bytes(audio_data)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get connection metadata"""
        return self.active_connections.get(connection_id)
    
    def update_context(self, connection_id: str, context_data: Dict[str, Any]):
        """Update connection context"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].update(context_data)

# Global connection manager
manager = ConnectionManager()

class WebSocketHandler:
    """Handles WebSocket events and message routing"""
    
    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.streaming_llm = StreamingLLMService()
        
    async def handle_connection(self, websocket: WebSocket, user_id: str):
        """Handle new WebSocket connection"""
        connection_id = await manager.connect(websocket, user_id)
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "connection_established",
                "connection_id": connection_id,
                "message": "🙏 Welcome to BuddyAgents! Your AI companions are ready.",
                "available_agents": ["mitra", "guru", "parikshak"],
                "features": ["text_chat", "voice_streaming", "agent_switching"]
            }
            
            await manager.send_personal_message(
                json.dumps(welcome_msg), 
                connection_id
            )
            
            # Handle incoming messages
            async for message in websocket.iter_text():
                await self.process_message(message, connection_id)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket {connection_id} disconnected")
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
        finally:
            manager.disconnect(connection_id)
    
    async def process_message(self, message: str, connection_id: str):
        """Process incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            connection_info = manager.get_connection_info(connection_id)
            if not connection_info:
                return
            
            user_id = connection_info["user_id"]
            
            # Route message based on type
            if message_type == "chat_message":
                await self.handle_chat_message(data, connection_id, user_id)
            
            elif message_type == "voice_message":
                await self.handle_voice_message(data, connection_id, user_id)
            
            elif message_type == "agent_switch":
                await self.handle_agent_switch(data, connection_id)
            
            elif message_type == "start_voice_streaming":
                await self.handle_start_voice_streaming(data, connection_id, user_id)
            
            elif message_type == "stop_voice_streaming":
                await self.handle_stop_voice_streaming(connection_id)
            
            elif message_type == "video_call_request":
                await self.handle_video_call_request(data, connection_id, user_id)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON message from {connection_id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def handle_chat_message(self, data: Dict[str, Any], connection_id: str, user_id: str):
        """Handle text chat message"""
        try:
            user_message = data.get("message", "")
            agent_type = data.get("agent", "mitra")
            context_id = data.get("context_id")
            
            if not user_message:
                return
            
            # Update connection context
            manager.update_context(connection_id, {
                "current_agent": agent_type,
                "last_message_at": datetime.now().isoformat()
            })
            
            # Send typing indicator
            typing_msg = {
                "type": "agent_typing",
                "agent": agent_type,
                "message": f"{agent_type.title()} is thinking..."
            }
            await manager.send_personal_message(json.dumps(typing_msg), connection_id)
            
            # Get response from agent
            response = await self.orchestrator.route_message(
                message=user_message,
                agent_type=agent_type,
                user_id=user_id
            )
            
            # Send text response
            response_msg = {
                "type": "agent_response",
                "agent": agent_type,
                "message": response,
                "timestamp": datetime.now().isoformat()
            }
            
            await manager.send_personal_message(json.dumps(response_msg), connection_id)
            
            # Also send audio if voice streaming is enabled
            connection_info = manager.get_connection_info(connection_id)
            if connection_info and connection_info.get("audio_session_id"):
                await self.stream_response_audio(response, agent_type, connection_id, user_id)
        
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    async def handle_voice_message(self, data: Dict[str, Any], connection_id: str, user_id: str):
        """Handle voice message (speech-to-text + response)"""
        try:
            # This would integrate with speech-to-text service
            # For now, treat as text message
            text_message = data.get("transcript", "")
            
            if text_message:
                # Process as chat message
                await self.handle_chat_message({
                    "message": text_message,
                    "agent": data.get("agent", "mitra")
                }, connection_id, user_id)
        
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
    
    async def handle_agent_switch(self, data: Dict[str, Any], connection_id: str):
        """Handle agent switching"""
        try:
            new_agent = data.get("agent", "mitra")
            
            # Update connection context
            manager.update_context(connection_id, {
                "current_agent": new_agent,
                "agent_switched_at": datetime.now().isoformat()
            })
            
            # Send confirmation
            switch_msg = {
                "type": "agent_switched",
                "agent": new_agent,
                "message": f"Switched to {new_agent.title()}. How can I help you?"
            }
            
            await manager.send_personal_message(json.dumps(switch_msg), connection_id)
        
        except Exception as e:
            logger.error(f"Error switching agent: {e}")
    
    async def handle_start_voice_streaming(self, data: Dict[str, Any], connection_id: str, user_id: str):
        """Start voice streaming session"""
        try:
            agent_type = data.get("agent", "mitra")
            
            # Generate audio session ID
            audio_session_id = f"audio_{connection_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Update connection with audio session
            manager.update_context(connection_id, {
                "audio_session_id": audio_session_id,
                "voice_streaming_enabled": True,
                "current_agent": agent_type
            })
            
            # Send confirmation
            stream_msg = {
                "type": "voice_streaming_started",
                "audio_session_id": audio_session_id,
                "agent": agent_type,
                "message": f"🎵 Voice streaming started with {agent_type.title()}"
            }
            
            await manager.send_personal_message(json.dumps(stream_msg), connection_id)
        
        except Exception as e:
            logger.error(f"Error starting voice streaming: {e}")
    
    async def handle_stop_voice_streaming(self, connection_id: str):
        """Stop voice streaming session"""
        try:
            # Update connection
            manager.update_context(connection_id, {
                "audio_session_id": None,
                "voice_streaming_enabled": False
            })
            
            # Send confirmation
            stop_msg = {
                "type": "voice_streaming_stopped",
                "message": "🔇 Voice streaming stopped"
            }
            
            await manager.send_personal_message(json.dumps(stop_msg), connection_id)
        
        except Exception as e:
            logger.error(f"Error stopping voice streaming: {e}")
    
    async def handle_video_call_request(self, data: Dict[str, Any], connection_id: str, user_id: str):
        """Handle video call request (for Parikshak agent)"""
        try:
            agent_type = data.get("agent", "parikshak")
            
            if agent_type != "parikshak":
                error_msg = {
                    "type": "error",
                    "message": "Video calls are only available with Parikshak (Interview Agent)"
                }
                await manager.send_personal_message(json.dumps(error_msg), connection_id)
                return
            
            # Generate video session ID
            video_session_id = f"video_{connection_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Update connection
            manager.update_context(connection_id, {
                "video_session_id": video_session_id,
                "video_call_active": True,
                "current_agent": agent_type
            })
            
            # Send video call details
            video_msg = {
                "type": "video_call_started",
                "video_session_id": video_session_id,
                "agent": agent_type,
                "webrtc_config": {
                    "ice_servers": [
                        {"urls": "stun:stun.l.google.com:19302"}
                    ]
                },
                "message": "📹 Video interview session started with Parikshak"
            }
            
            await manager.send_personal_message(json.dumps(video_msg), connection_id)
        
        except Exception as e:
            logger.error(f"Error handling video call request: {e}")
    
    async def stream_response_audio(self, text: str, agent_type: str, connection_id: str, user_id: str):
        """Stream audio response using Murf AI"""
        try:
            connection_info = manager.get_connection_info(connection_id)
            if not connection_info or not connection_info.get("voice_streaming_enabled"):
                return
            
            audio_session_id = connection_info.get("audio_session_id")
            
            # Send audio start notification
            audio_start_msg = {
                "type": "audio_stream_start",
                "agent": agent_type,
                "audio_session_id": audio_session_id
            }
            await manager.send_personal_message(json.dumps(audio_start_msg), connection_id)
            
            # Stream audio chunks
            async for audio_chunk in murf_client.stream_text_to_speech(
                text=text,
                agent_type=agent_type,
                user_id=user_id
            ):
                await manager.send_audio_chunk(audio_chunk, connection_id)
            
            # Send audio end notification
            audio_end_msg = {
                "type": "audio_stream_end",
                "agent": agent_type,
                "audio_session_id": audio_session_id
            }
            await manager.send_personal_message(json.dumps(audio_end_msg), connection_id)
        
        except Exception as e:
            logger.error(f"Error streaming audio response: {e}")

# Global handler instance
websocket_handler = WebSocketHandler()
