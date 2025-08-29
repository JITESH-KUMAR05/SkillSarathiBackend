"""
Voice Configuration for BuddyAgents
===================================

Defines voice settings and agent voice mappings for the Murf AI TTS system.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Voice configurations for Indian agents with validated Murf voice IDs
AGENT_VOICE_CONFIG = {
    "mitra": {
        "primary": "hi-IN-shweta",
        "voice_id": "hi-IN-shweta",
        "language": "Hindi",
        "gender": "Female",
        "description": "Warm, caring friend voice in Hindi",
        "personality": "supportive, empathetic, encouraging",
        "use_case": "Personal development and emotional support"
    },
    "guru": {
        "primary": "en-IN-eashwar",
        "voice_id": "en-IN-eashwar", 
        "language": "English (India)",
        "gender": "Male",
        "description": "Professional, knowledgeable teacher voice",
        "personality": "authoritative, patient, educational",
        "use_case": "Learning and skill development"
    },
    "parikshak": {
        "primary": "en-IN-isha",
        "voice_id": "en-IN-isha",
        "language": "English (India)", 
        "gender": "Female",
        "description": "Clear, professional evaluator voice",
        "personality": "analytical, fair, constructive",
        "use_case": "Assessment and feedback"
    }
}

# Voice settings for TTS generation
VOICE_SETTINGS = {
    "speed": 1.0,
    "pitch": 0,
    "emphasis": "moderate",
    "format": "wav",
    "sample_rate": 44100
}

def get_agent_voice(agent_type: str) -> Dict[str, Any]:
    """
    Get voice configuration for a specific agent type.
    
    Args:
        agent_type: The agent type (mitra, guru, parikshak)
        
    Returns:
        Voice configuration dictionary
    """
    try:
        config = AGENT_VOICE_CONFIG.get(agent_type, AGENT_VOICE_CONFIG["mitra"])
        logger.info(f"🎵 Voice config for {agent_type}: {config['voice_id']} ({config['language']})")
        return config
    except Exception as e:
        logger.error(f"Failed to get voice config for {agent_type}: {e}")
        return AGENT_VOICE_CONFIG["mitra"]  # Fallback to Mitra

def get_voice_info(voice_id: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a specific voice ID.
    
    Args:
        voice_id: The Murf voice ID
        
    Returns:
        Voice information dictionary or None if not found
    """
    for agent, config in AGENT_VOICE_CONFIG.items():
        if config["voice_id"] == voice_id:
            return {
                "agent": agent,
                **config
            }
    return None

def validate_voice_config() -> bool:
    """
    Validate that all required voice configurations are present.
    
    Returns:
        True if all configurations are valid
    """
    required_agents = ["mitra", "guru", "parikshak"]
    required_fields = ["voice_id", "language", "gender", "description"]
    
    for agent in required_agents:
        if agent not in AGENT_VOICE_CONFIG:
            logger.error(f"❌ Missing voice config for agent: {agent}")
            return False
            
        config = AGENT_VOICE_CONFIG[agent]
        for field in required_fields:
            if field not in config:
                logger.error(f"❌ Missing field '{field}' in config for agent: {agent}")
                return False
    
    logger.info("✅ Voice configuration validation passed")
    return True

# Export main components
__all__ = [
    "AGENT_VOICE_CONFIG", 
    "VOICE_SETTINGS",
    "get_agent_voice",
    "get_voice_info", 
    "validate_voice_config"
]
