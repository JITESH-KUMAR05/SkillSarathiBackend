"""
Configuration management for BuddyAgents Streamlit frontend.
"""

import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings


class FrontendConfig(BaseSettings):
    """Frontend configuration settings"""
    
    # API Configuration
    BACKEND_URL: str = "http://localhost:8000"
    WEBSOCKET_URL: str = "ws://localhost:8000"
    HEALTH_ENDPOINT: str = "/health"
    AGENTS_ENDPOINT: str = "/agents"
    CHAT_ENDPOINT: str = "/api/chat/send"
    VOICE_ENDPOINT: str = "/api/chat/voice/generate"
    
    # App Settings
    APP_TITLE: str = "🙏 BuddyAgents - Your AI Companions"
    APP_VERSION: str = "1.0.0"
    
    # Theme and UI Settings
    DEFAULT_THEME: str = "light"
    SIDEBAR_EXPANDED: bool = True
    
    # Additional Environment Variables
    DEBUG: bool = True
    API_TIMEOUT: int = 30
    MURF_API_KEY: str = ""
    MURF_API_URL: str = "https://api.murf.ai/v1"
    STUN_SERVER: str = "stun:stun.l.google.com:19302"
    
    # Voice Configuration
    VOICE_ENABLED: bool = True
    DEFAULT_VOICE: str = "aditi"
    VOICE_SPEED: int = 0
    
    # Video Settings
    VIDEO_ENABLED: bool = True
    VIDEO_RESOLUTION: str = "720p"
    VIDEO_FPS: int = 30
    
    # Session Settings
    SESSION_TIMEOUT_MINUTES: int = 30
    MAX_CONVERSATION_LENGTH: int = 50
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    
    model_config = {
        "env_file": ".env",
        "env_ignore_empty": True,
        "extra": "allow"
    }

# Agent Configuration - defined separately to avoid pydantic issues
AGENTS = {
    "mitra": {
        "name": "Mitra (मित्र)",
        "emoji": "🤗",
        "description": "Your caring friend for emotional support",
        "color": "#FF6B6B",
        "role": "friend"
    },
    "guru": {
        "name": "Guru (गुरु)", 
        "emoji": "🎓",
        "description": "Your learning mentor for growth",
        "color": "#4ECDC4",
        "role": "mentor"
    },
    "parikshak": {
        "name": "Parikshak (परीक्षक)",
        "emoji": "💼", 
        "description": "Your interview coach for career success",
        "color": "#45B7D1",
        "role": "coach"
    }
}

# Global configuration instance
config = FrontendConfig()

# Agent helper functions
def get_agent_config(agent_type: str) -> Optional[Dict[str, str]]:
    """Get configuration for a specific agent"""
    return AGENTS.get(agent_type)

def get_all_agents() -> Dict[str, Dict[str, str]]:
    """Get all agent configurations"""
    return AGENTS

def get_agent_names() -> List[str]:
    """Get list of all agent names"""
    return list(AGENTS.keys())

def get_agent_by_emoji(emoji: str) -> Optional[str]:
    """Get agent type by emoji"""
    for agent_type, agent_config in AGENTS.items():
        if agent_config["emoji"] == emoji:
            return agent_type
    return None

# Voice configuration
AVAILABLE_VOICES = {
    # Hindi voices
    "aditi": {"name": "Aditi", "language": "Hindi", "gender": "Female", "age": "Young Adult"},
    "kabir": {"name": "Kabir", "language": "Hindi", "gender": "Male", "age": "Young Adult"},
    "neerja": {"name": "Neerja", "language": "Hindi", "gender": "Female", "age": "Middle Aged"},
    "radhika": {"name": "Radhika", "language": "Hindi", "gender": "Female", "age": "Young Adult"},
    "saanvi": {"name": "Saanvi", "language": "Hindi", "gender": "Female", "age": "Young Adult"},
    "tarun": {"name": "Tarun", "language": "Hindi", "gender": "Male", "age": "Young Adult"},
    
    # English-India voices
    "alisha": {"name": "Alisha", "language": "English-India", "gender": "Female", "age": "Young Adult"},
    "arnav": {"name": "Arnav", "language": "English-India", "gender": "Male", "age": "Young Adult"},
    "kavya": {"name": "Kavya", "language": "English-India", "gender": "Female", "age": "Young Adult"},
    "priya": {"name": "Priya", "language": "English-India", "gender": "Female", "age": "Young Adult"},
    "rahul": {"name": "Rahul", "language": "English-India", "gender": "Male", "age": "Young Adult"},
    "ravi": {"name": "Ravi", "language": "English-India", "gender": "Male", "age": "Middle Aged"},
    "sneha": {"name": "Sneha", "language": "English-India", "gender": "Female", "age": "Young Adult"},
    
    # Bengali voices
    "aarohi": {"name": "Aarohi", "language": "Bengali", "gender": "Female", "age": "Young Adult"},
    "agni": {"name": "Agni", "language": "Bengali", "gender": "Male", "age": "Young Adult"},
    "anwesha": {"name": "Anwesha", "language": "Bengali", "gender": "Female", "age": "Young Adult"},
    "binita": {"name": "Binita", "language": "Bengali", "gender": "Female", "age": "Middle Aged"},
    
    # Tamil voices
    "dharini": {"name": "Dharini", "language": "Tamil", "gender": "Female", "age": "Young Adult"},
    "rajan": {"name": "Rajan", "language": "Tamil", "gender": "Male", "age": "Young Adult"},
    "shruthi": {"name": "Shruthi", "language": "Tamil", "gender": "Female", "age": "Young Adult"},
    "valluvar": {"name": "Valluvar", "language": "Tamil", "gender": "Male", "age": "Middle Aged"}
}
