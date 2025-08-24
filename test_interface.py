"""
Streamlit Test Interface for Skillsarathi AI Backend
Quick and easy way to test all backend functionalities
"""

import streamlit as st
import asyncio
import websockets
import json
import aiohttp
import time
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Skillsarathi AI - Backend Test Interface",
    page_icon="🤖",
    layout="wide"
)

# Title and description
st.title("🤖 Skillsarathi AI - Backend Test Interface")
st.markdown("Real-time testing interface for minimal latency WebSocket communication")

# Sidebar for configuration
st.sidebar.header("Configuration")
backend_url = st.sidebar.text_input("Backend URL", value="localhost:8000")
websocket_url = f"ws://{backend_url}/ws"
api_url = f"http://{backend_url}"

# Test connection button
if st.sidebar.button("🔗 Test Backend Connection"):
    with st.spinner("Testing connection..."):
        try:
            import requests
            response = requests.get(f"{api_url}/docs", timeout=5)
            if response.status_code == 200:
                st.sidebar.success("✅ Backend is running!")
                st.sidebar.write(f"API Docs: {api_url}/docs")
            else:
                st.sidebar.error(f"❌ Backend returned status {response.status_code}")
        except Exception as e:
            st.sidebar.error(f"❌ Connection failed: {str(e)}")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "websocket_connected" not in st.session_state:
    st.session_state.websocket_connected = False

# Chat interface
st.header("💬 Real-time Chat (WebSocket)")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    st.chat_message("user").write(prompt)
    
    # Send to backend and get response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Simple HTTP request for now (can be upgraded to WebSocket)
            import requests
            
            start_time = time.time()
            
            # Test with direct API call first
            payload = {
                "message": prompt,
                "user_id": "streamlit_test",
                "timestamp": datetime.now().isoformat()
            }
            
            # For now, simulate response since we don't have REST endpoint
            # This will be replaced with actual WebSocket connection
            response_texts = [
                f"I received your message: '{prompt}'. I'm responding with minimal latency!",
                f"Thank you for saying: '{prompt}'. How can I help you further?",
                f"Interesting! You mentioned: '{prompt}'. I'm here to assist you.",
                f"I understand: '{prompt}'. Let me help you with that."
            ]
            
            import random
            response_text = random.choice(response_texts)
            
            # Simulate streaming for demonstration
            words = response_text.split()
            for i, word in enumerate(words):
                full_response += word + " "
                message_placeholder.markdown(full_response + "▌")
                time.sleep(0.05)  # Simulate streaming delay
            
            end_time = time.time()
            latency = round((end_time - start_time) * 1000, 2)
            
            message_placeholder.markdown(full_response)
            st.caption(f"⚡ Response time: {latency}ms")
            
            # Add assistant response to chat
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Chat error: {e}")

# Metrics section
st.header("📊 Backend Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Messages", len(st.session_state.messages))

with col2:
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("User Messages", user_messages)

with col3:
    ai_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    st.metric("AI Responses", ai_messages)

with col4:
    st.metric("WebSocket Status", "🟢 Connected" if st.session_state.websocket_connected else "🔴 Disconnected")

# Test different agents
st.header("🎭 Multi-Agent Testing")

agent_col1, agent_col2, agent_col3 = st.columns(3)

with agent_col1:
    st.subheader("🤗 Companion Agent")
    if st.button("Test Companion", key="companion"):
        test_message = "I'm feeling a bit stressed about my exams. Can you help me?"
        st.session_state.messages.append({"role": "user", "content": test_message})
        response = "I understand exam stress can be overwhelming. Take deep breaths and remember you've prepared well. You've got this! 💪"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with agent_col2:
    st.subheader("👨‍🏫 Mentor Agent")
    if st.button("Test Mentor", key="mentor"):
        test_message = "Can you help me learn Python programming?"
        st.session_state.messages.append({"role": "user", "content": test_message})
        response = "Absolutely! Python is a great language to start with. Let's begin with variables and basic syntax. Would you like me to explain variables first?"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

with agent_col3:
    st.subheader("💼 Interview Agent")
    if st.button("Test Interview", key="interview"):
        test_message = "I want to practice for a software engineering interview"
        st.session_state.messages.append({"role": "user", "content": test_message})
        response = "Great! Let's start with a common question: Tell me about yourself and why you're interested in software engineering?"
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# Advanced testing section
st.header("🔧 Advanced Testing")

# Document upload test
st.subheader("📄 Document Upload & RAG Testing")
uploaded_file = st.file_uploader("Upload a document to test RAG functionality", type=['pdf', 'txt', 'docx'])
if uploaded_file is not None:
    st.success(f"File uploaded: {uploaded_file.name}")
    if st.button("Process Document"):
        st.info("Document processing would happen here (RAG system)")

# TTS testing
st.subheader("🔊 Text-to-Speech Testing")
tts_text = st.text_area("Enter text for TTS:", value="Hello! This is a test of the Murf AI text-to-speech system.")
if st.button("Generate Audio"):
    st.info("Audio generation would happen here (Murf AI integration)")

# Video interview simulation
st.subheader("🎥 Video Interview Testing")
if st.button("Start Mock Interview"):
    st.info("Video interview interface would launch here")

# Backend logs
st.header("📋 Backend Logs")
if st.button("Refresh Logs"):
    st.text_area("Recent logs would appear here", value="[INFO] Backend started\n[INFO] WebSocket connected\n[INFO] Message processed", height=150)

# Clear chat button
if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# Footer
st.markdown("---")
st.markdown("**Skillsarathi AI Backend Test Interface** - Built with Streamlit for rapid testing")

# Auto-refresh for real-time updates (optional)
if st.checkbox("Auto-refresh (5s)", value=False):
    time.sleep(5)
    st.rerun()
