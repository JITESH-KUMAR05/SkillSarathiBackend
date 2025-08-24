"""
Skillsarathi AI Backend Testing Interface
Comprehensive Streamlit app to test all backend functionalities
"""

import streamlit as st
import asyncio
import websockets
import json
import requests
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import time

# Configure Streamlit
st.set_page_config(
    page_title="Skillsarathi AI - Backend Testing",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend Configuration
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws"

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "name": "Test User",
        "age": 25,
        "location": "India",
        "profession": "Software Engineer",
        "interests": ["AI", "Technology", "Learning"],
        "learning_goals": ["Python", "Machine Learning", "Career Growth"]
    }
if 'current_agent' not in st.session_state:
    st.session_state.current_agent = "companion"
if 'interview_session' not in st.session_state:
    st.session_state.interview_session = None

def main():
    """Main Streamlit application"""
    
    # Sidebar for navigation
    st.sidebar.title("🎯 Skillsarathi AI Testing")
    st.sidebar.markdown("---")
    
    # Test selection
    test_mode = st.sidebar.selectbox(
        "Select Test Mode",
        [
            "🤖 Multi-Agent Chat",
            "🎥 Interview Simulation", 
            "📚 Document Upload & RAG",
            "🗣️ Text-to-Speech (Murf)",
            "🔧 API Testing",
            "📊 System Status"
        ]
    )
    
    # User Profile Configuration
    st.sidebar.markdown("### 👤 User Profile")
    with st.sidebar.expander("Edit Profile", expanded=False):
        st.session_state.user_profile["name"] = st.text_input(
            "Name", value=st.session_state.user_profile["name"]
        )
        st.session_state.user_profile["age"] = st.number_input(
            "Age", value=st.session_state.user_profile["age"], min_value=16, max_value=100
        )
        st.session_state.user_profile["location"] = st.text_input(
            "Location", value=st.session_state.user_profile["location"]
        )
        st.session_state.user_profile["profession"] = st.text_input(
            "Profession", value=st.session_state.user_profile["profession"]
        )
        
        # Handle lists
        interests_str = st.text_area(
            "Interests (comma-separated)", 
            value=", ".join(st.session_state.user_profile["interests"])
        )
        st.session_state.user_profile["interests"] = [
            i.strip() for i in interests_str.split(",") if i.strip()
        ]
        
        goals_str = st.text_area(
            "Learning Goals (comma-separated)", 
            value=", ".join(st.session_state.user_profile["learning_goals"])
        )
        st.session_state.user_profile["learning_goals"] = [
            g.strip() for g in goals_str.split(",") if g.strip()
        ]
    
    # Main content based on selected test mode
    if test_mode == "🤖 Multi-Agent Chat":
        test_multi_agent_chat()
    elif test_mode == "🎥 Interview Simulation":
        test_interview_simulation()
    elif test_mode == "📚 Document Upload & RAG":
        test_document_rag()
    elif test_mode == "🗣️ Text-to-Speech (Murf)":
        test_tts_murf()
    elif test_mode == "🔧 API Testing":
        test_api_endpoints()
    elif test_mode == "📊 System Status":
        show_system_status()

def test_multi_agent_chat():
    """Test the multi-agent chat system"""
    st.title("🤖 Multi-Agent Chat Testing")
    
    # Agent selection
    col1, col2 = st.columns([2, 1])
    
    with col2:
        agent_type = st.selectbox(
            "Select Agent",
            ["auto", "companion", "mentor", "interview"],
            index=0,
            help="Auto-detect will choose the best agent based on your message"
        )
        
        if st.button("🧹 Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    with col1:
        # Chat interface
        st.markdown("### Chat with Skillsarathi AI")
        
        # Display chat history
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    st.markdown(f"**You ({message.get('timestamp', 'N/A')}):** {message['content']}")
                else:
                    agent_name = {
                        "companion": "🤗 Sakhi (Companion)",
                        "mentor": "👨‍🏫 Guru (Mentor)", 
                        "interview": "👔 Parikshak (Interviewer)",
                        "auto": "🤖 AI"
                    }.get(message.get('agent_type', 'auto'), "🤖 AI")
                    
                    st.markdown(f"**{agent_name}:** {message['content']}")
                    
                    # Show additional metadata
                    if message.get('metadata'):
                        with st.expander("Response Details"):
                            st.json(message['metadata'])
        
        # Chat input
        user_message = st.text_area(
            "Type your message:",
            placeholder="Try asking about career advice, learning goals, or request a mock interview...",
            key="chat_input"
        )
        
        col_send, col_ws = st.columns([1, 1])
        
        with col_send:
            if st.button("💬 Send Message (HTTP)", disabled=not user_message.strip()):
                if user_message.strip():
                    send_http_message(user_message.strip(), agent_type)
        
        with col_ws:
            if st.button("⚡ Send via WebSocket", disabled=not user_message.strip()):
                if user_message.strip():
                    send_websocket_message(user_message.strip(), agent_type)

def send_http_message(message: str, agent_type: str):
    """Send message via HTTP API"""
    try:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "agent_type": agent_type
        })
        
        # Prepare request
        payload = {
            "message": message,
            "agent_type": agent_type,
            "user_context": st.session_state.user_profile
        }
        
        with st.spinner(f"Processing with {agent_type} agent..."):
            response = requests.post(
                f"{BACKEND_URL}/api/chat/message",
                json=payload,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Add response to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result.get("text", "No response"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent_type": result.get("agent_type", agent_type),
                "metadata": result.get("metadata", {}),
                "audio_url": result.get("audio_url")
            })
            
            # Show audio player if available
            if result.get("audio_url"):
                st.audio(result["audio_url"])
                
            st.success("Message sent successfully!")
            st.rerun()
            
        else:
            st.error(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Failed to send message: {str(e)}")

def send_websocket_message(message: str, agent_type: str):
    """Send message via WebSocket (simplified for demo)"""
    st.info("WebSocket messaging would be implemented in a real frontend. For now, using HTTP fallback.")
    send_http_message(message, agent_type)

def test_interview_simulation():
    """Test the interview simulation feature"""
    st.title("🎥 Interview Simulation Testing")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### Interview Settings")
        
        interview_type = st.selectbox(
            "Interview Type",
            ["general", "technical", "behavioral", "hr", "government", "startup"]
        )
        
        if st.button("🎬 Start New Interview"):
            start_interview_session(interview_type)
        
        if st.session_state.interview_session:
            st.success(f"Interview Session Active: {st.session_state.interview_session['type']}")
            if st.button("🛑 End Interview"):
                st.session_state.interview_session = None
                st.rerun()
    
    with col1:
        if st.session_state.interview_session:
            st.markdown("### 👔 Mock Interview in Progress")
            st.markdown(f"**Type:** {st.session_state.interview_session['type'].title()}")
            
            # Interview chat interface (similar to regular chat but with interview context)
            for message in st.session_state.chat_history:
                if message.get('session_type') == 'interview':
                    if message["role"] == "user":
                        st.markdown(f"**Candidate:** {message['content']}")
                    else:
                        st.markdown(f"**Interviewer:** {message['content']}")
            
            # Interview response input
            response = st.text_area(
                "Your Response:",
                placeholder="Answer the interview question naturally...",
                key="interview_response"
            )
            
            if st.button("📝 Submit Response", disabled=not response.strip()):
                if response.strip():
                    submit_interview_response(response.strip())
        else:
            st.info("👆 Start an interview session to begin the simulation")
            
            # Show example interview questions
            st.markdown("### 📝 Sample Interview Questions by Type")
            
            examples = {
                "Technical": [
                    "Explain the difference between a list and a tuple in Python",
                    "How would you optimize a slow database query?",
                    "Describe your approach to debugging a production issue"
                ],
                "Behavioral": [
                    "Tell me about a time when you faced a difficult challenge",
                    "How do you handle working under pressure?",
                    "Describe a situation where you had to learn something new quickly"
                ],
                "HR": [
                    "Why do you want to work for this company?",
                    "Where do you see yourself in 5 years?",
                    "What are your salary expectations?"
                ]
            }
            
            for category, questions in examples.items():
                with st.expander(f"{category} Questions"):
                    for q in questions:
                        st.markdown(f"• {q}")

def start_interview_session(interview_type: str):
    """Start a new interview session"""
    try:
        payload = {
            "type": "start_interview",
            "interview_type": interview_type,
            "user_context": st.session_state.user_profile
        }
        
        response = requests.post(
            f"{BACKEND_URL}/api/interview/start",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            st.session_state.interview_session = {
                "session_id": result.get("session_id"),
                "type": interview_type,
                "started_at": datetime.now()
            }
            
            # Add initial interview message
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result.get("text", "Welcome to the interview!"),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent_type": "interview",
                "session_type": "interview"
            })
            
            st.success(f"Started {interview_type} interview!")
            st.rerun()
        else:
            st.error(f"Failed to start interview: {response.text}")
            
    except Exception as e:
        st.error(f"Error starting interview: {str(e)}")

def submit_interview_response(response: str):
    """Submit response to interview"""
    try:
        if not st.session_state.interview_session:
            st.error("No active interview session")
            return
        
        # Add user response to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": response,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "session_type": "interview"
        })
        
        payload = {
            "message": response,
            "session_id": st.session_state.interview_session["session_id"],
            "agent_type": "interview",
            "user_context": st.session_state.user_profile
        }
        
        with st.spinner("Processing your response..."):
            api_response = requests.post(
                f"{BACKEND_URL}/api/interview/respond",
                json=payload,
                timeout=30
            )
        
        if api_response.status_code == 200:
            result = api_response.json()
            
            # Add interviewer response
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result.get("text", "Thank you for your response."),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent_type": "interview",
                "session_type": "interview",
                "metadata": result.get("metadata", {})
            })
            
            st.success("Response submitted!")
            st.rerun()
        else:
            st.error(f"Error: {api_response.text}")
            
    except Exception as e:
        st.error(f"Failed to submit response: {str(e)}")

def test_document_rag():
    """Test document upload and RAG functionality"""
    st.title("📚 Document Upload & RAG Testing")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Upload Documents")
        
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            accept_multiple_files=True,
            type=['pdf', 'txt', 'docx'],
            help="Upload documents to test the RAG system"
        )
        
        if uploaded_files:
            if st.button("🚀 Process Documents"):
                process_documents(uploaded_files)
        
        # Show uploaded documents
        if st.button("📋 List Uploaded Documents"):
            list_documents()
    
    with col2:
        st.markdown("### 🔍 Query Documents")
        
        query = st.text_area(
            "Ask a question about your documents:",
            placeholder="What is the main topic of the uploaded document?",
            key="rag_query"
        )
        
        if st.button("🔎 Search", disabled=not query.strip()):
            if query.strip():
                search_documents(query.strip())

def process_documents(uploaded_files):
    """Process uploaded documents"""
    try:
        for uploaded_file in uploaded_files:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                data = {"user_id": "test_user"}
                
                response = requests.post(
                    f"{BACKEND_URL}/api/documents/upload",
                    files=files,
                    data=data,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"✅ {uploaded_file.name}: {result.get('message', 'Processed successfully')}")
                else:
                    st.error(f"❌ {uploaded_file.name}: {response.text}")
                    
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")

def list_documents():
    """List all uploaded documents"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/documents/list/test_user")
        
        if response.status_code == 200:
            documents = response.json()
            if documents:
                df = pd.DataFrame(documents)
                st.dataframe(df)
            else:
                st.info("No documents uploaded yet")
        else:
            st.error(f"Error listing documents: {response.text}")
            
    except Exception as e:
        st.error(f"Failed to list documents: {str(e)}")

def search_documents(query: str):
    """Search documents using RAG"""
    try:
        payload = {"query": query, "user_id": "test_user"}
        
        with st.spinner("Searching documents..."):
            response = requests.post(
                f"{BACKEND_URL}/api/documents/search",
                json=payload,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            
            st.markdown("### 🎯 Search Results")
            st.markdown(f"**Answer:** {result.get('answer', 'No answer found')}")
            
            if result.get('sources'):
                st.markdown("**Sources:**")
                for i, source in enumerate(result['sources'], 1):
                    st.markdown(f"{i}. {source}")
                    
        else:
            st.error(f"Search failed: {response.text}")
            
    except Exception as e:
        st.error(f"Error searching documents: {str(e)}")

def test_tts_murf():
    """Test Text-to-Speech with Murf AI"""
    st.title("🗣️ Text-to-Speech (Murf) Testing")
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### 🎚️ Voice Settings")
        
        voice_id = st.selectbox(
            "Voice",
            ["en-IN-kavya", "en-IN-rishi", "en-US-male", "en-US-female"],
            help="Select the voice for synthesis"
        )
        
        speed = st.slider("Speed", 0.5, 2.0, 1.0, 0.1)
        volume = st.slider("Volume", 0.1, 1.0, 0.8, 0.1)
        
        format_type = st.selectbox("Format", ["mp3", "wav"])
    
    with col1:
        st.markdown("### 📝 Text to Convert")
        
        text_input = st.text_area(
            "Enter text to convert to speech:",
            value="नमस्ते! मैं स्किलसारथी AI हूं। मैं आपकी सहायता के लिए यहां हूं।",
            height=150,
            help="Enter text in English or Hindi"
        )
        
        if st.button("🎵 Generate Audio", disabled=not text_input.strip()):
            if text_input.strip():
                generate_audio(text_input.strip(), voice_id, speed, volume, format_type)

def generate_audio(text: str, voice_id: str, speed: float, volume: float, format_type: str):
    """Generate audio using Murf AI"""
    try:
        payload = {
            "text": text,
            "voice_id": voice_id,
            "speed": speed,
            "volume": volume,
            "format": format_type
        }
        
        with st.spinner("Generating audio..."):
            response = requests.post(
                f"{BACKEND_URL}/api/tts/generate",
                json=payload,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            audio_url = result.get("audio_url")
            
            if audio_url:
                st.success("✅ Audio generated successfully!")
                st.audio(audio_url)
                
                # Download link
                st.markdown(f"[🔗 Download Audio]({audio_url})")
            else:
                st.warning("Audio generated but no URL returned")
                
        else:
            st.error(f"TTS generation failed: {response.text}")
            
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")

def test_api_endpoints():
    """Test various API endpoints"""
    st.title("🔧 API Testing")
    
    # Health check
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏥 Health Check")
        if st.button("Check Backend Health"):
            check_backend_health()
    
    with col2:
        st.markdown("### 📊 Backend Info")
        if st.button("Get System Info"):
            get_system_info()
    
    # Authentication testing
    st.markdown("### 🔐 Authentication Testing")
    
    col_auth1, col_auth2 = st.columns(2)
    
    with col_auth1:
        st.markdown("**Register User**")
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        
        if st.button("Register"):
            if username and email and password:
                register_user(username, email, password)
    
    with col_auth2:
        st.markdown("**Login**")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if login_username and login_password:
                login_user(login_username, login_password)

def check_backend_health():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.success("✅ Backend is healthy!")
            st.json(data)
        else:
            st.error(f"❌ Backend unhealthy: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Cannot reach backend: {str(e)}")

def get_system_info():
    """Get system information"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/system/info", timeout=10)
        if response.status_code == 200:
            info = response.json()
            st.success("📊 System Information:")
            st.json(info)
        else:
            st.error(f"Failed to get system info: {response.text}")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def register_user(username: str, email: str, password: str):
    """Register a new user"""
    try:
        payload = {
            "username": username,
            "email": email,
            "password": password
        }
        
        response = requests.post(f"{BACKEND_URL}/api/auth/register", json=payload)
        
        if response.status_code == 200:
            st.success("✅ User registered successfully!")
        else:
            st.error(f"Registration failed: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def login_user(username: str, password: str):
    """Login user"""
    try:
        payload = {
            "username": username,
            "password": password
        }
        
        response = requests.post(f"{BACKEND_URL}/api/auth/login", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            st.success("✅ Login successful!")
            st.json(result)
        else:
            st.error(f"Login failed: {response.text}")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_system_status():
    """Show comprehensive system status"""
    st.title("📊 System Status Dashboard")
    
    # Backend status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Status"):
            st.rerun()
    
    with col2:
        backend_status = check_backend_status()
        if backend_status:
            st.success("✅ Backend Online")
        else:
            st.error("❌ Backend Offline")
    
    with col3:
        st.info(f"🕐 Last Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # System metrics
    st.markdown("### 📈 System Metrics")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/system/metrics", timeout=10)
        if response.status_code == 200:
            metrics = response.json()
            
            col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
            
            with col_metrics1:
                st.metric("Active Connections", metrics.get("active_connections", 0))
                st.metric("Total Messages", metrics.get("total_messages", 0))
            
            with col_metrics2:
                st.metric("CPU Usage", f"{metrics.get('cpu_usage', 0):.1f}%")
                st.metric("Memory Usage", f"{metrics.get('memory_usage', 0):.1f}%")
            
            with col_metrics3:
                st.metric("Response Time", f"{metrics.get('avg_response_time', 0):.2f}ms")
                st.metric("Error Rate", f"{metrics.get('error_rate', 0):.2f}%")
                
        else:
            st.warning("Could not fetch system metrics")
            
    except Exception as e:
        st.error(f"Error fetching metrics: {str(e)}")
    
    # Environment variables
    st.markdown("### 🔧 Environment Configuration")
    env_status = {
        "GITHUB_TOKEN": "✅" if os.getenv("GITHUB_TOKEN") else "❌",
        "MURF_API_KEY": "✅" if os.getenv("MURF_API_KEY") else "❌",
        "OPENAI_API_KEY": "✅" if os.getenv("OPENAI_API_KEY") else "❌ (Optional)",
        "AZURE_OPENAI_KEY": "✅" if os.getenv("AZURE_OPENAI_KEY") else "❌ (Optional)"
    }
    
    for env_var, status in env_status.items():
        st.markdown(f"**{env_var}:** {status}")

def check_backend_status():
    """Check if backend is responding"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    main()
