import streamlit as st
import requests
import json
from datetime import datetime
import time

# Configure Streamlit
st.set_page_config(
    page_title="Skillsarathi AI - Real Multi-Agent Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .agent-card {
        background: white;
        border: 2px solid #e1e5e9;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s;
    }
    .agent-card:hover {
        border-color: #667eea;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
    .agent-card.active {
        border-color: #667eea;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
        border-left: 4px solid #667eea;
    }
    .user-message {
        background: #f8f9fa;
        border-left-color: #28a745;
    }
    .ai-message {
        background: #e3f2fd;
        border-left-color: #2196f3;
    }
    .real-ai-badge {
        background: #28a745;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .status-connected {
        background: #28a745;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }
    .status-disconnected {
        background: #dc3545;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_agent" not in st.session_state:
    st.session_state.current_agent = "mentor"

# Configuration
BACKEND_URL = "http://localhost:8000"

# Agents configuration
AGENTS = {
    "mentor": {
        "name": "Anmol Mentor",
        "icon": "🎯",
        "description": "Career guidance and personal development",
        "color": "#2196f3"
    },
    "therapist": {
        "name": "Dr. Sneha",
        "icon": "💚",
        "description": "Mental health and wellness support",
        "color": "#4caf50"
    },
    "interview": {
        "name": "Parikshak",
        "icon": "💼",
        "description": "Interview preparation and skills",
        "color": "#ff9800"
    }
}

def check_backend_status():
    """Check if backend is reachable"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

def send_message(message, agent):
    """Send message to backend and get AI response"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat",
            json={"message": message, "agent": agent},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "response": data.get("response", "No response received"),
                "agent": data.get("agent", agent)
            }
        else:
            return {
                "success": False,
                "response": f"Backend error: {response.status_code}",
                "agent": agent
            }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "response": "❌ Cannot connect to backend. Please check if it's running.",
            "agent": agent
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": "⏰ Request timed out. The AI is taking too long to respond.",
            "agent": agent
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"Connection error: {str(e)}",
            "agent": agent
        }

# Header
st.markdown("""
<div class="main-header">
    <h1>🚀 Skillsarathi AI</h1>
    <h3>Real Multi-Agent Platform for India</h3>
    <p>Powered by GitHub LLM | Real AI Responses | Live Backend Connection</p>
</div>
""", unsafe_allow_html=True)

# Check backend status
backend_connected = check_backend_status()
status_class = "status-connected" if backend_connected else "status-disconnected"
status_text = "🟢 Connected" if backend_connected else "🔴 Disconnected"

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown(f'<div class="{status_class}">Backend: {status_text}</div>', unsafe_allow_html=True)
with col2:
    if st.button("🔄 Refresh Status"):
        st.rerun()
with col3:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# Sidebar - Agent Selection
st.sidebar.markdown("## 🤖 Select AI Agent")

for agent_id, agent_info in AGENTS.items():
    is_active = st.session_state.current_agent == agent_id
    
    if st.sidebar.button(
        f"{agent_info['icon']} {agent_info['name']}\n{agent_info['description']}",
        key=agent_id,
        use_container_width=True
    ):
        st.session_state.current_agent = agent_id
        st.rerun()

current_agent = AGENTS[st.session_state.current_agent]
st.sidebar.markdown(f"""
### Current Agent: {current_agent['icon']} {current_agent['name']}
**Specialty:** {current_agent['description']}
""")

# Main chat interface
st.markdown("## 💬 AI Chat Interface")

# Display chat messages
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>👤 You:</strong><br>
                {message["content"]}
                <br><small>📅 {message["timestamp"]}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            real_ai_badge = ""
            if message.get("real_ai", False):
                real_ai_badge = '<span class="real-ai-badge">✅ REAL AI</span>'
            
            agent_info = AGENTS.get(message.get("agent_key", "mentor"), current_agent)
            
            st.markdown(f"""
            <div class="chat-message ai-message">
                <strong>{agent_info['icon']} {agent_info['name']}:</strong> {real_ai_badge}<br>
                {message["content"]}
                <br><small>📅 {message["timestamp"]} | ⚡ {message.get("latency", 0)}ms</small>
            </div>
            """, unsafe_allow_html=True)

# Chat input
if backend_connected:
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "💬 Your message:",
            placeholder=f"Ask {current_agent['name']} anything...",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("🚀 Send", use_container_width=True)
        with col2:
            st.markdown(f"**Talking to:** {current_agent['icon']} {current_agent['name']}")
        
        if submitted and user_input.strip():
            # Add user message
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            st.session_state.messages.append(user_message)
            
            # Show processing
            with st.spinner(f"🤖 {current_agent['name']} is thinking..."):
                start_time = time.time()
                
                # Get AI response
                result = send_message(user_input, st.session_state.current_agent)
                
                end_time = time.time()
                latency = round((end_time - start_time) * 1000, 2)
                
                # Add AI response
                ai_message = {
                    "role": "assistant",
                    "content": result["response"],
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "agent_key": st.session_state.current_agent,
                    "latency": latency,
                    "real_ai": result["success"]
                }
                st.session_state.messages.append(ai_message)
            
            st.rerun()
else:
    st.error("❌ Backend is not connected. Please start the backend server.")
    st.code("cd /path/to/backend && uv run uvicorn main_simple_fixed:app --host 0.0.0.0 --port 8000 --reload")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <h4>🚀 Skillsarathi AI - Real Multi-Agent Platform</h4>
    <p><strong>✅ GitHub LLM</strong> | <strong>✅ Real AI Responses</strong> | <strong>✅ Live Backend</strong></p>
    <p><small>Built with ❤️ for India | Powered by FastAPI + Streamlit</small></p>
</div>
""", unsafe_allow_html=True)
