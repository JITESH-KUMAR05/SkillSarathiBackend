"""
Production Multi-Agent Backend System with Streamlit Interface
============================================================

Complete backend implementation with:
- Individual agent pages (Mitra, Guru, Parikshak)
- Global agent selector and management
- Real-time WebSocket communication
- Voice, video, document processing
- Cultural intelligence for Indian users
- Advanced session management
"""

import streamlit as st
import asyncio
import websockets
import json
import time
import requests
import base64
import io
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import threading
import queue
import tempfile
import uuid
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import pickle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import voice integration
from voice_integration import voice_manager, render_voice_message, init_voice_system
from free_agent_llm import free_agent_llm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================================
# CORE AGENT SYSTEM
# ================================

class AgentType(str, Enum):
    """Three main agents as per specification"""
    MITRA = "mitra"       # Friend - Empathetic companion
    GURU = "guru"         # Mentor - Career & learning expert
    PARIKSHAK = "parikshak"  # Interviewer - Technical assessment

@dataclass
class UserProfile:
    """User profile with Indian cultural context"""
    user_id: str
    name: str
    region: str = "north"  # north, south, east, west, northeast
    languages: Optional[List[str]] = None
    professional_level: str = "intermediate"  # beginner, intermediate, advanced, expert
    interests: Optional[List[str]] = None
    cultural_preferences: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.languages is None:
            self.languages = ["english", "hindi"]
        if self.interests is None:
            self.interests = []
        if self.cultural_preferences is None:
            self.cultural_preferences = {}

@dataclass
class ConversationSession:
    """Enhanced conversation session management"""
    session_id: str
    user_profile: UserProfile
    active_agent: AgentType
    conversation_history: List[Dict[str, Any]]
    session_goals: List[str]
    emotional_state: str = "neutral"
    relationship_depth: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

class DatabaseManager:
    """SQLite database for session and user management"""
    
    def __init__(self, db_path: str = "buddyagents.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                region TEXT DEFAULT 'north',
                languages TEXT,
                professional_level TEXT DEFAULT 'intermediate',
                interests TEXT,
                cultural_preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversation sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                active_agent TEXT,
                conversation_history TEXT,
                session_goals TEXT,
                emotional_state TEXT DEFAULT 'neutral',
                relationship_depth REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
            )
        """)
        
        # Agent interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_interactions (
                interaction_id TEXT PRIMARY KEY,
                session_id TEXT,
                agent_type TEXT,
                user_message TEXT,
                agent_response TEXT,
                response_metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_user_profile(self, profile: UserProfile):
        """Save or update user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles 
            (user_id, name, region, languages, professional_level, interests, cultural_preferences, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.user_id,
            profile.name,
            profile.region,
            json.dumps(profile.languages),
            profile.professional_level,
            json.dumps(profile.interests),
            json.dumps(profile.cultural_preferences),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve user profile"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserProfile(
                user_id=row[0],
                name=row[1],
                region=row[2],
                languages=json.loads(row[3]),
                professional_level=row[4],
                interests=json.loads(row[5]),
                cultural_preferences=json.loads(row[6])
            )
        return None
    
    def save_session(self, session: ConversationSession):
        """Save conversation session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_sessions 
            (session_id, user_id, active_agent, conversation_history, session_goals, 
             emotional_state, relationship_depth, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.user_profile.user_id,
            session.active_agent.value,
            json.dumps(session.conversation_history),
            json.dumps(session.session_goals),
            session.emotional_state,
            session.relationship_depth,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT session_id, active_agent, created_at, updated_at 
            FROM conversation_sessions 
            WHERE user_id = ? 
            ORDER BY updated_at DESC
        """, (user_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "active_agent": row[1],
                "created_at": row[2],
                "updated_at": row[3]
            })
        
        conn.close()
        return sessions

class AgentPersonalities:
    """Agent personality definitions with Indian cultural context"""
    
    MITRA = {
        "name": "Mitra",
        "hindi_name": "मित्र",
        "role": "Empathetic AI Companion",
        "personality": "Warm, supportive, culturally aware friend",
        "color": "#e74c3c",  # Warm red
        "avatar": "🤗",
        "greeting": {
            "english": "Hello! I'm Mitra, your AI friend. How are you feeling today?",
            "hindi": "नमस्ते! मैं मित्र हूँ, आपका AI दोस्त। आज कैसा महसूस कर रहे हैं?"
        },
        "specialties": [
            "Emotional support and companionship",
            "Cultural celebrations and festivals",
            "Daily life conversations",
            "Stress relief and motivation",
            "Personal relationship advice"
        ],
        "communication_style": "Warm, empathetic, uses cultural references",
        "voice_characteristics": "Gentle, understanding, reassuring"
    }
    
    GURU = {
        "name": "Guru",
        "hindi_name": "गुरु",
        "role": "Career & Learning Mentor",
        "personality": "Wise, knowledgeable, progressive teacher",
        "color": "#3498db",  # Professional blue
        "avatar": "🧠",
        "greeting": {
            "english": "Welcome! I'm Guru, your learning and career mentor. Ready to grow together?",
            "hindi": "स्वागत है! मैं गुरु हूँ, आपका शिक्षा और करियर मार्गदर्शक। साथ में बढ़ने के लिए तैयार हैं?"
        },
        "specialties": [
            "Career guidance and planning",
            "Skill development strategies",
            "Interview preparation",
            "Learning roadmaps",
            "Indian job market insights",
            "Technical and soft skills coaching"
        ],
        "communication_style": "Structured, educational, encouraging",
        "voice_characteristics": "Authoritative yet approachable, inspiring"
    }
    
    PARIKSHAK = {
        "name": "Parikshak",
        "hindi_name": "परीक्षक",
        "role": "Technical Interview Specialist",
        "personality": "Professional, thorough, constructive evaluator",
        "color": "#27ae60",  # Professional green
        "avatar": "📋",
        "greeting": {
            "english": "Greetings! I'm Parikshak, your interview coach. Let's prepare you for success!",
            "hindi": "नमस्कार! मैं परीक्षक हूँ, आपका इंटरव्यू कोच। आपको सफलता के लिए तैयार करते हैं!"
        },
        "specialties": [
            "Technical interview simulation",
            "Behavioral assessment",
            "Communication skills evaluation", 
            "Real-time feedback and scoring",
            "Industry-specific interview prep",
            "Voice and presentation analysis"
        ],
        "communication_style": "Professional, detailed, constructive",
        "voice_characteristics": "Clear, professional, evaluative"
    }

class BackendCommunicator:
    """Simple backend communication using GitHub LLM"""
    
    def __init__(self):
        self.base_url = "http://localhost:8002"  # Enhanced backend
        self.session = requests.Session()
        self.connected = False
        
        # Try to initialize GitHub LLM directly
        self.github_llm = None
        self.init_github_llm()
    
    def init_github_llm(self):
        """Initialize GitHub LLM directly"""
        try:
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                # Import and initialize GitHub LLM
                from app.llm.github_llm import GitHubLLM
                self.github_llm = GitHubLLM(github_token=github_token)
                logger.info("✅ GitHub LLM initialized successfully")
            else:
                logger.warning("❌ GITHUB_TOKEN not found in environment")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub LLM: {e}")
            self.github_llm = None
    
    async def send_message_to_agent(
        self, 
        agent_type: AgentType,
        message: str,
        user_profile: UserProfile,
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Send message to specific agent via backend or GitHub LLM"""
        
        # Try GitHub LLM first if available
        if self.github_llm:
            try:
                return await self._process_with_github_llm(agent_type, message, user_profile)
            except Exception as e:
                logger.error(f"GitHub LLM error: {e}")
        
        # Try enhanced backend
        try:
            payload = {
                "agent": agent_type.value,
                "message": message,
                "user_profile": {
                    "user_id": user_profile.user_id,
                    "name": user_profile.name,
                    "region": user_profile.region,
                    "languages": user_profile.languages,
                    "professional_level": user_profile.professional_level,
                    "interests": user_profile.interests,
                    "cultural_preferences": user_profile.cultural_preferences
                },
                "session_context": session_context or {},
                "cultural_context": {
                    "region": user_profile.region,
                    "languages": user_profile.languages,
                    "communication_style": "formal",
                    "family_structure": "joint"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            response = await self._http_request(payload, self.base_url + "/api/agent/chat")
            return response
            
        except Exception as e:
            logger.error(f"Backend communication error: {e}")
            # Return agent-specific fallback response
            return self._get_fallback_response(agent_type, message, user_profile)
    
    async def _process_with_github_llm(
        self, 
        agent_type: AgentType, 
        message: str, 
        user_profile: UserProfile
    ) -> Dict[str, Any]:
        """Process message using enhanced LLM system"""
        
        # Get agent personality
        agent_info = getattr(AgentPersonalities, agent_type.value.upper())
        
        # Use the new free agent LLM system
        try:
            user_profile_dict = {
                "user_id": user_profile.user_id,
                "name": user_profile.name,
                "region": user_profile.region,
                "languages": user_profile.languages,
                "professional_level": user_profile.professional_level,
                "interests": user_profile.interests,
                "cultural_preferences": user_profile.cultural_preferences
            }
            
            response = await free_agent_llm.generate_response(
                agent_type=agent_type.value,
                message=message,
                user_profile=user_profile_dict,
                agent_info=agent_info
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Enhanced LLM processing error: {e}")
            # Return fallback response
            return self._get_fallback_response(agent_type, message, user_profile)
    
    def _extract_cultural_elements(self, text: str) -> List[str]:
        """Extract cultural elements from response text"""
        cultural_elements = []
        cultural_words = ["namaste", "ji", "acha", "theek", "dhanyawad", "sat sri akal", "vanakkam"]
        
        for word in cultural_words:
            if word.lower() in text.lower():
                cultural_elements.append(word)
        
        return cultural_elements
    
    async def _http_request(self, payload: Dict[str, Any], url: Optional[str] = None) -> Dict[str, Any]:
        """Send request via HTTP"""
        endpoint = url or f"{self.base_url}/api/chat/agent"
        
        try:
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"HTTP error: {e}")
            raise
    
    def _get_fallback_response(
        self, 
        agent_type: AgentType, 
        message: str, 
        user_profile: UserProfile
    ) -> Dict[str, Any]:
        """Generate fallback response when backend is unavailable"""
        
        personalities = {
            AgentType.MITRA: AgentPersonalities.MITRA,
            AgentType.GURU: AgentPersonalities.GURU,
            AgentType.PARIKSHAK: AgentPersonalities.PARIKSHAK
        }
        
        agent_info = personalities[agent_type]
        
        # Generate contextual fallback based on agent type
        if agent_type == AgentType.MITRA:
            fallback_text = f"I understand you're sharing something important with me. As your AI friend {agent_info['name']}, I'm here to listen and support you. Though I'm experiencing some connection issues right now, I want you to know that your feelings matter."
        
        elif agent_type == AgentType.GURU:
            fallback_text = f"Thank you for your question about learning and growth. As {agent_info['name']}, your mentor, I'm committed to helping you develop your skills. While I'm working through some technical challenges, I encourage you to keep that curiosity and drive for improvement."
        
        elif agent_type == AgentType.PARIKSHAK:
            fallback_text = f"I appreciate you practicing with me. As {agent_info['name']}, your interview coach, I'm here to help you prepare thoroughly. Though we're experiencing some connectivity issues, remember that consistent practice is key to interview success."
        
        return {
            "response": fallback_text,
            "agent": agent_type.value,
            "status": "fallback",
            "personality": agent_info,
            "cultural_context": {
                "region": user_profile.region,
                "languages": user_profile.languages
            }
        }
    
    def test_connection(self) -> bool:
        """Test backend connectivity"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            self.connected = response.status_code == 200
            return self.connected
        except:
            self.connected = False
            return False

# ================================
# STREAMLIT APP ARCHITECTURE
# ================================

def init_session_state():
    """Initialize Streamlit session state"""
    
    # Core system components
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
    
    if 'backend_communicator' not in st.session_state:
        st.session_state.backend_communicator = BackendCommunicator()
    
    # User profile and session management
    if 'current_user_profile' not in st.session_state:
        st.session_state.current_user_profile = None
    
    if 'current_session' not in st.session_state:
        st.session_state.current_session = None
    
    # Navigation state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "global_selector"
    
    if 'selected_agent' not in st.session_state:
        st.session_state.selected_agent = AgentType.MITRA
    
    # Feature flags
    if 'voice_enabled' not in st.session_state:
        st.session_state.voice_enabled = False
    
    if 'video_enabled' not in st.session_state:
        st.session_state.video_enabled = False
    
    if 'hindi_mode' not in st.session_state:
        st.session_state.hindi_mode = False

def render_sidebar():
    """Enhanced sidebar with navigation and user profile"""
    
    with st.sidebar:
        st.title("🧠 BuddyAgents India")
        st.markdown("*Next-Generation AI Companions*")
        
        # Backend connection status
        if st.button("🔄 Test Backend Connection"):
            with st.spinner("Testing connection..."):
                connected = st.session_state.backend_communicator.test_connection()
                if connected:
                    st.success("✅ Backend Connected")
                else:
                    st.error("❌ Backend Disconnected")
        
        st.divider()
        
        # User Profile Section
        st.subheader("👤 User Profile")
        
        # User profile form
        with st.form("user_profile_form"):
            user_name = st.text_input("Name", value=st.session_state.current_user_profile.name if st.session_state.current_user_profile else "")
            user_region = st.selectbox("Region", ["north", "south", "east", "west", "northeast"], 
                                     index=0 if not st.session_state.current_user_profile else 
                                     ["north", "south", "east", "west", "northeast"].index(st.session_state.current_user_profile.region))
            
            languages = st.multiselect("Languages", ["english", "hindi", "tamil", "telugu", "bengali", "marathi", "gujarati"],
                                     default=["english", "hindi"])
            
            professional_level = st.selectbox("Professional Level", ["beginner", "intermediate", "advanced", "expert"])
            
            if st.form_submit_button("💾 Save Profile"):
                if user_name:
                    user_id = user_name.lower().replace(" ", "_")
                    
                    profile = UserProfile(
                        user_id=user_id,
                        name=user_name,
                        region=user_region,
                        languages=languages,
                        professional_level=professional_level
                    )
                    
                    st.session_state.db_manager.save_user_profile(profile)
                    st.session_state.current_user_profile = profile
                    st.success("✅ Profile saved!")
                else:
                    st.error("Please enter your name")
        
        st.divider()
        
        # Navigation
        st.subheader("🧭 Navigation")
        
        pages = {
            "🌐 Global Agent Selector": "global_selector",
            "👥 Mitra - AI Friend": "mitra_agent",
            "🎓 Guru - AI Mentor": "guru_agent", 
            "💼 Parikshak - AI Interviewer": "parikshak_agent",
            "📊 Session History": "session_history",
            "⚙️ Settings": "settings"
        }
        
        for page_name, page_key in pages.items():
            if st.button(page_name, key=f"nav_{page_key}"):
                st.session_state.current_page = page_key
        
        st.divider()
        
        # Quick Settings
        st.subheader("⚡ Quick Settings")
        st.session_state.voice_enabled = st.checkbox("🎤 Voice Mode", value=st.session_state.voice_enabled)
        st.session_state.video_enabled = st.checkbox("📹 Video Mode", value=st.session_state.video_enabled)
        st.session_state.hindi_mode = st.checkbox("🇮🇳 Hindi Mode", value=st.session_state.hindi_mode)
        
        # Voice Controls
        voice_manager.render_voice_controls()

def render_global_agent_selector():
    """Global agent selector and management page"""
    
    st.title("🌐 Global Agent Selector")
    st.markdown("Choose your AI companion based on your current needs")
    
    # Agent comparison cards
    col1, col2, col3 = st.columns(3)
    
    agents_info = [
        (AgentType.MITRA, AgentPersonalities.MITRA, col1),
        (AgentType.GURU, AgentPersonalities.GURU, col2),
        (AgentType.PARIKSHAK, AgentPersonalities.PARIKSHAK, col3)
    ]
    
    for agent_type, agent_info, col in agents_info:
        with col:
            st.markdown(f"""
            <div style="padding: 20px; border: 2px solid #e1e8ed; border-radius: 10px; margin: 10px 0;">
                <h3 style="color: #1f77b4;">{agent_info['name']} ({agent_info['hindi_name']})</h3>
                <p><strong>{agent_info['role']}</strong></p>
                <p style="font-style: italic;">{agent_info['personality']}</p>
                
                <details>
                    <summary><strong>Specialties</strong></summary>
                    <ul>
                        {''.join([f"<li>{specialty}</li>" for specialty in agent_info['specialties']])}
                    </ul>
                </details>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Chat with {agent_info['name']}", key=f"select_{agent_type.value}"):
                st.session_state.selected_agent = agent_type
                st.session_state.current_page = f"{agent_type.value}_agent"
                st.rerun()
    
    st.divider()
    
    # Quick interaction section
    st.subheader("💬 Quick Interaction")
    
    if st.session_state.current_user_profile:
        agent_choice = st.selectbox("Choose Agent", [agent.value.title() for agent in AgentType])
        user_message = st.text_area("Your message:", placeholder="Type your message here...")
        
        if st.button("💌 Send Message"):
            if user_message and agent_choice:
                selected_agent_type = AgentType(agent_choice.lower())
                
                with st.spinner(f"Getting response from {agent_choice}..."):
                    # Create async context for backend communication
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    response = loop.run_until_complete(
                        st.session_state.backend_communicator.send_message_to_agent(
                            selected_agent_type,
                            user_message,
                            st.session_state.current_user_profile
                        )
                    )
                    
                    # Display response
                    agent_info = getattr(AgentPersonalities, selected_agent_type.value.upper())
                    
                    st.markdown(f"""
                    <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <h4>{agent_info['name']} ({agent_info['hindi_name']}) responds:</h4>
                        <p>{response['response']}</p>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Please set up your user profile in the sidebar first!")

def render_agent_page(agent_type: AgentType):
    """Render individual agent interaction page"""
    
    agent_info = getattr(AgentPersonalities, agent_type.value.upper())
    
    # Page header
    st.title(f"{agent_info['name']} ({agent_info['hindi_name']})")
    st.markdown(f"**{agent_info['role']}**")
    st.markdown(f"*{agent_info['personality']}*")
    
    # Greeting
    if st.session_state.hindi_mode:
        greeting = agent_info['greeting']['hindi']
    else:
        greeting = agent_info['greeting']['english']
    
    st.info(greeting)
    
    # Create or load session
    if not st.session_state.current_session or st.session_state.current_session.active_agent != agent_type:
        if st.session_state.current_user_profile:
            session_id = f"{agent_type.value}_{int(time.time())}"
            st.session_state.current_session = ConversationSession(
                session_id=session_id,
                user_profile=st.session_state.current_user_profile,
                active_agent=agent_type,
                conversation_history=[],
                session_goals=[]
            )
    
    # Agent specialties
    with st.expander("🎯 What I can help you with"):
        for specialty in agent_info['specialties']:
            st.markdown(f"• {specialty}")
    
    # Conversation interface
    st.subheader("💬 Conversation")
    
    # Display conversation history
    if st.session_state.current_session and st.session_state.current_session.conversation_history:
        for i, interaction in enumerate(st.session_state.current_session.conversation_history[-10:]):  # Show last 10
            
            # User message
            st.markdown(f"""
            <div style="background-color: #e8f4fd; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right; color: #2c3e50;">
                <strong>You:</strong> {interaction['user_message']}
            </div>
            """, unsafe_allow_html=True)
            
            # Agent response
            st.markdown(f"""
            <div style="background-color: #f0f8ff; padding: 10px; border-radius: 10px; margin: 5px 0; color: #2c3e50;">
                <strong style="color: {agent_info.get('color', '#1f77b4')};">{agent_info['name']}:</strong> {interaction['agent_response']}
            </div>
            """, unsafe_allow_html=True)
    
    # Message input
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_input = st.text_area("Your message:", key=f"input_{agent_type.value}", placeholder=f"Talk to {agent_info['name']}...")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        
        if st.button("📤 Send", key=f"send_{agent_type.value}"):
            if user_input and st.session_state.current_user_profile:
                process_agent_interaction(agent_type, user_input)
                st.rerun()
        
        if st.session_state.voice_enabled:
            if st.button("🎤 Voice", key=f"voice_{agent_type.value}"):
                st.info("Voice input feature coming soon!")
        
        if st.session_state.video_enabled:
            if st.button("📹 Video", key=f"video_{agent_type.value}"):
                st.info("Video call feature coming soon!")
    
    # Session management
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Session", key=f"save_{agent_type.value}"):
            if st.session_state.current_session:
                st.session_state.db_manager.save_session(st.session_state.current_session)
                st.success("Session saved!")
    
    with col2:
        if st.button("🔄 New Session", key=f"new_{agent_type.value}"):
            st.session_state.current_session = None
            st.rerun()
    
    with col3:
        if st.button("📊 View Analytics", key=f"analytics_{agent_type.value}"):
            show_session_analytics(agent_type)

def process_agent_interaction(agent_type: AgentType, user_message: str):
    """Process interaction with selected agent with voice integration"""
    
    if not st.session_state.current_user_profile:
        st.error("Please set up your profile first!")
        return
    
    with st.spinner(f"Getting response from {agent_type.value.title()}..."):
        try:
            # Create async context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Get response from backend
            response = loop.run_until_complete(
                st.session_state.backend_communicator.send_message_to_agent(
                    agent_type,
                    user_message,
                    st.session_state.current_user_profile,
                    {
                        "session_id": st.session_state.current_session.session_id if st.session_state.current_session else None,
                        "conversation_history": st.session_state.current_session.conversation_history if st.session_state.current_session else []
                    }
                )
            )
            loop.close()
            
            # Get agent info for voice and display
            agent_info = getattr(AgentPersonalities, agent_type.value.upper())
            
            # Display response with voice integration
            st.markdown("### Agent Response:")
            render_voice_message(
                text=response['response'],
                agent_type=agent_type.value,
                agent_info=agent_info
            )
            
            # Update conversation history
            interaction = {
                "user_message": user_message,
                "agent_response": response['response'],
                "timestamp": datetime.now().isoformat(),
                "metadata": response.get('metadata', {}),
                "voice_url": response.get('voice_url'),
                "cultural_elements": response.get('cultural_elements', [])
            }
            
            if st.session_state.current_session:
                st.session_state.current_session.conversation_history.append(interaction)
                st.session_state.current_session.updated_at = datetime.now()
            
            # Clear input
            st.session_state[f"input_{agent_type.value}"] = ""
            
        except Exception as e:
            st.error(f"Error communicating with agent: {e}")
            logger.error(f"Agent interaction error: {e}")

def show_session_analytics(agent_type: AgentType):
    """Show session analytics and insights"""
    
    if not st.session_state.current_session:
        st.warning("No active session to analyze")
        return
    
    st.subheader(f"📊 Session Analytics - {agent_type.value.title()}")
    
    # Basic stats
    history = st.session_state.current_session.conversation_history
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Messages", len(history))
    
    with col2:
        total_words = sum(len(msg['user_message'].split()) + len(msg['agent_response'].split()) for msg in history)
        st.metric("Total Words", total_words)
    
    with col3:
        if history:
            session_duration = (datetime.now() - st.session_state.current_session.created_at).seconds // 60
            st.metric("Duration (min)", session_duration)
    
    with col4:
        st.metric("Relationship", f"{st.session_state.current_session.relationship_depth:.1f}")
    
    # Conversation timeline
    if history:
        st.subheader("💬 Conversation Timeline")
        for i, msg in enumerate(history[-5:], 1):  # Last 5 messages
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M")
            st.markdown(f"**{timestamp}** - Message {i}")

def render_session_history():
    """Render session history page"""
    
    st.title("📊 Session History")
    
    if not st.session_state.current_user_profile:
        st.warning("Please set up your profile to view session history")
        return
    
    # Get user sessions
    sessions = st.session_state.db_manager.get_user_sessions(st.session_state.current_user_profile.user_id)
    
    if not sessions:
        st.info("No previous sessions found. Start chatting with an agent to create your first session!")
        return
    
    st.markdown(f"**Found {len(sessions)} sessions**")
    
    # Display sessions
    for session in sessions:
        with st.expander(f"Session with {session['active_agent'].title()} - {session['updated_at']}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Agent:** {session['active_agent'].title()}")
            
            with col2:
                st.markdown(f"**Created:** {session['created_at']}")
            
            with col3:
                st.markdown(f"**Last Updated:** {session['updated_at']}")
            
            if st.button(f"Load Session", key=f"load_{session['session_id']}"):
                # Load session logic here
                st.info("Session loading feature coming soon!")

def render_settings():
    """Render settings and configuration page"""
    
    st.title("⚙️ Settings & Configuration")
    
    # System settings
    st.subheader("🔧 System Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.checkbox("🎤 Enable Voice Features", value=st.session_state.voice_enabled, key="settings_voice")
        st.checkbox("📹 Enable Video Features", value=st.session_state.video_enabled, key="settings_video")
        st.checkbox("🇮🇳 Hindi Mode Default", value=st.session_state.hindi_mode, key="settings_hindi")
    
    with col2:
        backend_url = st.text_input("Backend URL", value="http://localhost:8001")
        if st.button("🔄 Update Backend URL"):
            st.session_state.backend_communicator.base_url = backend_url
            st.success("Backend URL updated!")
    
    # Cultural preferences
    st.subheader("🎭 Cultural Preferences")
    
    cultural_regions = {
        "north": "North India (Hindi belt)",
        "south": "South India (Dravidian languages)",
        "east": "East India (Bengali culture)",
        "west": "West India (Marathi, Gujarati)",
        "northeast": "Northeast India (Tribal cultures)"
    }
    
    selected_region = st.selectbox("Primary Cultural Region", 
                                  options=list(cultural_regions.keys()),
                                  format_func=lambda x: cultural_regions[x])
    
    # Festival preferences
    festivals_by_region = {
        "north": ["Diwali", "Holi", "Karva Chauth", "Dussehra"],
        "south": ["Pongal", "Onam", "Ugadi", "Diwali"],
        "east": ["Durga Puja", "Kali Puja", "Poila Boishakh"],
        "west": ["Ganesh Chaturthi", "Navratri", "Gudi Padwa"],
        "northeast": ["Bihu", "Wangala", "Hornbill Festival"]
    }
    
    if selected_region in festivals_by_region:
        st.multiselect("Festivals You Celebrate", festivals_by_region[selected_region])
    
    # Data management
    st.subheader("💾 Data Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Export Data"):
            st.info("Data export feature coming soon!")
    
    with col2:
        if st.button("🗑️ Clear History"):
            if st.checkbox("I understand this will delete all my data"):
                st.warning("Are you sure? This action cannot be undone!")
    
    with col3:
        if st.button("🔄 Reset Settings"):
            # Reset logic here
            st.info("Settings reset feature coming soon!")

def main():
    """Main application entry point"""
    
    # Initialize voice system
    init_voice_system()
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar with voice controls
    render_sidebar()
    
    # Route to appropriate page
    if st.session_state.current_page == "global_selector":
        render_global_agent_selector()
    
    elif st.session_state.current_page == "mitra_agent":
        render_agent_page(AgentType.MITRA)
    
    elif st.session_state.current_page == "guru_agent":
        render_agent_page(AgentType.GURU)
    
    elif st.session_state.current_page == "parikshak_agent":
        render_agent_page(AgentType.PARIKSHAK)
    
    elif st.session_state.current_page == "session_history":
        render_session_history()
    
    elif st.session_state.current_page == "settings":
        render_settings()
    
    # Footer
    st.markdown("---")
    st.markdown("🇮🇳 **BuddyAgents India** - Next-Generation AI Companions for Indian Users")

if __name__ == "__main__":
    main()
