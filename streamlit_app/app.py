"""
Streamlit Frontend for BuddyAgents Platform
==========================================

Comprehensive test interface for all agents with document upload functionality.
"""

import streamlit as st
import requests
import json
import io
from datetime import datetime
from typing import Dict, Any, Optional
import base64
from streamlit_mic_recorder import mic_recorder

# Speech-to-Text function
def transcribe_audio(audio_bytes):
    """
    Transcribe audio bytes to text using speech recognition.
    Handles format conversion from streamlit-mic-recorder to compatible format.
    """
    if audio_bytes is None:
        return "No audio data received"
    
    try:
        import tempfile
        import os
        import speech_recognition as sr
        from pydub import AudioSegment
        import io
        
        # Create temporary files
        temp_input_path = None
        temp_wav_path = None
        
        try:
            # Save the audio bytes to a temporary file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_input:
                temp_input.write(audio_bytes)
                temp_input_path = temp_input.name
            
            # Convert audio to WAV format using pydub
            # streamlit-mic-recorder typically outputs WebM format
            try:
                # Try to load as WebM first
                audio = AudioSegment.from_file(temp_input_path, format="webm")
            except:
                try:
                    # Try other formats
                    audio = AudioSegment.from_file(temp_input_path)
                except:
                    # Try loading as raw bytes
                    audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            
            # Convert to WAV format (16-bit, mono, 16kHz - optimal for speech recognition)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Export as WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                audio.export(temp_wav_path, format="wav")
            
            # Initialize speech recognizer
            recognizer = sr.Recognizer()
            
            # Load and process the WAV file
            with sr.AudioFile(temp_wav_path) as source:
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=1)
                audio_data = recognizer.record(source)
            
            # Try Google Speech Recognition first (requires internet)
            try:
                text = recognizer.recognize_google(audio_data)
                return text if text.strip() else "No speech detected"
                
            except sr.UnknownValueError:
                return "Could not understand the audio. Please speak clearly."
                
            except sr.RequestError:
                # Fallback to offline recognition
                try:
                    text = recognizer.recognize_sphinx(audio_data)
                    return text if text.strip() else "No speech detected"
                except:
                    return "Speech recognition service unavailable. Please check your internet connection."
            
        finally:
            # Clean up temporary files
            for path in [temp_input_path, temp_wav_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except:
                        pass
                        
    except ImportError as e:
        missing_lib = str(e).split("'")[1] if "'" in str(e) else "speech recognition library"
        return f"Missing dependency: {missing_lib}. Please install required packages."
        
    except Exception as e:
        error_msg = f"Audio transcription error: {str(e)}"
        st.error(error_msg)
        return f"Could not transcribe the audio. Please try again."

# Page configuration
st.set_page_config(
    page_title="BuddyAgents Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Session state initialization with persistence
if 'candidate_id' not in st.session_state:
    st.session_state.candidate_id = None
if 'session_ids' not in st.session_state:
    st.session_state.session_ids = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = {'mitra': [], 'guru': [], 'parikshak': []}
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None

def load_session_from_storage():
    """Load session data from browser storage if available"""
    # Check if we have stored session data
    if st.session_state.candidate_id is None:
        # Try to restore from URL params or storage
        query_params = st.query_params
        if 'candidate_id' in query_params:
            candidate_id = query_params['candidate_id']
            # Validate this candidate exists
            if validate_candidate_session(candidate_id):
                st.session_state.candidate_id = candidate_id
                # Clear URL params
                del st.query_params['candidate_id']

def validate_candidate_session(candidate_id: str) -> bool:
    """Validate if a candidate session is still valid"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/candidates/candidate/{candidate_id}/progress")
        return response.status_code == 200
    except:
        return False

def persist_session(candidate_id: str, user_data: Optional[dict] = None):
    """Persist session data"""
    st.session_state.candidate_id = candidate_id
    if user_data:
        st.session_state.user_profile = user_data
    
    # Store in URL for persistence across refreshes
    st.query_params['candidate_id'] = candidate_id

# Load session on startup
load_session_from_storage()

def register_candidate(name: str, email: str, skills: list, experience: str, target_role: str) -> Optional[str]:
    """Register a new candidate"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/candidates/register",
            json={
                "name": name,
                "email": email,
                "skills": skills,
                "experience_level": experience,
                "target_role": target_role
            }
        )
        
        if response.status_code == 200:
            user_data = response.json()
            candidate_id = user_data['candidate_id']
            # Persist session for the newly registered user
            persist_session(candidate_id, user_data)
            return candidate_id
        else:
            st.error(f"Registration failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Registration error: {str(e)}")
        return None

def login_candidate(email: str) -> Optional[Dict[str, Any]]:
    """Login existing candidate by email"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/candidates/login",
            json={"email": email}
        )
        
        if response.status_code == 200:
            user_data = response.json()
            # Persist session for the logged-in user
            persist_session(user_data['id'], user_data)
            return user_data
        else:
            st.error(f"Login failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return None

def send_chat_message(agent_type: str, message: str, candidate_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Send message to agent and get response with session continuity"""
    try:
        payload = {
            "message": message,
            "candidate_id": candidate_id,
            "agent_type": agent_type,
            "voice_enabled": True
        }
        
        # Include session_id if provided for conversation continuity
        if session_id:
            payload["session_id"] = session_id
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/chat/enhanced",
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Store the session_id for future messages in this agent conversation
            if 'session_id' in response_data:
                if agent_type not in st.session_state.session_ids:
                    st.session_state.session_ids[agent_type] = response_data['session_id']
            
            return response_data
        else:
            st.error(f"Chat failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Chat error: {str(e)}")
        return None

def check_and_prompt_registration(agent_name: str) -> bool:
    """Check if user is registered, prompt registration if not"""
    if st.session_state.candidate_id is None:
        st.warning(f"🔐 Please register to chat with {agent_name}")
        
        # Inline registration form
        with st.form(f"register_form_{agent_name.lower()}"):
            st.subheader("Quick Registration")
            
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name", placeholder="Enter your name")
                email = st.text_input("Email", placeholder="your@email.com")
            with col2:
                phone = st.text_input("Phone", placeholder="+91 9876543210")
                preferred_language = st.selectbox("Preferred Language", ["en", "hi"], format_func=lambda x: "English" if x == "en" else "Hindi")
            
            skills = st.multiselect(
                "Skills", 
                ["Python", "JavaScript", "Data Analysis", "Machine Learning", "Communication", "Leadership"],
                default=["Python"]
            )
            
            interests = st.multiselect(
                "Interests",
                ["Software Development", "Data Science", "Web Development", "Mobile Apps", "AI/ML", "Career Growth"],
                default=["Software Development"]
            )
            
            submitted = st.form_submit_button("🚀 Register & Start Chatting", type="primary")
            
            if submitted:
                if name and email:
                    try:
                        candidate_data = {
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "skills": skills,
                            "interests": interests,
                            "preferred_language": preferred_language
                        }
                        
                        response = requests.post(f"{API_BASE_URL}/api/v1/candidates/register", json=candidate_data)
                        
                        if response.status_code == 200:
                            candidate_data = response.json()
                            st.session_state.candidate_id = candidate_data['candidate_id']
                            st.session_state.candidate_name = candidate_data['name']
                            st.success(f"✅ Welcome {name}! You can now chat with {agent_name}")
                            st.rerun()
                        else:
                            st.error(f"Registration failed: {response.text}")
                    except Exception as e:
                        st.error(f"Registration error: {str(e)}")
                else:
                    st.error("Please fill in at least your name and email")
        
        return False
    return True

def upload_document_to_guru(candidate_id: str, file) -> Optional[str]:
    """Upload document for Guru processing"""
    try:
        files = {"file": file}
        data = {"candidate_id": candidate_id}
        
        response = requests.post(
            f"{API_BASE_URL}/api/v1/documents/guru/upload",
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            return response.json()['document_id']
        else:
            st.error(f"Upload failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return None

def process_document_with_guru(document_id: str, action: str, topic: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Process document with Guru agent"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/documents/guru/process/{document_id}",
            json={
                "action": action,
                "specific_topic": topic,
                "difficulty_level": "intermediate"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Processing failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        return None

def test_voice_generation(agent_type: str, text: str) -> Optional[bytes]:
    """Test voice generation for an agent"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/voice/tts",
            json={
                "text": text,
                "agent": agent_type
            }
        )
        
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Voice generation failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Voice error: {str(e)}")
        return None

def get_candidate_progress(candidate_id: str) -> Optional[Dict[str, Any]]:
    """Get candidate progress data"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/candidates/candidate/{candidate_id}/progress")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Progress fetch failed: {response.text}")
            return None
    except Exception as e:
        st.error(f"Progress error: {str(e)}")
        return None

# Main UI
st.title("🤖 BuddyAgents Platform")
st.markdown("**AI Multi-Agent Companion for India with MCP Integration**")

# Sidebar for candidate authentication
with st.sidebar:
    st.header("👤 Candidate Access")
    
    if st.session_state.candidate_id is None:
        # Login/Register tabs
        login_tab, register_tab = st.tabs(["🔑 Login", "📝 Register"])
        
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="your.email@example.com")
                
                if st.form_submit_button("Login"):
                    if email:
                        candidate_data = login_candidate(email)
                        if candidate_data:
                            st.session_state.candidate_id = candidate_data['candidate_id']
                            st.session_state.candidate_name = candidate_data['name']
                            st.success(f"Welcome back, {candidate_data['name']}!")
                            st.rerun()
                    else:
                        st.error("Please enter your email")
        
        with register_tab:
            with st.form("registration_form"):
                name = st.text_input("Full Name", placeholder="Enter your name")
                email = st.text_input("Email", placeholder="your.email@example.com")
                skills = st.multiselect(
                    "Skills", 
                    ["Python", "JavaScript", "Java", "React", "Node.js", "SQL", "Machine Learning", "Data Science"],
                    default=["Python"]
                )
                experience = st.selectbox("Experience Level", ["beginner", "intermediate", "advanced"])
                target_role = st.text_input("Target Role", placeholder="Software Engineer")
                
                if st.form_submit_button("Register"):
                    if name and email:
                        candidate_id = register_candidate(name, email, skills, experience, target_role)
                        if candidate_id:
                            st.session_state.candidate_id = candidate_id
                            st.session_state.candidate_name = name
                            st.success(f"Registered! Welcome, {name}!")
                            st.rerun()
                    else:
                        st.error("Please fill in all required fields")
    else:
        # Logged in user info
        candidate_name = getattr(st.session_state, 'candidate_name', 'User')
        st.success(f"Logged in as: {candidate_name}")
        st.caption(f"ID: {st.session_state.candidate_id[:8]}...")
        
        if st.button("Logout"):
            st.session_state.candidate_id = None
            st.session_state.candidate_name = None
            st.session_state.session_ids = {}
            st.session_state.chat_history = {'mitra': [], 'guru': [], 'parikshak': []}
            st.success("Logged out successfully!")
            st.rerun()
        
        # Show progress
        st.header("📊 AI-Powered Progress Analysis")
        if st.button("🤖 Analyze My Progress"):
            progress = get_candidate_progress(st.session_state.candidate_id)
            if progress:
                # Basic metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Sessions", progress['total_sessions'])
                with col2:
                    st.metric("Total Messages", progress['total_messages'])
                with col3:
                    if 'agents_interacted' in progress:
                        st.metric("Agents Met", len(progress['agents_interacted']))
                
                # AI Analysis Section
                if 'ai_analysis' in progress:
                    ai = progress['ai_analysis']
                    
                    # Overall Progress Score
                    st.subheader("🎯 Overall Progress")
                    progress_score = ai.get('overall_progress_score', 0)
                    st.progress(progress_score / 100)
                    st.write(f"**Progress Score:** {progress_score:.1f}%")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Learning Style:** {ai.get('primary_learning_style', 'Analytical').title()}")
                        st.write(f"**Engagement Level:** {ai.get('engagement_level', 'Medium').title()}")
                    with col2:
                        st.write(f"**Learning Velocity:** {ai.get('learning_velocity', 1.0):.1f}x")
                        st.write(f"**Next Milestone:** {ai.get('next_milestone', 'Continue learning')}")
                    
                    # Skill Assessments
                    if ai.get('skill_assessments'):
                        st.subheader("💪 Skill Assessment")
                        for skill in ai['skill_assessments']:
                            level_emoji = {"beginner": "🌱", "intermediate": "🌿", "advanced": "🌳", "expert": "🏆"}
                            emoji = level_emoji.get(skill['current_level'], "🎯")
                            st.write(f"{emoji} **{skill['skill_name'].title()}:** {skill['current_level'].title()} "
                                   f"({skill['sessions_count']} sessions, {skill['confidence_score']:.1f} confidence)")
                    
                    # AI Insights
                    if ai.get('key_insights'):
                        st.subheader("🧠 AI Insights")
                        for insight in ai['key_insights'][:3]:  # Show top 3 insights
                            insight_type = insight['type']
                            emoji = {"strength": "💪", "weakness": "📈", "opportunity": "🎯", "recommendation": "💡"}
                            st.info(f"{emoji.get(insight_type, '🔍')} **{insight['title']}**\n\n{insight['description']}")
                    
                    # Agent Recommendations
                    col1, col2 = st.columns(2)
                    with col1:
                        if ai.get('guru_recommendations'):
                            st.subheader("👨‍🏫 Guru's Learning Tips")
                            for rec in ai['guru_recommendations'][:3]:
                                st.write(f"• {rec}")
                    
                    with col2:
                        if ai.get('parikshak_recommendations'):
                            st.subheader("🎯 Parikshak's Interview Prep")
                            for rec in ai['parikshak_recommendations'][:3]:
                                st.write(f"• {rec}")
                    
                    # Completion Estimate
                    if ai.get('estimated_completion_time'):
                        st.info(f"⏱️ **Estimated Learning Timeline:** {ai['estimated_completion_time']}")
                
                else:
                    st.info("💭 AI analysis will be available after more interactions. Keep chatting with the agents!")
                    if 'agents_interacted' in progress:
                        st.write("**Agents Interacted:**", progress['agents_interacted'])
        
        # Voice Settings
        st.header("🎵 Voice Settings")
        auto_audio = st.checkbox(
            "Auto-play voice responses",
            value=getattr(st.session_state, 'auto_audio', False),
            help="Automatically play voice for agent responses"
        )
        st.session_state.auto_audio = auto_audio

# Main content area
if st.session_state.candidate_id is None:
    st.info("👈 Please register as a candidate to start using the platform")
else:
    # Voice Testing Section
    with st.expander("🎵 Voice Testing (TTS)", expanded=False):
        st.subheader("Test Voice Generation")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            test_agent = st.selectbox(
                "Select Agent Voice",
                ["mitra", "guru", "parikshak"],
                format_func=lambda x: {
                    "mitra": "🤗 Mitra (मित्र) - Hindi",
                    "guru": "👨‍🏫 Guru (गुरु) - English", 
                    "parikshak": "🎯 Parikshak (परीक्षक) - English"
                }[x]
            )
            
            test_text = st.text_area(
                "Text to Convert",
                value={
                    "mitra": "नमस्ते! मैं मित्र हूँ। आप कैसे हैं?",
                    "guru": "Hello! I'm Guru, your learning mentor. How can I help you today?",
                    "parikshak": "Welcome! I'm Parikshak, your interview coach. Let's practice together."
                }[test_agent],
                height=100
            )
        
        with col2:
            if st.button("🎵 Generate Voice", type="primary"):
                if test_text.strip():
                    with st.spinner("Generating audio..."):
                        audio_data = test_voice_generation(test_agent, test_text)
                        
                        if audio_data:
                            st.success(f"✅ Audio generated! ({len(audio_data)} bytes)")
                            st.audio(audio_data, format='audio/wav')
                        else:
                            st.error("❌ Failed to generate audio")
                else:
                    st.warning("Please enter some text to convert")
    
    # Agent selection tabs
    tab1, tab2, tab3 = st.tabs(["🤗 Mitra (मित्र)", "👨‍🏫 Guru (गुरु)", "🎯 Parikshak (परीक्षक)"])
    
    # Mitra Tab - Emotional Support
    with tab1:
        st.header("🤗 Mitra - Your AI Friend")
        st.markdown("*Warm, caring companion for emotional support and daily conversations*")
        
        # Check registration
        if not check_and_prompt_registration("Mitra"):
            st.stop()
        
        # Chat interface
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            for i, msg in enumerate(st.session_state.chat_history['mitra']):
                if msg['role'] == 'user':
                    st.chat_message("user").write(msg['content'])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg['content'])
                        
                        # Only auto-play voice for the LATEST assistant message if auto-audio is enabled
                        is_latest_message = (i == len(st.session_state.chat_history['mitra']) - 1)
                        if is_latest_message and getattr(st.session_state, 'auto_audio', False) and getattr(st.session_state, 'new_response_mitra', False):
                            # Generate and auto-play voice for latest response only
                            audio_data = test_voice_generation('mitra', msg['content'])
                            if audio_data:
                                st.audio(audio_data, format='audio/wav', autoplay=True)
                            # Reset the flag after playing
                            st.session_state.new_response_mitra = False
                        elif not getattr(st.session_state, 'auto_audio', False):
                            # Show manual voice button
                            if st.button(f"🎵 Play Voice", key=f"mitra_voice_{i}"):
                                with st.spinner("Generating audio..."):
                                    audio_data = test_voice_generation('mitra', msg['content'])
                                    if audio_data:
                                        st.audio(audio_data, format='audio/wav')
        
        # Voice input section
        st.write("🎙️ **Voice Input** (Speak your question)")
        voice_input = mic_recorder(
            start_prompt="Start recording",
            stop_prompt="Stop recording", 
            just_once=True,
            use_container_width=True,
            callback=None,
            args=(),
            kwargs={},
            key='mitra_voice'
        )
        
        # Process voice input if available
        if voice_input and voice_input['bytes']:
            st.info("🎤 Voice recorded! Processing speech to text...")
            
            # Transcribe the audio to text
            transcribed_text = transcribe_audio(voice_input['bytes'])
            
            if transcribed_text:
                st.success(f"🎙️ **Transcribed:** {transcribed_text}")
                
                # Automatically send the transcribed text as user input
                st.session_state.chat_history['mitra'].append({'role': 'user', 'content': transcribed_text})
                
                # Send to API with session continuity
                response = send_chat_message(
                    'mitra', 
                    transcribed_text, 
                    st.session_state.candidate_id,
                    st.session_state.session_ids.get('mitra')
                )
                
                if response:
                    # Add assistant response to history
                    st.session_state.chat_history['mitra'].append({
                        'role': 'assistant', 
                        'content': response['response']
                    })
                    # Set flag for auto-audio to play the new response
                    st.session_state.new_response_mitra = True
                    st.rerun()
            else:
                st.error("Could not transcribe the audio. Please try again.")
        
        # Chat input
        if mitra_input := st.chat_input("मैं आज कैसे मदद कर सकता हूँ? (How can I help you today?)"):
            # Add user message to history
            st.session_state.chat_history['mitra'].append({'role': 'user', 'content': mitra_input})
            
            # Send to API with session continuity
            response = send_chat_message(
                'mitra', 
                mitra_input, 
                st.session_state.candidate_id,
                st.session_state.session_ids.get('mitra')
            )
            
            if response:
                # Add assistant response to history
                st.session_state.chat_history['mitra'].append({
                    'role': 'assistant', 
                    'content': response['response']
                })
                # Set flag for auto-audio to play the new response
                st.session_state.new_response_mitra = True
                st.rerun()
    
    # Guru Tab - Learning & Documents
    with tab2:
        st.header("👨‍🏫 Guru - Your Learning Mentor")
        st.markdown("*Educational guidance, skill development, and document analysis*")
        
        # Check registration
        if not check_and_prompt_registration("Guru"):
            st.stop()
        
        # Two columns: Chat and Document Upload
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("💬 Chat with Guru")
            
            # Display chat history
            for i, msg in enumerate(st.session_state.chat_history['guru']):
                if msg['role'] == 'user':
                    st.chat_message("user").write(msg['content'])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg['content'])
                        
                        # Only auto-play voice for the LATEST assistant message if auto-audio is enabled
                        is_latest_message = (i == len(st.session_state.chat_history['guru']) - 1)
                        if is_latest_message and getattr(st.session_state, 'auto_audio', False) and getattr(st.session_state, 'new_response_guru', False):
                            # Generate and auto-play voice for latest response only
                            audio_data = test_voice_generation('guru', msg['content'])
                            if audio_data:
                                st.audio(audio_data, format='audio/wav', autoplay=True)
                            # Reset the flag after playing
                            st.session_state.new_response_guru = False
                        elif not getattr(st.session_state, 'auto_audio', False):
                            # Show manual voice button
                            if st.button(f"🎵 Play Voice", key=f"guru_voice_{i}"):
                                with st.spinner("Generating audio..."):
                                    audio_data = test_voice_generation('guru', msg['content'])
                                    if audio_data:
                                        st.audio(audio_data, format='audio/wav')
            
            # Voice input section
            st.write("🎙️ **Voice Input** (Speak your question)")
            guru_voice_input = mic_recorder(
                start_prompt="Start recording",
                stop_prompt="Stop recording", 
                just_once=True,
                use_container_width=True,
                callback=None,
                args=(),
                kwargs={},
                key='guru_voice'
            )
            
            # Process voice input if available
            if guru_voice_input and guru_voice_input['bytes']:
                st.info("🎤 Voice recorded! Processing speech to text...")
                
                # Transcribe the audio to text
                transcribed_text = transcribe_audio(guru_voice_input['bytes'])
                
                if transcribed_text:
                    st.success(f"🎙️ **Transcribed:** {transcribed_text}")
                    
                    # Automatically send the transcribed text as user input
                    st.session_state.chat_history['guru'].append({'role': 'user', 'content': transcribed_text})
                    
                    # Send to API with session continuity
                    response = send_chat_message(
                        'guru', 
                        transcribed_text, 
                        st.session_state.candidate_id,
                        st.session_state.session_ids.get('guru')
                    )
                    
                    if response:
                        # Add assistant response to history
                        st.session_state.chat_history['guru'].append({
                            'role': 'assistant', 
                            'content': response['response']
                        })
                        # Set flag for auto-audio to play the new response
                        st.session_state.new_response_guru = True
                        st.rerun()
                else:
                    st.error("Could not transcribe the audio. Please try again.")
            
            # Chat input
            if guru_input := st.chat_input("Ask me about learning, skills, or career guidance"):
                # Add user message to history
                st.session_state.chat_history['guru'].append({'role': 'user', 'content': guru_input})
                
                # Send to API with session continuity
                response = send_chat_message(
                    'guru', 
                    guru_input, 
                    st.session_state.candidate_id,
                    st.session_state.session_ids.get('guru')
                )
                
                if response:
                    # Add assistant response to history
                    st.session_state.chat_history['guru'].append({
                        'role': 'assistant', 
                        'content': response['response']
                    })
                    # Set flag for auto-audio to play the new response
                    st.session_state.new_response_guru = True
                    st.rerun()
        
        with col2:
            st.subheader("📄 Document Analysis")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Upload document for analysis",
                type=['txt', 'pdf', 'docx', 'md', 'py', 'js', 'html', 'css', 'json'],
                help="Upload documents for explanation, test generation, or analysis"
            )
            
            if uploaded_file is not None:
                st.write(f"**File:** {uploaded_file.name}")
                st.write(f"**Size:** {uploaded_file.size} bytes")
                
                if st.button("Upload to Guru", key="upload_btn"):
                    with st.spinner("Uploading..."):
                        document_id = upload_document_to_guru(st.session_state.candidate_id, uploaded_file)
                        
                        if document_id:
                            st.success(f"Document uploaded! ID: {document_id[:8]}...")
                            st.session_state.last_document_id = document_id
                
                # Document processing options
                if hasattr(st.session_state, 'last_document_id'):
                    st.subheader("🔍 Process Document")
                    
                    action = st.selectbox(
                        "Choose action:",
                        ["explain", "generate_test", "summarize", "extract_concepts"]
                    )
                    
                    specific_topic = st.text_input(
                        "Specific topic (optional)",
                        placeholder="Enter specific topic to focus on"
                    )
                    
                    if st.button("Process Document", key="process_btn"):
                        with st.spinner("Processing with Guru..."):
                            result = process_document_with_guru(
                                st.session_state.last_document_id, 
                                action, 
                                specific_topic
                            )
                            
                            if result:
                                st.success("Processing completed!")
                                st.json(result['result'])
    
    # Parikshak Tab - Interview Coaching
    with tab3:
        st.header("🎯 Parikshak - Your Interview Coach")
        st.markdown("*Professional interview preparation and technical assessment*")
        
        # Check registration
        if not check_and_prompt_registration("Parikshak"):
            st.stop()
        
        # Chat interface
        chat_container = st.container()
        
        with chat_container:
            # Display chat history
            for i, msg in enumerate(st.session_state.chat_history['parikshak']):
                if msg['role'] == 'user':
                    st.chat_message("user").write(msg['content'])
                else:
                    with st.chat_message("assistant"):
                        st.write(msg['content'])
                        
                        # Only auto-play voice for the LATEST assistant message if auto-audio is enabled
                        is_latest_message = (i == len(st.session_state.chat_history['parikshak']) - 1)
                        if is_latest_message and getattr(st.session_state, 'auto_audio', False) and getattr(st.session_state, 'new_response_parikshak', False):
                            # Generate and auto-play voice for latest response only
                            audio_data = test_voice_generation('parikshak', msg['content'])
                            if audio_data:
                                st.audio(audio_data, format='audio/wav', autoplay=True)
                            # Reset the flag after playing
                            st.session_state.new_response_parikshak = False
                        elif not getattr(st.session_state, 'auto_audio', False):
                            # Show manual voice button
                            if st.button(f"🎵 Play Voice", key=f"parikshak_voice_{i}"):
                                with st.spinner("Generating audio..."):
                                    audio_data = test_voice_generation('parikshak', msg['content'])
                                    if audio_data:
                                        st.audio(audio_data, format='audio/wav')
        
        # Voice input section
        st.write("🎙️ **Voice Input** (Speak your question)")
        parikshak_voice_input = mic_recorder(
            start_prompt="Start recording",
            stop_prompt="Stop recording", 
            just_once=True,
            use_container_width=True,
            callback=None,
            args=(),
            kwargs={},
            key='parikshak_voice'
        )
        
        # Process voice input if available
        if parikshak_voice_input and parikshak_voice_input['bytes']:
            st.info("🎤 Voice recorded! Processing speech to text...")
            
            # Transcribe the audio to text
            transcribed_text = transcribe_audio(parikshak_voice_input['bytes'])
            
            if transcribed_text:
                st.success(f"🎙️ **Transcribed:** {transcribed_text}")
                
                # Automatically send the transcribed text as user input
                st.session_state.chat_history['parikshak'].append({'role': 'user', 'content': transcribed_text})
                
                # Send to API with session continuity
                response = send_chat_message(
                    'parikshak', 
                    transcribed_text, 
                    st.session_state.candidate_id,
                    st.session_state.session_ids.get('parikshak')
                )
                
                if response:
                    # Add assistant response to history
                    st.session_state.chat_history['parikshak'].append({
                        'role': 'assistant', 
                        'content': response['response']
                    })
                    # Set flag for auto-audio to play the new response
                    st.session_state.new_response_parikshak = True
                    st.rerun()
            else:
                st.error("Could not transcribe the audio. Please try again.")
        
        # Chat input
        if parikshak_input := st.chat_input("Ask me about interview preparation, mock interviews, or assessments"):
            # Add user message to history
            st.session_state.chat_history['parikshak'].append({'role': 'user', 'content': parikshak_input})
            
            # Send to API with session continuity
            response = send_chat_message(
                'parikshak', 
                parikshak_input, 
                st.session_state.candidate_id,
                st.session_state.session_ids.get('parikshak')
            )
            
            if response:
                # Add assistant response to history
                st.session_state.chat_history['parikshak'].append({
                    'role': 'assistant', 
                    'content': response['response']
                })
                # Set flag for auto-audio to play the new response
                st.session_state.new_response_parikshak = True
                st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        🤖 BuddyAgents Platform - AI Multi-Agent Companion for India<br>
        Powered by Azure OpenAI • Voice by Murf AI • Built with FastAPI & Streamlit
    </div>
    """, 
    unsafe_allow_html=True
)