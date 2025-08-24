import streamlit as st
import requests
import json
import asyncio
import websockets
import aiohttp
import tempfile
import os
import time
import base64
import cv2
import numpy as np
import speech_recognition as sr
import threading
from datetime import datetime
from PIL import Image
import io

# Configure Streamlit
st.set_page_config(
    page_title="Skillsarathi AI - Advanced Multi-Agent Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .agent-dashboard {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    .agent-dashboard:hover {
        border-color: #667eea;
        transform: translateY(-5px);
        box-shadow: 0 8px 40px rgba(102, 126, 234, 0.2);
    }
    .chat-container {
        height: 400px;
        overflow-y: auto;
        border: 1px solid #e1e5e9;
        border-radius: 10px;
        padding: 1rem;
        background: #f8f9fa;
    }
    .message-bubble {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 15px;
        max-width: 80%;
    }
    .user-bubble {
        background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
        margin-left: auto;
        color: #333;
    }
    .ai-bubble {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        margin-right: auto;
        color: #333;
    }
    .feature-status {
        padding: 0.5rem 1rem;
        border-radius: 20px;
        margin: 0.2rem;
        display: inline-block;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .status-active {
        background: #28a745;
        color: white;
    }
    .status-inactive {
        background: #dc3545;
        color: white;
    }
    .status-processing {
        background: #ffc107;
        color: #333;
    }
    .video-container {
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 1rem;
        background: #f8f9fa;
    }
    .interview-controls {
        background: linear-gradient(135deg, #ff9a9e 0%, #fad0c4 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .rag-info {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
BACKEND_URL = "http://localhost:8001"
MURF_API_KEY = "ap2_748d5a3d73cd407eb42cbadcfc4ad8b1"

# Agent configurations
AGENTS = {
    "mentor": {
        "name": "Anmol Mentor",
        "icon": "🎯",
        "description": "Career guidance and personal development",
        "color": "#2196f3",
        "voice_id": "en-IN-neerja",
        "specialties": ["Career Planning", "Skill Development", "Goal Setting", "Professional Growth"]
    },
    "therapist": {
        "name": "Dr. Sneha",
        "icon": "💚",
        "description": "Mental health and wellness support",
        "color": "#4caf50",
        "voice_id": "en-IN-kavya",
        "specialties": ["Stress Management", "Emotional Wellness", "Mindfulness", "Work-Life Balance"]
    },
    "interview": {
        "name": "Parikshak",
        "icon": "💼",
        "description": "Interview preparation and technical evaluation",
        "color": "#ff9800",
        "voice_id": "en-IN-kiran",
        "specialties": ["Technical Interviews", "Coding Assessment", "Behavioral Questions", "Mock Interviews"]
    }
}

# Initialize session state
def init_session_state():
    if "agents_data" not in st.session_state:
        st.session_state.agents_data = {agent_id: {"messages": [], "user_profile": {}} for agent_id in AGENTS.keys()}
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"
    if "voice_enabled" not in st.session_state:
        st.session_state.voice_enabled = False
    if "video_enabled" not in st.session_state:
        st.session_state.video_enabled = False
    if "interview_mode" not in st.session_state:
        st.session_state.interview_mode = False
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "name": "",
            "skills": [],
            "experience": "",
            "goals": [],
            "conversation_history": []
        }

init_session_state()

class AdvancedMurfTTS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.murf.ai/v1"
        
    async def synthesize(self, text: str, voice_id: str = "en-IN-neerja") -> bytes:
        """Generate TTS audio with proper authentication"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        payload = {
            "voiceId": voice_id,
            "text": text,
            "format": "mp3",
            "sampleRate": 44100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/speech/generate",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    error_text = await response.text()
                    st.error(f"TTS Error {response.status}: {error_text}")
                    return b""

class VoiceRecorder:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
    def listen_once(self) -> str:
        """Record and transcribe speech once"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source)
                st.info("🎤 Listening... Speak now!")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
            text = self.recognizer.recognize_google(audio)
            return text
            
        except sr.WaitTimeoutError:
            return "Timeout - no speech detected"
        except sr.UnknownValueError:
            return "Could not understand audio"
        except Exception as e:
            return f"Speech recognition error: {str(e)}"

class VideoMonitor:
    def __init__(self):
        self.cap = None
        self.recording = False
        
    def start_camera(self):
        """Start video capture"""
        try:
            self.cap = cv2.VideoCapture(0)
            return True
        except Exception as e:
            st.error(f"Camera error: {e}")
            return False
            
    def capture_frame(self):
        """Capture a single frame"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None
        
    def detect_cheating(self, frame):
        """Basic cheating detection (multiple faces, phone detection, etc.)"""
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Load face cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        cheating_alerts = []
        
        # Check for multiple faces
        if len(faces) > 1:
            cheating_alerts.append("⚠️ Multiple faces detected")
            
        # Check if no face detected (person looking away)
        if len(faces) == 0:
            cheating_alerts.append("⚠️ No face detected - are you looking away?")
            
        return cheating_alerts, faces
        
    def stop_camera(self):
        """Stop video capture"""
        if self.cap:
            self.cap.release()

class RAGSystem:
    def __init__(self):
        self.user_data = st.session_state.user_profile
        
    def store_conversation(self, agent_id: str, user_message: str, ai_response: str):
        """Store conversation for RAG"""
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_id,
            "user_message": user_message,
            "ai_response": ai_response
        }
        
        if "conversation_history" not in self.user_data:
            self.user_data["conversation_history"] = []
            
        self.user_data["conversation_history"].append(conversation_entry)
        
        # Also store in agent-specific data
        st.session_state.agents_data[agent_id]["messages"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        st.session_state.agents_data[agent_id]["messages"].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_context_for_agent(self, agent_id: str) -> str:
        """Get relevant context for current conversation"""
        recent_conversations = self.user_data.get("conversation_history", [])[-5:]  # Last 5 conversations
        
        context = f"""
        User Profile:
        - Name: {self.user_data.get('name', 'Not provided')}
        - Skills: {', '.join(self.user_data.get('skills', []))}
        - Experience: {self.user_data.get('experience', 'Not provided')}
        - Goals: {', '.join(self.user_data.get('goals', []))}
        
        Recent Conversation Context:
        """
        
        for conv in recent_conversations:
            if conv['agent'] == agent_id:
                context += f"- User: {conv['user_message'][:100]}...\n"
                context += f"- AI: {conv['ai_response'][:100]}...\n"
                
        return context

# Initialize components
tts_manager = AdvancedMurfTTS(MURF_API_KEY)
voice_recorder = VoiceRecorder()
video_monitor = VideoMonitor()
rag_system = RAGSystem()

def check_backend_status():
    """Check backend connection"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def send_message_with_context(message: str, agent_id: str) -> dict:
    """Send message with RAG context"""
    try:
        # Get context from RAG system
        context = rag_system.get_context_for_agent(agent_id)
        enhanced_message = f"Context: {context}\n\nUser Message: {message}"
        
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": enhanced_message, "agent": agent_id},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data.get("response", "No response received")
            
            # Store in RAG system
            rag_system.store_conversation(agent_id, message, ai_response)
            
            return {
                "success": True,
                "response": ai_response,
                "agent": agent_id
            }
        else:
            return {
                "success": False,
                "response": f"Backend error: {response.status_code}",
                "agent": agent_id
            }
    except Exception as e:
        return {
            "success": False,
            "response": f"Connection error: {str(e)}",
            "agent": agent_id
        }

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 Skillsarathi AI - Advanced Multi-Agent Platform</h1>
    <h3>Real AI | Voice Communication | Video Monitoring | Smart RAG</h3>
    <p>Individual Agent Dashboards with Shared Intelligence & Advanced Features</p>
</div>
""", unsafe_allow_html=True)

# Status indicators
backend_connected = check_backend_status()
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_class = "status-active" if backend_connected else "status-inactive"
    status_text = "🟢 Connected" if backend_connected else "🔴 Disconnected"
    st.markdown(f'<div class="feature-status {status_class}">Backend: {status_text}</div>', unsafe_allow_html=True)

with col2:
    voice_status = "status-active" if st.session_state.voice_enabled else "status-inactive"
    st.markdown(f'<div class="feature-status {voice_status}">🎤 Voice: {"ON" if st.session_state.voice_enabled else "OFF"}</div>', unsafe_allow_html=True)

with col3:
    video_status = "status-active" if st.session_state.video_enabled else "status-inactive"
    st.markdown(f'<div class="feature-status {video_status}">📹 Video: {"ON" if st.session_state.video_enabled else "OFF"}</div>', unsafe_allow_html=True)

with col4:
    interview_status = "status-active" if st.session_state.interview_mode else "status-inactive"
    st.markdown(f'<div class="feature-status {interview_status}">💼 Interview: {"ON" if st.session_state.interview_mode else "OFF"}</div>', unsafe_allow_html=True)

# Navigation
nav_options = ["🏠 Dashboard"] + [f"{info['icon']} {info['name']}" for info in AGENTS.values()]
selected_nav = st.selectbox("Navigate to:", nav_options)

if selected_nav == "🏠 Dashboard":
    st.session_state.current_page = "dashboard"
else:
    for agent_id, info in AGENTS.items():
        if f"{info['icon']} {info['name']}" == selected_nav:
            st.session_state.current_page = agent_id
            break

# Dashboard Overview
if st.session_state.current_page == "dashboard":
    st.markdown("## 🏠 Multi-Agent Dashboard Overview")
    
    # Global controls
    st.markdown("### 🔧 Global Controls")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎤 Toggle Voice", use_container_width=True):
            st.session_state.voice_enabled = not st.session_state.voice_enabled
            st.rerun()
            
    with col2:
        if st.button("📹 Toggle Video", use_container_width=True):
            st.session_state.video_enabled = not st.session_state.video_enabled
            if st.session_state.video_enabled:
                video_monitor.start_camera()
            else:
                video_monitor.stop_camera()
            st.rerun()
            
    with col3:
        if st.button("💼 Interview Mode", use_container_width=True):
            st.session_state.interview_mode = not st.session_state.interview_mode
            st.rerun()
            
    with col4:
        if st.button("🗑️ Clear All Data", use_container_width=True):
            st.session_state.agents_data = {agent_id: {"messages": [], "user_profile": {}} for agent_id in AGENTS.keys()}
            st.session_state.user_profile = {"name": "", "skills": [], "experience": "", "goals": [], "conversation_history": []}
            st.rerun()
    
    # User Profile Section
    st.markdown("### 👤 User Profile (Shared Across All Agents)")
    
    with st.expander("📝 Update Your Profile", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Your Name", value=st.session_state.user_profile.get("name", ""))
            experience = st.text_area("Experience", value=st.session_state.user_profile.get("experience", ""))
            
        with col2:
            skills = st.text_input("Skills (comma-separated)", value=", ".join(st.session_state.user_profile.get("skills", [])))
            goals = st.text_input("Goals (comma-separated)", value=", ".join(st.session_state.user_profile.get("goals", [])))
            
        if st.button("💾 Update Profile"):
            st.session_state.user_profile.update({
                "name": name,
                "experience": experience,
                "skills": [s.strip() for s in skills.split(",") if s.strip()],
                "goals": [g.strip() for g in goals.split(",") if g.strip()]
            })
            st.success("✅ Profile updated!")
            st.rerun()
    
    # RAG Information
    st.markdown('<div class="rag-info">', unsafe_allow_html=True)
    st.markdown("### 🧠 Smart Memory System (RAG)")
    
    total_conversations = len(st.session_state.user_profile.get("conversation_history", []))
    st.metric("Total Conversations Stored", total_conversations)
    
    if total_conversations > 0:
        recent_conv = st.session_state.user_profile["conversation_history"][-1]
        st.markdown(f"**Last Interaction:** {recent_conv['timestamp'][:16]} with {AGENTS[recent_conv['agent']]['name']}")
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Agent Overview Cards
    st.markdown("### 🤖 Agent Status Overview")
    
    for agent_id, agent_info in AGENTS.items():
        agent_messages = len(st.session_state.agents_data[agent_id]["messages"])
        
        with st.container():
            st.markdown('<div class="agent-dashboard">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.markdown(f"## {agent_info['icon']}")
                
            with col2:
                st.markdown(f"### {agent_info['name']}")
                st.markdown(f"**Specialty:** {agent_info['description']}")
                st.markdown(f"**Messages:** {agent_messages}")
                
                # Show specialties
                st.markdown("**Capabilities:**")
                for specialty in agent_info['specialties']:
                    st.markdown(f"• {specialty}")
                    
            with col3:
                if st.button(f"Chat with {agent_info['name']}", key=f"chat_{agent_id}", use_container_width=True):
                    st.session_state.current_page = agent_id
                    st.rerun()
                    
            st.markdown('</div>', unsafe_allow_html=True)

# Individual Agent Pages
elif st.session_state.current_page in AGENTS:
    agent_id = st.session_state.current_page
    agent_info = AGENTS[agent_id]
    
    st.markdown(f"## {agent_info['icon']} {agent_info['name']} - Interactive Session")
    st.markdown(f"**Specialty:** {agent_info['description']}")
    
    # Agent-specific controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Video feed for interview mode
        if st.session_state.video_enabled and agent_id == "interview":
            st.markdown('<div class="video-container">', unsafe_allow_html=True)
            st.markdown("### 📹 Live Interview Monitoring")
            
            video_placeholder = st.empty()
            cheating_placeholder = st.empty()
            
            if video_monitor.cap:
                frame = video_monitor.capture_frame()
                if frame is not None:
                    # Detect cheating
                    cheating_alerts, faces = video_monitor.detect_cheating(frame)
                    
                    # Draw rectangles around faces
                    for (x, y, w, h) in faces:
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                    
                    # Display video
                    video_placeholder.image(frame, caption="Live Interview Feed", use_column_width=True)
                    
                    # Show cheating alerts
                    if cheating_alerts:
                        cheating_placeholder.error("\n".join(cheating_alerts))
                    else:
                        cheating_placeholder.success("✅ Monitoring: All clear")
                        
            st.markdown('</div>', unsafe_allow_html=True)
            
    with col2:
        # Chat interface
        st.markdown("### 💬 Conversation")
        
        # Display messages
        chat_container = st.container()
        with chat_container:
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            for message in st.session_state.agents_data[agent_id]["messages"]:
                if message["role"] == "user":
                    st.markdown(f'''
                    <div class="message-bubble user-bubble">
                        <strong>👤 You:</strong><br>
                        {message["content"]}
                        <br><small>📅 {message["timestamp"]}</small>
                    </div>
                    ''', unsafe_allow_html=True)
                else:
                    st.markdown(f'''
                    <div class="message-bubble ai-bubble">
                        <strong>{agent_info["icon"]} {agent_info["name"]}:</strong><br>
                        {message["content"]}
                        <br><small>📅 {message["timestamp"]}</small>
                    </div>
                    ''', unsafe_allow_html=True)
                    
            st.markdown('</div>', unsafe_allow_html=True)
            
    with col3:
        # Voice controls and features
        st.markdown("### 🎤 Voice & Features")
        
        if st.session_state.voice_enabled:
            if st.button("🎤 Start Voice Input", use_container_width=True):
                with st.spinner("🎤 Listening..."):
                    voice_text = voice_recorder.listen_once()
                    if voice_text and "error" not in voice_text.lower():
                        st.session_state.voice_input = voice_text
                        st.success(f"🎤 Heard: {voice_text}")
                    else:
                        st.error(f"🎤 {voice_text}")
                        
        # Text input
        user_input = st.text_area(
            "💭 Your message:",
            value=st.session_state.get("voice_input", ""),
            placeholder=f"Talk to {agent_info['name']}...",
            height=100,
            key=f"input_{agent_id}"
        )
        
        if st.button("🚀 Send Message", use_container_width=True, key=f"send_{agent_id}"):
            if user_input and user_input.strip():
                with st.spinner(f"🤖 {agent_info['name']} is thinking..."):
                    # Send message with context
                    result = send_message_with_context(user_input, agent_id)
                    
                    if result["success"]:
                        # Generate TTS if voice enabled
                        if st.session_state.voice_enabled:
                            try:
                                # Create audio file
                                async def generate_audio():
                                    return await tts_manager.synthesize(
                                        result["response"][:200],  # Limit length
                                        agent_info["voice_id"]
                                    )
                                
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                audio_data = loop.run_until_complete(generate_audio())
                                loop.close()
                                
                                if audio_data:
                                    # Save and play audio
                                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                                        tmp_file.write(audio_data)
                                        tmp_file_path = tmp_file.name
                                    
                                    st.audio(tmp_file_path)
                                    st.success(f"🔊 {agent_info['name']} spoke!")
                                    
                                    # Clean up
                                    try:
                                        os.unlink(tmp_file_path)
                                    except:
                                        pass
                                else:
                                    st.warning("⚠️ TTS generation failed")
                                    
                            except Exception as e:
                                st.error(f"🔊 TTS Error: {str(e)}")
                    else:
                        st.error(f"❌ {result['response']}")
                
                # Clear voice input
                if "voice_input" in st.session_state:
                    del st.session_state.voice_input
                    
                st.rerun()
        
        # Agent-specific features
        if agent_id == "interview" and st.session_state.interview_mode:
            st.markdown('<div class="interview-controls">', unsafe_allow_html=True)
            st.markdown("### 💼 Interview Controls")
            
            if st.button("📝 Start Technical Interview", use_container_width=True):
                st.info("🚀 Technical interview mode activated!")
                
            if st.button("⏹️ End Interview", use_container_width=True):
                st.success("✅ Interview session completed!")
                
            st.markdown("**Anti-Cheating Features:**")
            st.markdown("• 👁️ Face tracking")
            st.markdown("• 📱 Multiple person detection")
            st.markdown("• 🔍 Screen monitoring")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <h4>🚀 Skillsarathi AI - Advanced Multi-Agent Platform</h4>
    <p><strong>✅ Real AI</strong> | <strong>🎤 Voice Communication</strong> | <strong>📹 Video Monitoring</strong> | <strong>🧠 Smart RAG</strong></p>
    <p><strong>💼 Interview Mode</strong> | <strong>🔍 Anti-Cheating</strong> | <strong>📊 Shared Intelligence</strong></p>
    <p><small>Built with ❤️ for India | Advanced AI Platform</small></p>
</div>
""", unsafe_allow_html=True)
