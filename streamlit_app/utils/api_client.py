"""
BuddyAgents API Client
=====================

HTTP client for communicating with the BuddyAgents backend API.
"""

import asyncio
import json
import aiohttp
import requests
import streamlit as st
from typing import Dict, List, Optional, Any, AsyncGenerator
import websockets
from .config import config

class BuddyAgentsAPI:
    """Synchronous API client for BuddyAgents backend"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or config.BACKEND_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": f"BuddyAgents-Frontend/{config.APP_VERSION}"
        })
    
    def health_check(self) -> Dict[str, Any]:
        """Check backend health status"""
        try:
            response = self.session.get(f"{self.base_url}{config.HEALTH_ENDPOINT}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Backend health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get available agents and their configurations"""
        try:
            response = self.session.get(f"{self.base_url}{config.AGENTS_ENDPOINT}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch agents: {e}")
            return []
    
    def send_chat_message(self, message: str, agent: str, user_id: str = "streamlit_user") -> Dict[str, Any]:
        """Send chat message to agent"""
        try:
            data = {
                "message": message,
                "agent_type": agent,
                "candidate_id": user_id,  # Backend expects candidate_id
                "voice_enabled": False
            }
            
            response = self.session.post(
                f"{self.base_url}{config.CHAT_ENDPOINT}",
                json=data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                response.raise_for_status()
                
        except Exception as e:
            return {
                "response": f"Sorry, I'm having trouble connecting right now. Error: {str(e)}",
                "agent_type": agent,
                "error": True
            }
    
    def generate_voice(self, text: str, agent: str) -> Optional[bytes]:
        """Generate voice audio for text and return actual audio data"""
        try:
            # Use JSON data for the voice endpoint
            data = {
                "text": text,
                "agent": agent  # Backend expects 'agent' not 'agent_type'
            }
            
            # Debug: Log the request
            st.info(f"🔄 Requesting voice for '{text[:50]}...' with agent '{agent}'")
            
            response = self.session.post(
                f"{self.base_url}{config.VOICE_ENDPOINT}",
                json=data  # Use JSON data to match VoiceRequest model
            )
            
            # Debug: Log response details
            st.info(f"📡 Response: Status={response.status_code}, Content-Type={response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                # Check if we got audio data or JSON response
                content_type = response.headers.get('content-type', '')
                
                if 'audio' in content_type:
                    # We got actual audio data
                    audio_data = response.content
                    agent_name = response.headers.get('X-Voice-Agent', agent)
                    audio_size = response.headers.get('X-Voice-Size', len(audio_data))
                    
                    # Debug: Validate audio data
                    if not audio_data or len(audio_data) == 0:
                        st.error("❌ Received empty audio data from backend")
                        return None
                    
                    # Debug: Check audio data format
                    audio_start = audio_data[:16] if len(audio_data) >= 16 else audio_data
                    st.info(f"🔊 Audio data starts with: {audio_start}")
                    
                    st.success(f"🎵 Voice generated for {agent_name} ({audio_size} bytes)")
                    return audio_data
                else:
                    # We got JSON response (fallback)
                    try:
                        response_json = response.json()
                        if response_json.get("status") == "success":
                            st.success(f"🎵 Voice generated: {response_json.get('message', 'Success')}")
                            return b"placeholder_audio"
                        else:
                            st.warning(f"Voice generation failed: {response_json}")
                            return None
                    except json.JSONDecodeError:
                        st.error("❌ Received invalid JSON response")
                        return None
            else:
                st.warning(f"Voice generation failed: HTTP {response.status_code}")
                st.error(f"Response content: {response.text[:200]}...")
                return None
                
        except Exception as e:
            st.error(f"Voice generation error: {e}")
            import traceback
            st.error(f"Full error: {traceback.format_exc()}")
            return None

class AsyncBuddyAgentsAPI:
    """Asynchronous API client for real-time features"""
    
    def __init__(self, base_url: Optional[str] = None, ws_url: Optional[str] = None):
        self.base_url = base_url or config.BACKEND_URL
        self.ws_url = ws_url or config.WEBSOCKET_URL
    
    async def connect_websocket(self, user_id: str) -> websockets.WebSocketServerProtocol:
        """Connect to WebSocket for real-time communication"""
        try:
            uri = f"{self.ws_url}/ws/{user_id}"
            websocket = await websockets.connect(uri)
            return websocket
        except Exception as e:
            st.error(f"WebSocket connection failed: {e}")
            raise
    
    async def send_websocket_message(self, websocket, message: Dict[str, Any]):
        """Send message via WebSocket"""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            st.error(f"WebSocket send failed: {e}")
            raise
    
    async def receive_websocket_message(self, websocket) -> Dict[str, Any]:
        """Receive message from WebSocket"""
        try:
            message = await websocket.recv()
            return json.loads(message)
        except Exception as e:
            st.error(f"WebSocket receive failed: {e}")
            raise

# Global API client instances
api_client = BuddyAgentsAPI()
async_api_client = AsyncBuddyAgentsAPI()

# Helper functions for Streamlit integration
@st.cache_data(ttl=60)
def get_backend_status():
    """Cached backend health check"""
    return api_client.health_check()

@st.cache_data(ttl=300) 
def get_available_agents():
    """Cached agents list"""
    return api_client.get_agents()

def send_message_with_loading(message: str, agent: str, user_id: str = "streamlit_user"):
    """Send message with loading indicator"""
    with st.spinner(f"🤔 {config.AGENTS[agent]['name']} is thinking..."):
        return api_client.send_chat_message(message, agent, user_id)
