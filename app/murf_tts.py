"""
Murf AI WebSocket Integration for Real-time TTS Streaming
"""

import asyncio
import websockets
import json
import logging
import base64
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class MurfWebSocketTTS:
    """Real-time TTS using Murf AI WebSocket streaming"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws_url = "wss://api.murf.ai/v1/speech/stream"
        self.websocket = None
        self.is_connected = False
        self.context_id = None
        
    async def connect(self):
        """Connect to Murf AI WebSocket"""
        try:
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            self.websocket = await websockets.connect(
                self.ws_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_connected = True
            logger.info("Connected to Murf AI WebSocket")
            
            # Start context session
            await self._start_context()
            
        except Exception as e:
            logger.error(f"Failed to connect to Murf AI: {e}")
            self.is_connected = False
            raise
    
    async def _start_context(self):
        """Start a new TTS context session"""
        try:
            context_message = {
                "type": "context_start",
                "voice_id": "en-US-sarah",  # Valid Murf voice ID
                "format": "mp3",
                "sample_rate": 24000,
                "bit_rate": 128000,
                "settings": {
                    "speed": 1.0,
                    "pitch": 0,
                    "volume": 1.0,
                    "emphasis": "moderate"
                }
            }
            
            await self.websocket.send(json.dumps(context_message))
            
            # Wait for context confirmation
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "context_started":
                self.context_id = data.get("context_id")
                logger.info(f"TTS context started: {self.context_id}")
            else:
                logger.error(f"Failed to start context: {data}")
                
        except Exception as e:
            logger.error(f"Context start error: {e}")
    
    async def synthesize_stream(self, text: str, callback: Callable[[bytes], None]):
        """Stream TTS audio chunks in real-time"""
        if not self.is_connected or not self.websocket:
            await self.connect()
        
        try:
            # Send text for synthesis
            synthesis_message = {
                "type": "synthesize",
                "context_id": self.context_id,
                "text": text,
                "chunk_size": 1024  # Small chunks for low latency
            }
            
            await self.websocket.send(json.dumps(synthesis_message))
            
            # Receive audio chunks
            while True:
                response = await self.websocket.recv()
                data = json.loads(response)
                
                if data.get("type") == "audio_chunk":
                    # Decode base64 audio data
                    audio_data = base64.b64decode(data.get("audio", ""))
                    if audio_data:
                        callback(audio_data)
                
                elif data.get("type") == "synthesis_complete":
                    logger.info("TTS synthesis completed")
                    break
                
                elif data.get("type") == "error":
                    logger.error(f"TTS error: {data.get('message')}")
                    break
                    
        except Exception as e:
            logger.error(f"TTS streaming error: {e}")
    
    async def disconnect(self):
        """Disconnect from Murf AI WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from Murf AI")

class MurfHTTPTTS:
    """Fallback HTTP TTS when WebSocket is not available"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.murf.ai/v1"
    
    async def synthesize(self, text: str) -> bytes:
        """Generate TTS audio using HTTP API"""
        import aiohttp
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "voice_id": "en-US-sarah",
            "text": text,
            "format": "mp3",
            "sample_rate": 24000,
            "settings": {
                "speed": 1.0,
                "pitch": 0,
                "volume": 1.0
            }
        }
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/speech/generate",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        error_text = await response.text()
                        logger.error(f"Murf HTTP TTS error: {response.status} - {error_text}")
                        return b""
        except Exception as e:
            logger.error(f"HTTP TTS error: {e}")
            return b""

# Global TTS instance
murf_tts = None

def get_murf_tts(api_key: str) -> MurfWebSocketTTS:
    """Get or create Murf TTS instance"""
    global murf_tts
    if murf_tts is None:
        murf_tts = MurfWebSocketTTS(api_key)
    return murf_tts
