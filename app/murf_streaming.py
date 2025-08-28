"""
Production Murf AI WebSocket Streaming Client
===========================================

Implements WebSocket-based streaming for ultra-low latency TTS with:
- Persistent session management
- Voice switching capabilities  
- Graceful error handling and rate limiting
- Optimized audio buffering
"""

import asyncio
import json
import base64
import logging
import websockets
import uuid
from typing import Optional, Dict, Any, AsyncGenerator, Union
import aiohttp
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class MurfWebSocketClient:
    """Production-grade Murf AI WebSocket client for real-time TTS streaming"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MURF_API_KEY")
        self.ws_url = "wss://api.murf.ai/v1/stream"
        self.session_id = str(uuid.uuid4())
        self.websocket = None
        self.context_sessions = {}  # Track user sessions
        
        # Voice configurations for Indian agents - UPDATED with real Murf voice IDs
        self.agent_voices = {
            "mitra": "hi-IN-shweta",     # Hindi female voice - warm, caring
            "guru": "en-IN-eashwar",     # English-India male voice - professional
            "parikshak": "en-IN-isha"    # English-India female voice - clear evaluator
        }
        
        self.current_voice = "hi-IN-shweta"  # Default to Mitra's voice
        self.audio_format = "wav"
        self.sample_rate = 44100
        
    async def connect(self):
        """Establish persistent WebSocket connection with authentication"""
        try:
            if not self.api_key:
                logger.warning("❌ No Murf API key provided - using fallback mode")
                return False
                
            headers = {
                "api-key": self.api_key,  # Murf uses 'api-key' header
                "User-Agent": "BuddyAgents/1.0"
            }
            
            # Try WebSocket connection with proper headers parameter
            try:
                self.websocket = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    ping_interval=30,
                    ping_timeout=10
                )
            except TypeError:
                # Fallback for older websockets versions
                self.websocket = await websockets.connect(
                    self.ws_url,
                    ping_interval=30,
                    ping_timeout=10
                )
            
            # Send initial session setup if connected
            if self.websocket:
                init_message = {
                    "type": "session_init",
                    "session_id": self.session_id,
                    "audio_config": {
                        "format": self.audio_format,
                        "sample_rate": self.sample_rate,
                        "channels": 1
                    }
                }
                
                await self.websocket.send(json.dumps(init_message))
                logger.info(f"✅ Murf WebSocket connected: {self.session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Murf WebSocket: {e}")
            logger.info("🔄 Falling back to HTTP API for TTS")
            return False
    
    async def disconnect(self):
        """Gracefully close WebSocket connection"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("Murf WebSocket disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
    
    async def switch_voice(self, agent_type: str) -> bool:
        """Switch voice based on agent type"""
        try:
            new_voice = self.agent_voices.get(agent_type, "hi-IN-shweta")
            if new_voice != self.current_voice:
                self.current_voice = new_voice
                
                # Send voice change command
                voice_change = {
                    "type": "voice_change",
                    "voice_id": new_voice,
                    "session_id": self.session_id
                }
                
                if self.websocket:
                    await self.websocket.send(json.dumps(voice_change))
                    logger.info(f"🎵 Voice switched to {new_voice} for {agent_type}")
                    return True
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch voice: {e}")
            return False
    
    async def stream_text_to_speech(
        self, 
        text: str, 
        user_id: str,
        agent_type: str = "mitra",
        context_id: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream text to speech with context preservation
        
        Yields audio chunks as they're generated for real-time playback
        """
        try:
            # Ensure connection
            if not self.websocket or self.websocket.closed:
                connected = await self.connect()
                if not connected:
                    raise Exception("Failed to connect to Murf WebSocket")
            
            # Switch voice if needed
            await self.switch_voice(agent_type)
            
            # Create or reuse context session
            if not context_id:
                context_id = f"{user_id}_{agent_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Prepare streaming request
            tts_request = {
                "type": "tts_stream",
                "text": text,
                "voice_id": self.current_voice,
                "context_id": context_id,
                "user_id": user_id,
                "agent_type": agent_type,
                "audio_config": {
                    "format": self.audio_format,
                    "sample_rate": self.sample_rate,
                    "streaming": True,
                    "chunk_size": 1024
                },
                "voice_settings": {
                    "speed": 1.0,
                    "pitch": 0,
                    "emphasis": "moderate"
                }
            }
            
            # Send TTS request
            if self.websocket:
                await self.websocket.send(json.dumps(tts_request))
                
                # Stream audio chunks
                async for message in self.websocket:
                    try:
                        if isinstance(message, str):
                            # JSON message (status/control)
                            data = json.loads(message)
                            
                            if data.get("type") == "audio_chunk":
                                # Audio data in base64
                                audio_data = base64.b64decode(data["audio"])
                                yield audio_data
                                
                            elif data.get("type") == "stream_complete":
                                logger.info("🎵 TTS stream completed")
                                break
                                
                            elif data.get("type") == "error":
                                logger.error(f"Murf TTS error: {data.get('message')}")
                                break
                                
                        elif isinstance(message, bytes):
                            # Direct binary audio data
                            yield message
                        
                    except json.JSONDecodeError:
                        # Direct binary audio (non-JSON)
                        if isinstance(message, bytes):
                            yield message
                        elif isinstance(message, str):
                            yield message.encode('utf-8')
                    except Exception as e:
                        logger.error(f"Error processing audio chunk: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"TTS streaming error: {e}")
            # Fallback to HTTP API if WebSocket fails
            async for chunk in self._fallback_http_tts(text, agent_type):
                yield chunk
    
    async def _fallback_http_tts(self, text: str, agent_type: str) -> AsyncGenerator[bytes, None]:
        """Fallback to HTTP API when WebSocket fails"""
        try:
            voice_id = self.agent_voices.get(agent_type, "hi-IN-shweta")
            
            url = "https://api.murf.ai/v1/speech/generate"
            headers = {
                "api-key": self.api_key,  # Murf uses 'api-key' header
                "Content-Type": "application/json"
            }
            
            payload = {
                "voiceId": voice_id,
                "text": text,
                "format": "WAV",
                "sampleRate": self.sample_rate
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        # Stream audio in chunks
                        async for chunk in response.content.iter_chunked(1024):
                            if chunk:  # Ensure non-empty chunks
                                yield chunk
                    else:
                        logger.error(f"HTTP TTS fallback failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Fallback TTS error: {e}")
    
    async def get_available_voices(self) -> Dict[str, Any]:
        """Get available voices from Murf API"""
        try:
            if not self.api_key:
                return {"voices": []}
                
            url = "https://api.murf.ai/v1/speech/voices"
            headers = {"api-key": self.api_key}  # Murf uses 'api-key' header
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"voices": []}
                        
        except Exception as e:
            logger.error(f"Failed to fetch voices: {e}")
            return {"voices": []}

# Global instance for application use
murf_client = MurfWebSocketClient()
