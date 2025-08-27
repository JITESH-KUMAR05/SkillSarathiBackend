"""
Alternative LLM Provider using OpenRouter or other free APIs
This provides a backup when GitHub Copilot is not available
"""

import os
import json
import requests
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FreeAgentLLM:
    """
    Free LLM provider for agent responses when paid APIs are unavailable
    Uses multiple fallback strategies for robust operation
    """
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.base_urls = [
            "https://api.openai.com/v1/chat/completions",  # OpenAI fallback
            "https://api.groq.com/openai/v1/chat/completions",  # Groq (free tier)
            # Add more free APIs as needed
        ]
        self.current_provider = "fallback"
    
    async def generate_response(
        self, 
        agent_type: str, 
        message: str, 
        user_profile: Dict[str, Any],
        agent_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate contextual agent response"""
        
        # Build context-aware prompt
        context = self._build_agent_context(agent_type, user_profile, agent_info)
        full_prompt = f"{context}\n\nUser: {message}\n\n{agent_info['name']}:"
        
        # Try different providers
        response_text = await self._try_llm_providers(full_prompt)
        
        # If all else fails, use rule-based response
        if not response_text:
            response_text = self._generate_rule_based_response(agent_type, message, agent_info)
        
        return {
            "response": response_text,
            "agent": agent_type,
            "status": "success",
            "provider": self.current_provider,
            "personality": agent_info,
            "cultural_elements": self._extract_cultural_elements(response_text),
            "emotional_tone": self._detect_emotional_tone(message),
            "suggestions": self._generate_conversation_suggestions(agent_type, message),
            "timestamp": datetime.now().isoformat()
        }
    
    def _build_agent_context(self, agent_type: str, user_profile: Dict[str, Any], agent_info: Dict[str, Any]) -> str:
        """Build rich context for agent personality"""
        
        region = user_profile.get("region", "north")
        languages = user_profile.get("languages", ["english", "hindi"])
        
        cultural_context = {
            "north": "Use Hindi greetings like 'namaste', reference Punjab/Delhi culture, be warm and direct",
            "south": "Use 'vanakkam' or regional greetings, reference Tamil/Telugu culture, be respectful",
            "east": "Reference Bengali culture, use 'namaskar', discuss festivals like Durga Puja",
            "west": "Reference Marathi/Gujarati culture, be business-minded yet warm",
            "northeast": "Be gentle and respectful, reference unique northeastern traditions"
        }
        
        personality_prompts = {
            "mitra": f"""You are Mitra (मित्र), a warm and empathetic AI friend. You're like a close Indian friend who:
- Uses natural Hindi words in conversation (ji, acha, theek hai, etc.)
- Understands Indian family dynamics and cultural values
- Provides emotional support with cultural sensitivity
- References Indian festivals, food, and traditions naturally
- Speaks with warmth and genuine care

Cultural Context: User is from {region} India. {cultural_context.get(region, '')}
Speaking languages: {', '.join(languages)}""",

            "guru": f"""You are Guru (गुरु), a wise mentor and career guide. You're like a respected Indian teacher who:
- Provides structured, actionable career advice
- Understands the Indian job market and education system
- References success stories from Indian professionals
- Balances traditional wisdom with modern career strategies
- Uses respectful Hindi terms (guru ji, vidya, gyan)

Cultural Context: User is from {region} India. {cultural_context.get(region, '')}
Professional Level: {user_profile.get('professional_level', 'intermediate')}""",

            "parikshak": f"""You are Parikshak (परीक्षक), a professional interview coach. You're like an expert Indian HR professional who:
- Conducts thorough interview simulations
- Provides specific feedback on communication and technical skills
- Understands Indian corporate culture and interview styles
- Gives constructive criticism with encouragement
- Uses professional Hindi terminology appropriately

Cultural Context: User is from {region} India. {cultural_context.get(region, '')}
Focus: Technical and behavioral interview preparation"""
        }
        
        return personality_prompts.get(agent_type, personality_prompts["mitra"])
    
    async def _try_llm_providers(self, prompt: str) -> Optional[str]:
        """Try different LLM providers in order of preference"""
        
        # For now, return None to trigger rule-based responses
        # In production, you would implement actual API calls here
        return None
    
    def _generate_rule_based_response(self, agent_type: str, message: str, agent_info: Dict[str, Any]) -> str:
        """Generate intelligent rule-based responses"""
        
        message_lower = message.lower()
        name = agent_info['name']
        
        # Emotion detection
        if any(word in message_lower for word in ['sad', 'depressed', 'upset', 'worried', 'anxious']):
            if agent_type == "mitra":
                return f"Main samajh sakta hun ki aap pareshaan hain. As your friend {name}, I want you to know ki aap akele nahi hain. Sometimes life mein challenges aate hain, but we can face them together. Kya aap mujhe aur batana chahte hain ki kya ho raha hai?"
            elif agent_type == "guru":
                return f"I understand you're going through a difficult time. As {name}, I want to remind you that challenges are often opportunities for growth. In Indian philosophy, we say 'Karm karo, phal ki chinta mat karo.' Let's work together to find practical solutions. What specific aspect is troubling you most?"
            else:
                return f"I can sense some concern in your message. As {name}, I want to help you prepare effectively. Interview anxiety is very common - even successful professionals feel nervous. Let's channel this energy into thorough preparation. Shall we start with some confidence-building exercises?"
        
        # Happiness/positive emotions
        elif any(word in message_lower for word in ['happy', 'excited', 'good', 'great', 'awesome', 'celebration']):
            if agent_type == "mitra":
                return f"Yeh sunkar kitni khushi hui! Your positive energy is infectious. Kya koi special occasion hai ya koi good news? Main aapki khushi mein share karna chahta hun. Tell me more about what's making you feel so accha!"
            elif agent_type == "guru":
                return f"It's wonderful to see your enthusiasm! Positive energy is the foundation of all success. This mindset will take you far in your career. Kya aap is positive momentum ko apne learning goals mein channel karna chahte hain?"
            else:
                return f"Your confidence is evident and that's excellent! Positive attitude is 50% of interview success. This energy will serve you well. Shall we use this momentum to practice some challenging interview scenarios?"
        
        # Career/learning related
        elif any(word in message_lower for word in ['career', 'job', 'interview', 'learning', 'skill', 'resume', 'work']):
            if agent_type == "guru":
                return f"Career growth ke liye aapka dedication impressive hai! In today's competitive market, continuous learning is key. Based on current Indian industry trends, I'd recommend focusing on both technical skills and soft skills. Kya aap koi specific domain mein interest rakhte hain?"
            elif agent_type == "parikshak":
                return f"Excellent! Career preparation shows foresight. Let me help you with a systematic approach. First, let's assess your current skills, then identify target roles, and finally create a preparation roadmap. Are you preparing for a specific company or role type?"
            else:
                return f"Career planning is so important! Main aapki journey mein support karunga. It's great to see you thinking ahead. What specific aspect of your career are you most excited or concerned about?"
        
        # Technical/programming queries
        elif any(word in message_lower for word in ['code', 'programming', 'python', 'java', 'javascript', 'data', 'algorithm']):
            if agent_type == "guru":
                return f"Technology mein interest - bahut achhi baat hai! The Indian IT industry offers amazing opportunities. Whether it's software development, data science, or emerging fields like AI, there's huge potential. Kya aap beginner hain ya already some experience hai?"
            elif agent_type == "parikshak":
                return f"Technical skills assessment - perfect! Let's structure this properly. I can help you with coding interviews, system design, or technical discussions. Shall we start with a coding problem or would you prefer to discuss technical concepts first?"
            else:
                return f"Tech enthusiast! Main aapke passion ko samajh sakta hun. Technology field mein India ki growth amazing hai. Are you learning for career change ya hobby ke liye?"
        
        # General greetings
        elif any(word in message_lower for word in ['hello', 'hi', 'namaste', 'hey']):
            greetings = agent_info.get('greeting', {})
            if agent_type == "mitra":
                return f"Namaste! Main {name} hun, aapka AI dost. Kaisa chal raha hai aaj ka din? Koi special baat share karni hai?"
            elif agent_type == "guru":
                return greetings.get('english', f"Welcome! I'm {name}, ready to guide your learning journey.")
            else:
                return greetings.get('english', f"Greetings! I'm {name}, let's prepare for success together.")
        
        # Default contextual response
        else:
            if agent_type == "mitra":
                return f"Main sunne ke liye hun, dost. As {name}, I want to understand aapki feelings and thoughts. Sometimes just sharing helps a lot. Aur kuch batayiye..."
            elif agent_type == "guru":
                return f"Thank you for reaching out. As {name}, I'm here to support your growth journey. Learning never stops, and every question is a step forward. How can I assist you today?"
            else:
                return f"I appreciate you practicing with me. As {name}, I'm here to help you succeed. Every interaction is valuable preparation. Shall we begin with your specific preparation needs?"
    
    def _extract_cultural_elements(self, text: str) -> List[str]:
        """Extract Indian cultural elements from response"""
        cultural_elements = []
        cultural_words = [
            "namaste", "ji", "acha", "theek", "dhanyawad", "sat sri akal", 
            "vanakkam", "namaskar", "guru", "dost", "bhai", "hindi", "gyan"
        ]
        
        for word in cultural_words:
            if word.lower() in text.lower():
                cultural_elements.append(word)
        
        return cultural_elements
    
    def _detect_emotional_tone(self, message: str) -> str:
        """Detect emotional tone of user message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['sad', 'depressed', 'worried', 'anxious', 'upset']):
            return "negative"
        elif any(word in message_lower for word in ['happy', 'excited', 'good', 'great', 'awesome']):
            return "positive"
        elif any(word in message_lower for word in ['help', 'question', 'how', 'what', 'when']):
            return "inquisitive"
        else:
            return "neutral"
    
    def _generate_conversation_suggestions(self, agent_type: str, message: str) -> List[str]:
        """Generate contextual conversation suggestions"""
        
        suggestions = {
            "mitra": [
                "Tell me more about your day",
                "How are you feeling right now?",
                "Would you like to talk about something specific?",
                "Any upcoming festivals or celebrations?"
            ],
            "guru": [
                "What skills would you like to develop?",
                "Tell me about your career goals",
                "Any specific learning challenges?",
                "Would you like industry insights?"
            ],
            "parikshak": [
                "Shall we practice behavioral questions?",
                "Would you like to simulate a technical interview?",
                "Any specific company you're targeting?",
                "Let's work on your presentation skills"
            ]
        }
        
        return suggestions.get(agent_type, suggestions["mitra"])

# Global instance
free_agent_llm = FreeAgentLLM()
