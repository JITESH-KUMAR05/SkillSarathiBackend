"""
Session Management for BuddyAgents
==================================

Handles user sessions, preferences, and conversation history.
"""

import streamlit as st
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

class SessionManager:
    """Manages user sessions and preferences"""
    
    def __init__(self):
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        
        # User identification
        if "user_id" not in st.session_state:
            st.session_state.user_id = str(uuid.uuid4())
        
        # Session IDs for backend communication
        if "session_ids" not in st.session_state:
            st.session_state.session_ids = {
                "mitra": f"session_{uuid.uuid4().hex[:8]}",
                "guru": f"session_{uuid.uuid4().hex[:8]}",
                "parikshak": f"session_{uuid.uuid4().hex[:8]}"
            }
        
        # Current agent
        if "current_agent" not in st.session_state:
            st.session_state.current_agent = "mitra"
        
        # Conversation history per agent
        if "conversations" not in st.session_state:
            st.session_state.conversations = {
                "mitra": [],
                "guru": [],
                "parikshak": []
            }
        
        # User preferences
        if "preferences" not in st.session_state:
            st.session_state.preferences = {
                "theme": "light",
                "voice_enabled": True,
                "voice_speed": 1.0,
                "voice_pitch": 1.0,
                "language": "en-IN",
                "auto_play_voice": True,
                "show_typing_indicator": True
            }
        
        # User profile
        if "user_profile" not in st.session_state:
            st.session_state.user_profile = None
        
        # Authentication
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        
        # Interview session state
        if "interview_session" not in st.session_state:
            st.session_state.interview_session = {
                "active": False,
                "start_time": None,
                "questions": [],
                "responses": [],
                "current_question": 0
            }
    
    def set_current_agent(self, agent: str):
        """Set the current agent"""
        st.session_state.current_agent = agent
    
    def get_current_agent(self) -> str:
        """Get the current agent"""
        return st.session_state.get("current_agent", "mitra")
    
    def get_session_id(self, agent: str) -> str:
        """Get the session ID for a specific agent"""
        self.init_session_state()
        return st.session_state.session_ids.get(agent, f"session_{uuid.uuid4().hex[:8]}")
    
    def store_session_id(self, agent: str, session_id: str):
        """Store session ID for an agent"""
        self.init_session_state()
        st.session_state.session_ids[agent] = session_id
    
    def regenerate_session_id(self, agent: str) -> str:
        """Generate a new session ID for an agent"""
        new_session_id = f"session_{uuid.uuid4().hex[:8]}"
        st.session_state.session_ids[agent] = new_session_id
        return new_session_id
    
    def add_message(self, agent: str, role: str, content: str, timestamp: Optional[datetime] = None):
        """Add a message to conversation history"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Ensure conversations is initialized
        self.init_session_state()
        
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat(),
            "agent": agent
        }
        
        if agent in st.session_state.conversations:
            st.session_state.conversations[agent].append(message)
            
            # Limit conversation length
            max_length = 50
            if len(st.session_state.conversations[agent]) > max_length:
                st.session_state.conversations[agent] = st.session_state.conversations[agent][-max_length:]
    
    def get_conversation_history(self, agent: str) -> List[Dict[str, Any]]:
        """Get conversation history for an agent"""
        # Ensure conversations is initialized
        self.init_session_state()
        return st.session_state.conversations.get(agent, [])
    
    def clear_conversation(self, agent: str):
        """Clear conversation history for an agent"""
        self.init_session_state()
        if agent in st.session_state.conversations:
            st.session_state.conversations[agent] = []
    
    def set_preference(self, key: str, value: Any):
        """Set a user preference"""
        self.init_session_state()
        st.session_state.preferences[key] = value
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference"""
        self.init_session_state()
        return st.session_state.preferences.get(key, default)
    
    def update_preference(self, key: str, value: Any):
        """Update a user preference (alias for set_preference)"""
        self.set_preference(key, value)
    
    def set_user_profile(self, name: str, email: str):
        """Set user profile information"""
        st.session_state.user_profile = {
            "name": name,
            "email": email,
            "created_at": datetime.now().isoformat()
        }
        st.session_state.authenticated = True
    
    def get_user_profile(self) -> Optional[Dict[str, str]]:
        """Get user profile information"""
        return st.session_state.get("user_profile")
    
    def get_user_id(self) -> str:
        """Get the current user ID"""
        self.init_session_state()
        return st.session_state.get("user_id", "")
    
    def logout(self):
        """Logout user and clear profile"""
        st.session_state.user_profile = None
        st.session_state.authenticated = False
    
    def start_interview_session(self):
        """Start an interview session"""
        st.session_state.interview_session = {
            "active": True,
            "start_time": datetime.now().isoformat(),
            "questions": [],
            "responses": [],
            "current_question": 0
        }
    
    def end_interview_session(self):
        """End an interview session"""
        if "interview_session" in st.session_state:
            st.session_state.interview_session["active"] = False
    
    def get_session_stats(self):
        """Get session statistics"""
        self.init_session_state()
        
        total_messages = 0
        agents_used = []
        
        for agent, messages in st.session_state.conversations.items():
            if messages:
                agents_used.append(agent)
                total_messages += len(messages)
        
        return {
            "user_id": st.session_state.get("user_id", ""),
            "current_agent": self.get_current_agent(),
            "authenticated": st.session_state.get("authenticated", False),
            "total_messages": total_messages,
            "agents_used": agents_used,
            "preferences": st.session_state.get("preferences", {})
        }

# Global session manager instance
session_manager = SessionManager()
