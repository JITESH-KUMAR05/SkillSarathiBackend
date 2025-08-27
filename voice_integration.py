"""
Voice Integration Module for Multi-Agent Platform
Integrates Murf AI TTS with Streamlit interface
"""

import os
import asyncio
import requests
import base64
import tempfile
import logging
import streamlit as st
from typing import Optional, Dict, Any
from app.murf_streaming import MurfStreamingClient

logger = logging.getLogger(__name__)

class VoiceManager:
    """Manages voice synthesis and playback for agents"""
    
    def __init__(self):
        self.murf_api_key = os.getenv("MURF_API_KEY", "your_murf_api_key_here")
        self.murf_client = MurfStreamingClient(self.murf_api_key)
        self.voice_enabled = True
        
        # Agent-specific voice settings
        self.agent_voices = {
            "mitra": {
                "voice_id": "en-IN-kavya",  # Warm female voice
                "speed": 0.9,
                "volume": 0.8,
                "style": "friendly"
            },
            "guru": {
                "voice_id": "en-IN-madhur",  # Professional male voice
                "speed": 1.0,
                "volume": 0.85,
                "style": "authoritative"
            },
            "parikshak": {
                "voice_id": "en-IN-dhwani",  # Clear professional voice
                "speed": 1.1,
                "volume": 0.9,
                "style": "professional"
            }
        }
    
    def toggle_voice(self, enabled: bool):
        """Toggle voice synthesis on/off"""
        self.voice_enabled = enabled
        st.session_state.voice_enabled = enabled
    
    async def generate_speech(self, text: str, agent_type: str) -> Optional[str]:
        """Generate speech for agent response"""
        if not self.voice_enabled:
            return None
            
        try:
            voice_config = self.agent_voices.get(agent_type, self.agent_voices["mitra"])
            
            # Generate audio with Murf
            audio_url = await self.murf_client.generate_streaming_audio(
                text=text,
                voice_id=voice_config["voice_id"],
                speed=voice_config["speed"],
                volume=voice_config["volume"]
            )
            
            if audio_url:
                return audio_url
            else:
                # Fallback: Generate placeholder audio
                return self._generate_fallback_audio(text, agent_type)
                
        except Exception as e:
            logger.error(f"Voice generation error: {e}")
            return self._generate_fallback_audio(text, agent_type)
    
    def _generate_fallback_audio(self, text: str, agent_type: str) -> Optional[str]:
        """Generate fallback audio when Murf is unavailable"""
        try:
            # For now, return None - in production, you could use:
            # - Local TTS engines (pyttsx3, espeak)
            # - Browser's Web Speech API
            # - Other cloud TTS services
            logger.warning(f"Fallback audio not implemented for: {text[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Fallback audio error: {e}")
            return None
    
    def render_voice_controls(self):
        """Render voice control UI in Streamlit"""
        with st.sidebar:
            st.subheader("🔊 Voice Controls")
            
            # Voice toggle
            voice_enabled = st.checkbox(
                "Enable Voice Responses", 
                value=st.session_state.get("voice_enabled", True),
                help="Turn on/off voice synthesis for agent responses"
            )
            self.toggle_voice(voice_enabled)
            
            if voice_enabled:
                st.info("🎵 Voice synthesis enabled with Indian accents")
                
                # Voice speed info (read-only for now to avoid session state conflicts)
                st.markdown("**Speech Settings:**")
                st.markdown("- Speed: Normal (1.0x)")
                st.markdown("- Auto-play: Enabled")
                st.markdown("- Accent: Indian English")
                
            else:
                st.info("🔇 Voice synthesis disabled")
    
    def play_audio_in_streamlit(self, audio_url: str, agent_name: str):
        """Play audio in Streamlit interface"""
        if not audio_url:
            return
            
        try:
            # Download audio file
            response = requests.get(audio_url)
            if response.status_code == 200:
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file_path = tmp_file.name
                
                # Display audio player in Streamlit
                with open(tmp_file_path, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format="audio/mp3")
                
                # Auto-play if enabled
                if st.session_state.get("auto_play", True):
                    st.markdown(f"""
                    <script>
                        const audio = document.querySelector('audio');
                        if (audio) audio.play();
                    </script>
                    """, unsafe_allow_html=True)
                
                # Clean up
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            st.error(f"Could not play audio for {agent_name}")

# Global voice manager instance
voice_manager = VoiceManager()

# Streamlit integration helpers
def render_voice_message(text: str, agent_type: str, agent_info: Dict[str, Any]):
    """Render a message with voice synthesis"""
    # Display the text message
    st.markdown(f"""
    <div style="background-color: #f0f8ff; padding: 10px; border-radius: 10px; margin: 5px 0; color: #2c3e50; border-left: 4px solid {agent_info.get('color', '#1f77b4')};">
        <strong style="color: {agent_info.get('color', '#1f77b4')};">{agent_info['avatar']} {agent_info['name']}:</strong> {text}
    </div>
    """, unsafe_allow_html=True)
    
    # Generate and play voice if enabled
    if st.session_state.get("voice_enabled", True):
        with st.spinner(f"{agent_info['name']} is speaking..."):
            try:
                # Run async voice generation
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                audio_url = loop.run_until_complete(
                    voice_manager.generate_speech(text, agent_type)
                )
                loop.close()
                
                if audio_url:
                    voice_manager.play_audio_in_streamlit(audio_url, agent_info['name'])
                else:
                    st.info(f"🔇 Voice synthesis temporarily unavailable for {agent_info['name']}")
                    
            except Exception as e:
                logger.error(f"Voice integration error: {e}")
                st.warning(f"Voice playback failed for {agent_info['name']}")

def init_voice_system():
    """Initialize voice system in Streamlit"""
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = True
    if "auto_play" not in st.session_state:
        st.session_state.auto_play = True
    if "voice_speed" not in st.session_state:
        st.session_state.voice_speed = 1.0
