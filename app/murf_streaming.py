"""
Production Murf AI Integration - FIXED VERSION
=============================================
"""

import asyncio
import json
import base64
import time
import logging
import uuid
import os
from typing import Optional, AsyncGenerator, Dict, Any
import aiohttp
import websockets

logger = logging.getLogger(__name__)

class MurfAIService:
    """Production Murf AI service with FIXED WebSocket authentication"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MURF_API_KEY")
        
        # CORRECTED endpoints
        self.base_url = "https://api.murf.ai/v1"
        self.voices_url = f"{self.base_url}/speech/voices"
        self.generate_url = f"{self.base_url}/speech/generate"
        self.websocket_url = "wss://api.murf.ai/v1/speech/stream-input"
        
        # Agent voice mappings
        self.agent_voices = {
            "mitra": "hi-IN-shweta",
            "guru": "en-IN-isha", 
            "parikshak": "en-IN-isha"
        }
        
    async def generate_speech_http(self, text: str, agent_type: str = "mitra") -> Optional[bytes]:
        """Generate speech using HTTP API (working method)"""
        try:
            voice_id = self.agent_voices.get(agent_type, "hi-IN-shweta")
            
            headers = {
                "api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "voiceId": voice_id,
                "text": text,
                "format": "WAV",
                "sampleRate": "44K"
            }
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.generate_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        audio_url = data.get("audioFile")
                        
                        if audio_url:
                            async with session.get(audio_url) as audio_response:
                                if audio_response.status == 200:
                                    audio_data = await audio_response.read()
                                    logger.info(f"✅ Speech generated: {len(audio_data)} bytes")
                                    return audio_data
            return None
            
        except Exception as e:
            logger.error(f"❌ HTTP TTS failed: {e}")
            return None
    
    async def stream_speech_websocket(self, text: str, agent_type: str = "mitra") -> AsyncGenerator[bytes, None]:
        """Stream speech with FIXED WebSocket authentication"""
        try:
            # FIXED: Try multiple authentication methods
            auth_methods = [
                # Method 1: Query parameter 
                f"{self.websocket_url}?api_key={self.api_key}",
                # Method 2: Original URL with headers
                self.websocket_url
            ]
            
            websocket = None
            
            # Try each authentication method
            for i, url in enumerate(auth_methods):
                try:
                    if i == 0:  # Query param method
                        websocket = await websockets.connect(url, ping_interval=30)
                    else:  # Header method
                        headers = {"api-key": self.api_key} if self.api_key else {}
                        websocket = await websockets.connect(url, additional_headers=headers, ping_interval=30)
                    
                    logger.info(f"✅ WebSocket connected using method {i+1}")
                    break
                    
                except Exception as e:
                    logger.warning(f"❌ Auth method {i+1} failed: {e}")
                    continue
            
            if not websocket:
                logger.warning("🔄 WebSocket failed, using HTTP fallback")
                audio_data = await self.generate_speech_http(text, agent_type)
                if audio_data:
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        yield audio_data[i:i + chunk_size]
                        await asyncio.sleep(0.01)
                return
            
            # Send voice config and text
            voice_id = self.agent_voices.get(agent_type, "hi-IN-shweta")
            
            voice_config = {"voiceId": voice_id, "format": "WAV", "sampleRate": "44K"}
            await websocket.send(json.dumps(voice_config))
            
            text_message = {"text": text, "end": True}
            await websocket.send(json.dumps(text_message))
            
            # Receive audio chunks
            audio_received = False
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        data = json.loads(message)
                        if "audio" in data:
                            audio_chunk = base64.b64decode(data["audio"])
                            audio_received = True
                            yield audio_chunk
                        if data.get("final") or data.get("complete"):
                            break
                    except json.JSONDecodeError:
                        continue
                elif isinstance(message, bytes):
                    audio_received = True
                    yield message
            
            await websocket.close()
            
            # HTTP fallback if no WebSocket audio
            if not audio_received:
                audio_data = await self.generate_speech_http(text, agent_type)
                if audio_data:
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        yield audio_data[i:i + chunk_size]
                        await asyncio.sleep(0.01)
                        
        except Exception as e:
            logger.error(f"❌ WebSocket streaming failed: {e}")
            # Final HTTP fallback
            audio_data = await self.generate_speech_http(text, agent_type)
            if audio_data:
                chunk_size = 4096
                for i in range(0, len(audio_data), chunk_size):
                    yield audio_data[i:i + chunk_size]
                    await asyncio.sleep(0.01)
    
    async def validate_setup(self) -> Dict[str, Any]:
        """Validate setup"""
        results = {
            "api_key_present": bool(self.api_key),
            "auth_token_valid": False,
            "voices_accessible": False, 
            "test_synthesis": False,
            "agent_voices": {}
        }
        
        if not self.api_key:
            return results
        
        # Test HTTP generation to validate auth
        for agent, voice_id in self.agent_voices.items():
            test_text = f"Hello, I am {agent}, your AI assistant."
            audio_data = await self.generate_speech_http(test_text, agent)
            working = bool(audio_data and len(audio_data) > 1000)
            results["agent_voices"][agent] = {"voice_id": voice_id, "working": working}
            if working:
                results["test_synthesis"] = True
                results["auth_token_valid"] = True
        
        return results

# Global instances
murf_service = MurfAIService()

# Backward compatibility
async def stream_text_to_speech(text: str, agent_type: str = "mitra", user_id: str = "default"):
    async for chunk in murf_service.stream_speech_websocket(text, agent_type):
        yield chunk

class MurfWebSocketClient:
    def __init__(self, api_key: Optional[str] = None):
        self.service = MurfAIService(api_key)
        self.agent_voices = self.service.agent_voices
    
    async def stream_text_to_speech(self, text: str, user_id: str, agent_type: str = "mitra", context_id: Optional[str] = None):
        async for chunk in self.service.stream_speech_websocket(text, agent_type):
            yield chunk

murf_client = MurfWebSocketClient()
