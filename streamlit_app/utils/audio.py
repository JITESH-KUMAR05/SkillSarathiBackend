"""
Audio Processing Utilities
==========================

Handles audio playback, recording, and voice processing for BuddyAgents.
"""

import streamlit as st
import io
import base64
from typing import Optional
import numpy as np
import streamlit.components.v1 as components

class AudioManager:
    """Manages audio operations for the frontend"""
    
    def __init__(self):
        self.audio_format = "audio/wav"
    
    def play_audio_safe(self, audio_data: bytes) -> bool:
        """Safe audio player using BytesIO to avoid MediaFileHandler issues"""
        try:
            if not audio_data or len(audio_data) == 0:
                st.error("❌ No audio data to play")
                return False
            
            if audio_data == b"placeholder_audio":
                st.warning("⚠️ Placeholder audio data received")
                return False
            
            # Method 1: Use BytesIO with st.audio (recommended approach)
            import io
            try:
                audio_io = io.BytesIO(audio_data)
                st.audio(audio_io, format='audio/wav')
                st.success("✅ Audio ready! Click ▶️ to play")
                return True
            except Exception as bytesio_error:
                st.warning(f"BytesIO audio failed: {bytesio_error}")
            
            # Method 2: HTML5 audio with base64 as fallback
            import base64
            audio_b64 = base64.b64encode(audio_data).decode()
            
            # Create autoplay HTML5 audio player
            audio_html = f"""
            <div style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #e8f5e8 0%, #f3e5f5 100%); 
                        border-radius: 15px; border: 3px solid #4CAF50; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <h3 style="color: #2E7D32; margin: 0 0 15px 0; text-align: center;">🎵 AI Voice Response</h3>
                <audio controls style="width: 100%; max-width: 600px; margin: 10px 0;" preload="auto" autoplay>
                    <source src="data:audio/wav;base64,{audio_b64}" type="audio/wav">
                    <source src="data:audio/mpeg;base64,{audio_b64}" type="audio/mpeg">
                    <source src="data:audio/ogg;base64,{audio_b64}" type="audio/ogg">
                    <p style="color: red; text-align: center;">❌ Your browser doesn't support audio playback. Please try Chrome/Firefox.</p>
                </audio>
                <div style="text-align: center; margin-top: 15px;">
                    <p style="margin: 5px 0; color: #1565C0; font-weight: bold;">💡 Audio should play automatically!</p>
                    <p style="margin: 5px 0; color: #424242;">If you don't hear audio, click the ▶️ play button above</p>
                    <p style="margin: 5px 0; color: #666; font-size: 12px;">🔍 Audio: {len(audio_data)} bytes | Format: WAV</p>
                </div>
            </div>
            """
            
            st.markdown(audio_html, unsafe_allow_html=True)
            st.success("✅ HTML5 audio player loaded!")
            
            return True
            
        except Exception as e:
            st.error(f"❌ Audio playback failed: {e}")
            import traceback
            st.error(f"Error details: {traceback.format_exc()}")
            return False

    def play_audio(self, audio_data: bytes, auto_play: bool = True) -> str:
        """Play audio using safe HTML5 method to avoid MediaFileHandler issues"""
        try:
            # Validate audio data
            if not audio_data or len(audio_data) == 0:
                st.error("❌ No audio data received")
                return ""
            
            # Check if it's placeholder audio
            if audio_data == b"placeholder_audio":
                st.warning("🎵 Voice generation completed but audio data not available")
                return ""
            
            # Log audio info for debugging
            st.info(f"🔊 Audio received: {len(audio_data)} bytes")
            
            # Add download button for manual testing
            try:
                st.download_button(
                    label="💾 Download Audio File for Testing",
                    data=audio_data,
                    file_name=f"voice_response_{len(audio_data)}_bytes.wav",
                    mime="audio/wav",
                    help="Download the audio file to test it manually"
                )
            except Exception as download_error:
                st.warning(f"Download button failed: {download_error}")
            
            # Use the safe audio player to avoid MediaFileHandler issues
            if self.play_audio_safe(audio_data):
                return "audio_ready"
            else:
                return ""
            try:
                st.download_button(
                    label="💾 Download Audio File for Testing",
                    data=audio_data,
                    file_name=f"voice_response_{len(audio_data)}_bytes.wav",
                    mime="audio/wav",
                    help="Download the audio file to test it manually"
                )
            except Exception as download_error:
                st.warning(f"Download button failed: {download_error}")
            
            # Try multiple audio formats for better compatibility
            try:
                # Use safe audio method to avoid MediaFileHandler issues
                return "audio_ready" if self.play_audio_safe(audio_data) else ""
            except Exception as st_audio_error:
                st.warning(f"Streamlit audio failed: {st_audio_error}")
                
                # Fallback: Use HTML5 audio with base64 encoding
                try:
                    import base64
                    audio_b64 = base64.b64encode(audio_data).decode()
                    
                    # Create HTML audio player with better compatibility
                    audio_html = f"""
                    <div style="margin: 15px 0; padding: 10px; background: #f0f2f6; border-radius: 8px;">
                        <p><strong>� Voice Response Ready</strong></p>
                        <audio controls style="width: 100%; max-width: 400px;" preload="auto">
                            <source src="data:audio/wav;base64,{audio_b64}" type="audio/wav">
                            <source src="data:audio/mpeg;base64,{audio_b64}" type="audio/mpeg">
                            <source src="data:audio/ogg;base64,{audio_b64}" type="audio/ogg">
                            <p style="color: red;">❌ Your browser doesn't support audio playback. Please try Chrome/Firefox.</p>
                        </audio>
                        <p><small>💡 Click the play button above to hear the AI's voice response</small></p>
                    </div>
                    """
                    
                    st.markdown(audio_html, unsafe_allow_html=True)
                    st.success("🎵 Fallback audio player loaded!")
                    return audio_b64
                    
                except Exception as html_error:
                    st.error(f"HTML audio fallback failed: {html_error}")
                    return ""
            
        except Exception as e:
            st.error(f"Audio playback completely failed: {e}")
            st.info(f"💡 Debug info: audio_data type={type(audio_data)}, length={len(audio_data) if audio_data else 0}")
            return ""
    
    def create_audio_player(self, audio_data: bytes, key: Optional[str] = None) -> bool:
        """Create an audio player widget using safe BytesIO method"""
        try:
            import io
            audio_io = io.BytesIO(audio_data)
            st.audio(audio_io, format=self.audio_format)
            return True
        except Exception as e:
            st.error(f"Failed to create audio player: {e}")
            return False
    
    def record_audio_button(self, key: str = "audio_recorder") -> Optional[bytes]:
        """Create audio recording button with speech-to-text"""
        st.markdown("### 🎤 Voice Input")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🎤 Start Voice Input", key=f"{key}_start", type="primary"):
                st.info("🎤 Click 'Record Audio' below to speak...")
                
        with col2:
            if st.button("⏹️ Stop & Process", key=f"{key}_stop"):
                st.success("✅ Voice processing complete!")
        
        # Add JavaScript-based speech recognition
        speech_to_text_html = f"""
        <div id="voice-input-{key}" style="margin: 20px 0;">
            <button onclick="startSpeechRecognition_{key}()" 
                    style="background: #FF4B4B; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px;">
                🎤 Click to Speak
            </button>
            <button onclick="stopSpeechRecognition_{key}()" 
                    style="background: #0E4B8C; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; margin-left: 10px;">
                ⏹️ Stop
            </button>
            <div id="speech-output-{key}" style="margin-top: 15px; padding: 10px; background: #f0f2f6; border-radius: 5px; min-height: 50px;">
                <em>Your speech will appear here...</em>
            </div>
        </div>

        <script>
        let recognition_{key};
        let isRecording_{key} = false;

        function startSpeechRecognition_{key}() {{
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition_{key} = new SpeechRecognition();
                recognition_{key}.continuous = true;
                recognition_{key}.interimResults = true;
                recognition_{key}.lang = 'en-US';

                recognition_{key}.onstart = function() {{
                    isRecording_{key} = true;
                    document.getElementById('speech-output-{key}').innerHTML = '<strong>🎤 Listening... Speak now!</strong>';
                }};

                recognition_{key}.onresult = function(event) {{
                    let transcript = '';
                    for (let i = event.resultIndex; i < event.results.length; ++i) {{
                        transcript += event.results[i][0].transcript;
                    }}
                    document.getElementById('speech-output-{key}').innerHTML = '<strong>📝 Detected:</strong><br>' + transcript;
                    
                    // Store the transcript for Streamlit to access
                    sessionStorage.setItem('speechTranscript_{key}', transcript);
                }};

                recognition_{key}.onerror = function(event) {{
                    document.getElementById('speech-output-{key}').innerHTML = '<span style="color: red;">❌ Speech recognition error: ' + event.error + '</span>';
                }};

                recognition_{key}.onend = function() {{
                    isRecording_{key} = false;
                    document.getElementById('speech-output-{key}').innerHTML += '<br><em>✅ Recording stopped.</em>';
                }};

                recognition_{key}.start();
            }} else {{
                document.getElementById('speech-output-{key}').innerHTML = '<span style="color: red;">❌ Speech recognition not supported in this browser. Please use Chrome/Edge.</span>';
            }}
        }}

        function stopSpeechRecognition_{key}() {{
            if (recognition_{key} && isRecording_{key}) {{
                recognition_{key}.stop();
            }}
        }}
        </script>
        """
        
        components.html(speech_to_text_html, height=200)
        
        # Check if speech transcript is available
        if st.button("📥 Get Voice Input", key=f"{key}_get"):
            st.info("💡 Speak using the microphone above, then click this button to use your voice input!")
        
        return None
    
    def text_to_speech_indicator(self, text: str, agent: str) -> None:
        """Show TTS processing indicator"""
        with st.spinner(f"🔊 Generating voice for {agent}..."):
            st.info(f"Converting to speech: {text[:50]}{'...' if len(text) > 50 else ''}")

    def create_voice_conversation_interface(self, agent: str) -> str:
        """Create a complete voice conversation interface"""
        st.markdown("---")
        st.markdown("### 🎙️ Voice Conversation Mode")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**🎤 Speak to the AI:**")
            
            # Simple speech recognition button
            if st.button("🎤 Click & Speak", key=f"voice_input_{agent}", type="primary"):
                st.info("🎤 Feature coming soon! For now, type your message below and the AI will respond with voice.")
                
            st.markdown("""
            <div style='padding: 15px; background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); 
                        border-radius: 10px; margin: 10px 0; border: 2px solid #90caf9;'>
                <small style='color: #1565c0; font-weight: bold;'>💡 <strong>How to use voice:</strong><br>
                <span style='color: #424242;'>
                1. Type your message below<br>
                2. Click "Share" to send<br>
                3. Click ▶️ on the audio player to hear AI's voice response
                </span>
                </small>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**🔊 AI Voice Response:**")
            st.info("The AI will generate voice after responding. Click the ▶️ play button to hear it!")
            
            # Audio controls
            st.markdown("**🎚️ Voice Settings:**")
            voice_enabled = st.checkbox("🔊 Enable Voice", value=True, key=f"voice_enabled_{agent}")
            if voice_enabled:
                st.success("✅ Voice responses enabled")
            else:
                st.warning("⚠️ Voice responses disabled")
        
        return "voice_interface_ready"

# Create audio processing functions for easy import
audio_manager = AudioManager()

def play_tts_audio(audio_data: bytes, auto_play: bool = True) -> bool:
    """Helper function to play TTS audio"""
    if audio_data:
        try:
            audio_manager.play_audio(audio_data, auto_play)
            return True
        except Exception as e:
            st.error(f"TTS playback failed: {e}")
            return False
    return False

def show_audio_controls(voice_enabled: bool = True) -> dict:
    """Show audio control widgets"""
    controls = {}
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        controls['voice_enabled'] = st.checkbox(
            "🔊 Enable Voice", 
            value=voice_enabled,
            help="Enable text-to-speech for agent responses"
        )
    
    with col2:
        controls['auto_play'] = st.checkbox(
            "▶️ Auto Play", 
            value=True,
            help="Automatically play voice responses"
        )
    
    with col3:
        controls['voice_speed'] = st.slider(
            "🎚️ Speed", 
            min_value=0.5, 
            max_value=2.0, 
            value=1.0, 
            step=0.1,
            help="Voice playback speed"
        )
    
    return controls

# Create global audio manager instance
audio_manager = AudioManager()
