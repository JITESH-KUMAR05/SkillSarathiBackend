"""
Enhanced Multi-Agent Backend Integration
======================================

Integrates with existing FastAPI backend and provides enhanced agent routing,
cultural intelligence, and real-time processing capabilities using GitHub LLM.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import from existing backend
try:
    from app.agents.multi_agent_system import MultiAgentOrchestrator
    from app.llm.github_llm import GitHubLLM
    from app.rag.enhanced_rag_system import EnhancedRAGSystem
    from app.core.config import get_settings
    BACKEND_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import existing backend modules: {e}")
    BACKEND_AVAILABLE = False

logger = logging.getLogger(__name__)

# ================================
# ENHANCED MODELS
# ================================

class AgentType(str, Enum):
    MITRA = "mitra"
    GURU = "guru" 
    PARIKSHAK = "parikshak"

class CulturalContext(BaseModel):
    region: str = Field(default="north", description="Indian region")
    languages: List[str] = Field(default=["english", "hindi"])
    festivals: List[str] = Field(default_factory=list)
    communication_style: str = Field(default="formal")
    family_structure: str = Field(default="joint")

class UserProfileRequest(BaseModel):
    user_id: str
    name: str
    region: str = "north"
    languages: List[str] = ["english", "hindi"]
    professional_level: str = "intermediate"
    interests: List[str] = []
    cultural_preferences: Dict[str, Any] = {}

class AgentMessage(BaseModel):
    agent: AgentType
    message: str
    user_profile: UserProfileRequest
    session_context: Optional[Dict[str, Any]] = None
    cultural_context: Optional[CulturalContext] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentResponse(BaseModel):
    response: str
    agent: AgentType
    personality_info: Dict[str, Any]
    cultural_elements: List[str] = []
    emotional_tone: str = "neutral"
    suggestions: List[str] = []
    voice_url: Optional[str] = None
    status: str = "success"
    timestamp: datetime = Field(default_factory=datetime.now)

# ================================
# ENHANCED AGENT PERSONALITIES
# ================================

class EnhancedAgentPersonalities:
    """Enhanced agent personalities with cultural intelligence"""
    
    @staticmethod
    def get_mitra_personality(cultural_context: CulturalContext) -> Dict[str, Any]:
        """Get Mitra personality adapted to cultural context"""
        
        base_personality = {
            "name": "Mitra",
            "hindi_name": "मित्र", 
            "role": "Empathetic AI Companion",
            "core_traits": ["empathetic", "warm", "supportive", "culturally_aware"],
            "communication_style": "conversational",
            "emotional_intelligence": 0.95
        }
        
        # Regional adaptations
        regional_adaptations = {
            "north": {
                "greetings": ["namaste", "sat sri akal"],
                "expressions": ["kya haal hai", "sab theek"],
                "cultural_refs": ["punjabi_warmth", "delhi_friendliness"]
            },
            "south": {
                "greetings": ["vanakkam", "namaste"],
                "expressions": ["eppadi irukeenga", "yella chennagide"],
                "cultural_refs": ["tamil_hospitality", "south_respect"]
            },
            "east": {
                "greetings": ["namaskar", "adaab"],
                "expressions": ["kemon acho", "bhalo thakben"],
                "cultural_refs": ["bengali_culture", "intellectual_talks"]
            },
            "west": {
                "greetings": ["namaste", "kemcho"],
                "expressions": ["kay challay", "kasa kay"],
                "cultural_refs": ["marathi_pride", "gujarati_warmth"]
            }
        }
        
        if cultural_context.region in regional_adaptations:
            base_personality.update(regional_adaptations[cultural_context.region])
        
        return base_personality
    
    @staticmethod
    def get_guru_personality(cultural_context: CulturalContext) -> Dict[str, Any]:
        """Get Guru personality adapted to cultural context"""
        
        return {
            "name": "Guru",
            "hindi_name": "गुरु",
            "role": "Career & Learning Mentor",
            "core_traits": ["knowledgeable", "patient", "structured", "motivational"],
            "communication_style": "educational",
            "expertise_areas": [
                "technical_skills", "career_planning", "interview_prep",
                "indian_job_market", "skill_development", "leadership"
            ],
            "teaching_philosophy": "progressive_learning",
            "cultural_wisdom": "traditional_yet_modern"
        }
    
    @staticmethod
    def get_parikshak_personality(cultural_context: CulturalContext) -> Dict[str, Any]:
        """Get Parikshak personality adapted to cultural context"""
        
        return {
            "name": "Parikshak", 
            "hindi_name": "परीक्षक",
            "role": "Technical Interview Specialist",
            "core_traits": ["professional", "thorough", "fair", "constructive"],
            "communication_style": "structured_assessment",
            "assessment_areas": [
                "technical_knowledge", "problem_solving", "communication_skills",
                "cultural_fit", "leadership_potential", "adaptability"
            ],
            "evaluation_approach": "holistic_assessment",
            "feedback_style": "constructive_detailed"
        }

# ================================
# ENHANCED BACKEND SERVICE
# ================================

class EnhancedMultiAgentService:
    """Enhanced multi-agent service with cultural intelligence"""
    
    def __init__(self):
        self.llm = None
        self.rag_system = None
        self.orchestrator = None
        self.initialize_services()
    
    def initialize_services(self):
        """Initialize backend services"""
        try:
            if BACKEND_AVAILABLE:
                # Get GitHub token from environment
                github_token = os.getenv("GITHUB_TOKEN")
                if not github_token:
                    raise ValueError("GITHUB_TOKEN not found in environment")
                
                # Initialize services
                self.rag_system = EnhancedRAGSystem()
                self.llm = GitHubLLM(github_token=github_token)
                self.orchestrator = MultiAgentOrchestrator(self.rag_system)
                logger.info("✅ Initialized with existing backend services using GitHub LLM")
            else:
                raise ImportError("Backend not available")
        except Exception as e:
            logger.warning(f"Could not initialize existing services: {e}")
            # Initialize fallback services
            self.initialize_fallback_services()
    
    def initialize_fallback_services(self):
        """Initialize fallback services when main backend is unavailable"""
        logger.info("🔄 Initializing fallback services")
        # Fallback implementation would go here
    
    async def process_agent_message(self, message: AgentMessage) -> AgentResponse:
        """Process message through appropriate agent"""
        
        # Build cultural context
        cultural_context = message.cultural_context or CulturalContext(
            region=message.user_profile.region,
            languages=message.user_profile.languages
        )
        
        # Get agent personality
        personality = self.get_agent_personality(message.agent, cultural_context)
        
        # Process through backend
        try:
            if self.orchestrator:
                response_text = await self.process_with_orchestrator(message)
            else:
                response_text = await self.process_with_fallback(message, personality)
            
            # Enhance response with cultural intelligence
            enhanced_response = self.enhance_response_culturally(response_text, cultural_context, personality)
            
            return AgentResponse(
                response=enhanced_response,
                agent=message.agent,
                personality_info=personality,
                cultural_elements=self.extract_cultural_elements(enhanced_response),
                emotional_tone=self.detect_emotional_tone(enhanced_response),
                suggestions=self.generate_suggestions(message.agent, enhanced_response),
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error processing agent message: {e}")
            return self.generate_error_response(message.agent, str(e))
    
    async def process_with_orchestrator(self, message: AgentMessage) -> str:
        """Process message using existing orchestrator"""
        
        if not self.orchestrator:
            raise Exception("Orchestrator not available")
        
        try:
            # Convert agent type to conversation ID format
            conversation_id = f"{message.user_profile.user_id}_{message.agent.value}_{int(datetime.now().timestamp())}"
            
            # Process through orchestrator with streaming
            response_parts = []
            async for chunk in self.orchestrator.process_message(
                user_id=message.user_profile.user_id,
                conversation_id=conversation_id,
                message=message.message,
                session_context=message.session_context
            ):
                if chunk:
                    response_parts.append(chunk)
            
            return "".join(response_parts) if response_parts else "I'm processing your request..."
            
        except Exception as e:
            logger.error(f"Orchestrator processing error: {e}")
            raise
    
    async def process_with_fallback(self, message: AgentMessage, personality: Dict[str, Any]) -> str:
        """Fallback processing when main backend is unavailable"""
        
        # Agent-specific fallback responses
        fallback_responses = {
            AgentType.MITRA: self.generate_mitra_fallback(message, personality),
            AgentType.GURU: self.generate_guru_fallback(message, personality),
            AgentType.PARIKSHAK: self.generate_parikshak_fallback(message, personality)
        }
        
        return fallback_responses.get(message.agent, "I'm here to help you!")
    
    def generate_mitra_fallback(self, message: AgentMessage, personality: Dict[str, Any]) -> str:
        """Generate Mitra fallback response"""
        
        user_message = message.message.lower()
        
        if any(word in user_message for word in ["sad", "upset", "stressed", "worried"]):
            return f"I can sense you're going through something difficult. As your friend {personality['name']}, I want you to know that I'm here for you. Sometimes just talking about what's bothering you can help. Would you like to share what's on your mind?"
        
        elif any(word in user_message for word in ["happy", "excited", "good", "great"]):
            return f"I'm so happy to hear the positivity in your message! It's wonderful when life gives us reasons to smile. Tell me more about what's making you feel so good today!"
        
        elif any(word in user_message for word in ["festival", "celebration", "diwali", "holi"]):
            return f"Festivals are such a beautiful part of our Indian culture! They bring families together and fill our hearts with joy. Are you celebrating? I'd love to hear about your preparations!"
        
        else:
            return f"Hello! I'm {personality['name']}, your AI friend. I'm here to chat, listen, and support you in whatever way I can. What would you like to talk about today?"
    
    def generate_guru_fallback(self, message: AgentMessage, personality: Dict[str, Any]) -> str:
        """Generate Guru fallback response"""
        
        user_message = message.message.lower()
        
        if any(word in user_message for word in ["career", "job", "work", "interview"]):
            return f"Career development is a journey, not a destination. As your mentor {personality['name']}, I'm here to guide you through this path. Whether it's skill building, interview preparation, or understanding the Indian job market, let's work together to achieve your professional goals. What specific area would you like to focus on?"
        
        elif any(word in user_message for word in ["learn", "study", "skill", "course"]):
            return f"Learning is the key to growth and success. I'm excited to help you on this educational journey! Whether you want to develop technical skills, improve soft skills, or explore new domains, I can provide structured guidance. What subject or skill are you most interested in developing?"
        
        elif any(word in user_message for word in ["confused", "direction", "path"]):
            return f"It's completely normal to feel uncertain about your path sometimes. That's where mentorship becomes valuable. Let's explore your interests, strengths, and goals together to find clarity. Tell me about your current situation and what you're hoping to achieve."
        
        else:
            return f"Welcome to your learning journey! I'm {personality['name']}, your career and learning mentor. I specialize in helping Indian professionals and students achieve their goals through structured guidance, skill development, and career planning. How can I help you grow today?"
    
    def generate_parikshak_fallback(self, message: AgentMessage, personality: Dict[str, Any]) -> str:
        """Generate Parikshak fallback response"""
        
        user_message = message.message.lower()
        
        if any(word in user_message for word in ["interview", "preparation", "practice"]):
            return f"Interview preparation is crucial for career success, especially in today's competitive market. As {personality['name']}, your interview specialist, I can help you practice technical questions, improve your communication skills, and build confidence. What type of interview are you preparing for - technical, behavioral, or both?"
        
        elif any(word in user_message for word in ["nervous", "anxious", "scared", "worried"]):
            return f"It's natural to feel nervous about interviews - even experienced professionals do! The key is turning that nervous energy into focused preparation. I'm here to help you practice systematically and build the confidence you need. Let's start with understanding what specific aspects make you feel anxious."
        
        elif any(word in user_message for word in ["feedback", "improve", "better"]):
            return f"Continuous improvement is the hallmark of successful professionals. I can provide detailed feedback on your responses, communication style, and technical approach. Would you like to practice answering some questions, or do you have specific areas you'd like me to evaluate?"
        
        else:
            return f"Greetings! I'm {personality['name']}, your professional interview coach and technical assessor. I specialize in helping candidates prepare for interviews through realistic practice sessions, detailed feedback, and skill assessment. Whether you're preparing for technical rounds, behavioral interviews, or leadership assessments, I'm here to help you succeed. How can we begin your preparation today?"
    
    def get_agent_personality(self, agent_type: AgentType, cultural_context: CulturalContext) -> Dict[str, Any]:
        """Get agent personality based on type and cultural context"""
        
        personality_getters = {
            AgentType.MITRA: EnhancedAgentPersonalities.get_mitra_personality,
            AgentType.GURU: EnhancedAgentPersonalities.get_guru_personality,
            AgentType.PARIKSHAK: EnhancedAgentPersonalities.get_parikshak_personality
        }
        
        return personality_getters[agent_type](cultural_context)
    
    def enhance_response_culturally(self, response: str, cultural_context: CulturalContext, personality: Dict[str, Any]) -> str:
        """Enhance response with cultural intelligence"""
        
        # Add regional expressions if appropriate
        if cultural_context.region == "north" and "hindi" in cultural_context.languages:
            if "good" in response.lower():
                response = response.replace("good", "accha")
            
        # Add cultural warmth
        if personality.get("core_traits") and "warm" in personality["core_traits"]:
            response = response.replace("Hello", "Namaste")
        
        return response
    
    def extract_cultural_elements(self, response: str) -> List[str]:
        """Extract cultural elements from response"""
        cultural_elements = []
        
        cultural_words = {
            "namaste": "traditional_greeting",
            "ji": "respectful_address", 
            "acha": "hindi_expression",
            "festival": "cultural_celebration",
            "family": "family_values"
        }
        
        for word, element in cultural_words.items():
            if word in response.lower():
                cultural_elements.append(element)
        
        return cultural_elements
    
    def detect_emotional_tone(self, response: str) -> str:
        """Detect emotional tone of response"""
        
        positive_words = ["happy", "excited", "wonderful", "great", "amazing"]
        supportive_words = ["understand", "support", "help", "here for you"]
        professional_words = ["assess", "evaluate", "feedback", "improve"]
        
        if any(word in response.lower() for word in positive_words):
            return "positive"
        elif any(word in response.lower() for word in supportive_words):
            return "supportive"
        elif any(word in response.lower() for word in professional_words):
            return "professional"
        else:
            return "neutral"
    
    def generate_suggestions(self, agent_type: AgentType, response: str) -> List[str]:
        """Generate follow-up suggestions based on agent and response"""
        
        suggestions = {
            AgentType.MITRA: [
                "Tell me more about your day",
                "How are you feeling right now?",
                "Would you like to talk about something specific?",
                "Any upcoming festivals or celebrations?"
            ],
            AgentType.GURU: [
                "What skills would you like to develop?",
                "Tell me about your career goals",
                "Need help with interview preparation?",
                "Want to explore learning opportunities?"
            ],
            AgentType.PARIKSHAK: [
                "Ready for a practice interview?",
                "Want feedback on your communication?",
                "Need help with technical questions?",
                "Shall we work on your presentation skills?"
            ]
        }
        
        return suggestions.get(agent_type, [])
    
    def generate_error_response(self, agent_type: AgentType, error_message: str) -> AgentResponse:
        """Generate error response"""
        
        error_responses = {
            AgentType.MITRA: "I'm experiencing some technical difficulties, but I'm still here for you as your friend. Please try again in a moment.",
            AgentType.GURU: "There seems to be a technical issue on my end. As your mentor, I apologize for the inconvenience. Let's try again shortly.",
            AgentType.PARIKSHAK: "I'm encountering a technical problem right now. As your interview coach, I want to ensure quality interaction. Please retry in a moment."
        }
        
        return AgentResponse(
            response=error_responses.get(agent_type, "Technical issue encountered. Please try again."),
            agent=agent_type,
            personality_info={},
            status="error"
        )

# ================================
# FASTAPI APPLICATION
# ================================

app = FastAPI(
    title="Enhanced Multi-Agent Backend",
    description="Production-grade multi-agent system for Indian AI companions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
agent_service = EnhancedMultiAgentService()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# ================================
# API ENDPOINTS
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "service": "enhanced_multi_agent_backend"
    }

@app.post("/api/agent/chat")
async def chat_with_agent(message: AgentMessage) -> AgentResponse:
    """Chat with specific agent"""
    
    try:
        response = await agent_service.process_agent_message(message)
        return response
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agent/personalities")
async def get_agent_personalities():
    """Get all agent personalities"""
    
    cultural_context = CulturalContext()  # Default context
    
    personalities = {}
    for agent_type in AgentType:
        personalities[agent_type.value] = agent_service.get_agent_personality(agent_type, cultural_context)
    
    return personalities

@app.websocket("/ws/agent/{agent_type}")
async def websocket_agent_chat(websocket: WebSocket, agent_type: str):
    """WebSocket endpoint for real-time agent chat"""
    
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Create agent message
            agent_message = AgentMessage(
                agent=AgentType(agent_type),
                message=message_data["message"],
                user_profile=UserProfileRequest(**message_data["user_profile"]),
                session_context=message_data.get("session_context"),
                cultural_context=CulturalContext(**message_data.get("cultural_context", {}))
            )
            
            # Process message
            response = await agent_service.process_agent_message(agent_message)
            
            # Send response back
            await manager.send_personal_message(response.json(), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.send_personal_message(
            json.dumps({"error": str(e)}), 
            websocket
        )

@app.post("/api/user/profile")
async def save_user_profile(profile: UserProfileRequest):
    """Save user profile"""
    
    # Here you would integrate with the database
    # For now, just return success
    return {
        "status": "success",
        "message": "Profile saved successfully",
        "user_id": profile.user_id
    }

@app.get("/api/user/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """Get user's conversation sessions"""
    
    # Here you would query the database for user sessions
    # For now, return empty list
    return {
        "user_id": user_id,
        "sessions": []
    }

if __name__ == "__main__":
    # Run the enhanced backend
    uvicorn.run(
        "enhanced_multi_agent_backend:app",
        host="0.0.0.0",
        port=8002,  # Different port to avoid conflicts
        reload=True,
        log_level="info"
    )
