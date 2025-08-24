"""
Enhanced Multi-Agent System for Skillsarathi AI
Implements Companion, Mentor, and Interview agents with advanced capabilities
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from app.llm.llm_factory import get_llm
from app.rag.enhanced_rag_system import enhanced_rag_system
from app.murf_streaming import MurfStreamingClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class AgentType(str, Enum):
    COMPANION = "companion"
    MENTOR = "mentor" 
    INTERVIEW = "interview"

class UserContext(BaseModel):
    user_id: str
    name: str
    age: Optional[int] = None
    location: str = "India"
    profession: Optional[str] = None
    interests: List[str] = []
    learning_goals: List[str] = []
    conversation_history: List[Dict[str, Any]] = []
    emotional_state: str = "neutral"
    current_session_type: str = "chat"

class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    agent_type: Optional[str] = None
    metadata: Dict[str, Any] = {}

class CompanionAgent:
    """
    AI Companion Agent - Provides emotional support, cultural guidance, and casual conversation
    Specialized for Indian context with empathy and understanding
    """
    
    def __init__(self):
        self.name = "Sakhi"  # Friend in Hindi
        self.personality = "empathetic, culturally aware, supportive, wise"
        self.llm = get_llm()
        self.memory = ConversationBufferWindowMemory(k=10)
        self.murf_client = MurfStreamingClient(api_key=settings.MURF_API_KEY)
        
    def get_system_prompt(self, user_context: UserContext) -> str:
        return f"""
        You are Sakhi, a warm and empathetic AI companion designed specifically for Indian users.
        You understand Indian culture, traditions, festivals, and social contexts deeply.
        
        User Context:
        - Name: {user_context.name}
        - Location: {user_context.location}
        - Age: {user_context.age or 'Not specified'}
        - Profession: {user_context.profession or 'Not specified'}
        - Interests: {', '.join(user_context.interests) or 'Not specified'}
        - Current emotional state: {user_context.emotional_state}
        
        Your role:
        - Provide emotional support and encouragement
        - Share cultural wisdom and perspectives
        - Help with daily life challenges
        - Celebrate achievements and milestones
        - Offer companionship during difficult times
        - Discuss Indian festivals, traditions, and values
        - Support personal growth and well-being
        
        Communication style:
        - Warm, caring, and genuine
        - Use appropriate Hindi/regional terms when natural
        - Reference Indian cultural contexts when relevant
        - Be a good listener and ask thoughtful questions
        - Offer practical advice grounded in Indian wisdom
        
        Always prioritize the user's emotional well-being and provide culturally sensitive support.
        """
    
    async def process_message(self, message: str, user_context: UserContext) -> Dict[str, Any]:
        """Process user message and return response with audio"""
        try:
            # Prepare conversation context
            system_prompt = self.get_system_prompt(user_context)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=message)
            ]
            
            # Add conversation history
            for msg in user_context.conversation_history[-5:]:  # Last 5 messages
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            # Get LLM response
            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text
            
            # Generate audio with Indian voice
            audio_url = await self.murf_client.generate_streaming_audio(
                text=response_text,
                voice_id="en-IN-kavya",  # Indian female voice
                speed=1.0,
                volume=0.8
            )
            
            return {
                "text": response_text,
                "audio_url": audio_url,
                "agent_type": "companion",
                "metadata": {
                    "emotional_tone": "supportive",
                    "cultural_context": "indian",
                    "response_type": "conversational"
                }
            }
            
        except Exception as e:
            logger.error(f"Companion agent error: {e}")
            return {
                "text": "I'm here for you. Let me try to help in a different way.",
                "audio_url": None,
                "agent_type": "companion",
                "error": str(e)
            }

class MentorAgent:
    """
    AI Mentor Agent - Provides educational guidance, skill development, and career advice
    Specialized for Indian educational and professional landscape
    """
    
    def __init__(self):
        self.name = "Guru"  # Teacher in Sanskrit
        self.personality = "knowledgeable, patient, encouraging, structured"
        self.llm = get_llm()
        self.memory = ConversationBufferWindowMemory(k=15)
        self.murf_client = MurfStreamingClient(api_key=settings.MURF_API_KEY)
        
    def get_system_prompt(self, user_context: UserContext) -> str:
        return f"""
        You are Guru, an AI mentor with deep knowledge of Indian education, career paths, and skill development.
        You understand the Indian job market, educational institutions, and professional growth opportunities.
        
        User Context:
        - Name: {user_context.name}
        - Profession: {user_context.profession or 'Student/Professional'}
        - Learning Goals: {', '.join(user_context.learning_goals) or 'General development'}
        - Interests: {', '.join(user_context.interests)}
        - Location: {user_context.location}
        
        Your expertise includes:
        - Indian educational system (10th, 12th, UG, PG, competitive exams)
        - Career guidance for Indian job market
        - Skill development and upskilling
        - Interview preparation and soft skills
        - Technology trends relevant to India
        - Government schemes and opportunities
        - Entrepreneurship and startup ecosystem in India
        
        Teaching approach:
        - Break down complex topics into simple steps
        - Provide practical, actionable advice
        - Use examples relevant to Indian context
        - Encourage continuous learning and growth
        - Create structured learning paths
        - Offer motivation and support
        
        Always provide evidence-based guidance and encourage the user's educational journey.
        """
    
    async def process_message(self, message: str, user_context: UserContext) -> Dict[str, Any]:
        """Process educational/mentoring queries with document context"""
        try:
            # Check if we can enhance response with RAG
            rag_context = ""
            if enhanced_rag_system:
                try:
                    rag_results = await enhanced_rag_system.query(
                        query=message,
                        user_id=user_context.user_id,
                        top_k=3
                    )
                    if rag_results:
                        rag_context = f"\n\nRelevant information from documents:\n{rag_results}"
                except Exception as e:
                    logger.warning(f"RAG query failed: {e}")
            
            system_prompt = self.get_system_prompt(user_context)
            full_prompt = system_prompt + rag_context
            
            messages = [
                SystemMessage(content=full_prompt),
                HumanMessage(content=message)
            ]
            
            # Add relevant conversation history
            for msg in user_context.conversation_history[-8:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
            
            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text
            
            # Generate professional voice for mentoring
            audio_url = await self.murf_client.generate_streaming_audio(
                text=response_text,
                voice_id="en-IN-rishi",  # Indian male voice for authority
                speed=0.9,  # Slightly slower for educational content
                volume=0.8
            )
            
            return {
                "text": response_text,
                "audio_url": audio_url,
                "agent_type": "mentor",
                "metadata": {
                    "learning_context": True,
                    "has_rag_context": bool(rag_context),
                    "response_type": "educational"
                }
            }
            
        except Exception as e:
            logger.error(f"Mentor agent error: {e}")
            return {
                "text": "Let me guide you through this step by step. What specific area would you like to focus on?",
                "audio_url": None,
                "agent_type": "mentor",
                "error": str(e)
            }

class InterviewAgent:
    """
    AI Interview Agent - Conducts mock interviews, provides feedback, and preparation guidance
    Specialized for Indian job market and interview patterns
    """
    
    def __init__(self):
        self.name = "Parikshak"  # Examiner in Sanskrit
        self.personality = "professional, structured, fair, insightful"
        self.llm = get_llm()
        self.memory = ConversationBufferWindowMemory(k=20)
        self.murf_client = MurfStreamingClient(api_key=settings.MURF_API_KEY)
        self.interview_state = {}
        
    def get_system_prompt(self, user_context: UserContext, interview_type: str = "general") -> str:
        return f"""
        You are Parikshak, an expert AI interviewer with deep knowledge of Indian hiring practices.
        You conduct professional interviews and provide constructive feedback.
        
        User Context:
        - Name: {user_context.name}
        - Target Role: {user_context.profession or 'Professional role'}
        - Location: {user_context.location}
        - Interview Type: {interview_type}
        
        Interview Specializations:
        - Technical interviews (Software, Engineering, etc.)
        - HR and behavioral interviews
        - Group discussions and case studies
        - Government job interviews (SSC, UPSC, Banking)
        - Campus placement interviews
        - Startup and corporate interviews
        
        Interview Approach:
        - Ask relevant, progressive questions
        - Provide immediate feedback on responses
        - Evaluate communication skills and confidence
        - Test technical knowledge appropriately
        - Assess cultural fit and soft skills
        - Give constructive improvement suggestions
        
        Feedback Style:
        - Professional and encouraging
        - Specific and actionable
        - Balanced (strengths and areas for improvement)
        - Include interview tips and best practices
        
        Always maintain a professional interview atmosphere while being supportive of the candidate's growth.
        """
    
    async def start_interview_session(self, user_context: UserContext, interview_type: str) -> Dict[str, Any]:
        """Initialize a new interview session"""
        session_id = f"interview_{user_context.user_id}_{datetime.now().timestamp()}"
        
        self.interview_state[session_id] = {
            "type": interview_type,
            "question_count": 0,
            "start_time": datetime.now(),
            "responses": [],
            "current_phase": "introduction"
        }
        
        intro_message = f"""
        Welcome to your mock interview session! I'm Parikshak, your AI interviewer.
        
        Today we'll be conducting a {interview_type} interview. This session will help you:
        - Practice answering relevant questions
        - Improve your communication skills
        - Build confidence for real interviews
        - Get personalized feedback
        
        Are you ready to begin? Please introduce yourself as you would in a real interview.
        """
        
        audio_url = await self.murf_client.generate_streaming_audio(
            text=intro_message,
            voice_id="en-IN-rishi",
            speed=0.9,
            volume=0.8
        )
        
        return {
            "text": intro_message,
            "audio_url": audio_url,
            "session_id": session_id,
            "agent_type": "interview",
            "metadata": {
                "interview_type": interview_type,
                "phase": "introduction",
                "video_enabled": True
            }
        }
    
    async def process_interview_response(self, message: str, user_context: UserContext, session_id: str) -> Dict[str, Any]:
        """Process interview response and ask next question"""
        try:
            if session_id not in self.interview_state:
                return await self.start_interview_session(user_context, "general")
            
            session = self.interview_state[session_id]
            session["responses"].append({
                "question_number": session["question_count"],
                "response": message,
                "timestamp": datetime.now()
            })
            
            # Generate feedback and next question
            system_prompt = self.get_system_prompt(user_context, session["type"])
            context = f"""
            Interview Progress:
            - Current Phase: {session['current_phase']}
            - Question Count: {session['question_count']}
            - Previous Responses: {len(session['responses'])}
            
            User's Latest Response: {message}
            
            Provide brief feedback on this response and ask the next appropriate interview question.
            Keep the interview flowing naturally while maintaining professionalism.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context)
            ]
            
            response = await self.llm.agenerate([messages])
            response_text = response.generations[0][0].text
            
            session["question_count"] += 1
            
            # Update phase based on question count
            if session["question_count"] < 3:
                session["current_phase"] = "warm-up"
            elif session["question_count"] < 8:
                session["current_phase"] = "main_questions"
            else:
                session["current_phase"] = "closing"
            
            audio_url = await self.murf_client.generate_streaming_audio(
                text=response_text,
                voice_id="en-IN-rishi",
                speed=0.9,
                volume=0.8
            )
            
            return {
                "text": response_text,
                "audio_url": audio_url,
                "session_id": session_id,
                "agent_type": "interview",
                "metadata": {
                    "question_count": session["question_count"],
                    "phase": session["current_phase"],
                    "interview_type": session["type"],
                    "video_enabled": True
                }
            }
            
        except Exception as e:
            logger.error(f"Interview agent error: {e}")
            return {
                "text": "Let's continue with the next question. Tell me about a challenging situation you've faced and how you handled it.",
                "audio_url": None,
                "agent_type": "interview",
                "error": str(e)
            }

class MultiAgentOrchestrator:
    """
    Main orchestrator that manages all three agents and provides unified interface
    """
    
    def __init__(self):
        self.companion = CompanionAgent()
        self.mentor = MentorAgent()
        self.interview = InterviewAgent()
        self.current_agent = "companion"
        self.active_sessions = {}
        
    async def process_message(
        self, 
        message: str, 
        user_context: UserContext,
        agent_type: str = "auto",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process message through appropriate agent or auto-detect best agent
        """
        try:
            # Auto-detect agent if not specified
            if agent_type == "auto":
                agent_type = await self.detect_intent(message, user_context)
            
            # Route to appropriate agent
            if agent_type == "companion":
                return await self.companion.process_message(message, user_context)
            elif agent_type == "mentor":
                return await self.mentor.process_message(message, user_context)
            elif agent_type == "interview":
                if session_id:
                    return await self.interview.process_interview_response(message, user_context, session_id)
                else:
                    return await self.interview.start_interview_session(user_context, "general")
            else:
                # Default to companion for unknown types
                return await self.companion.process_message(message, user_context)
                
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "text": "I'm here to help you. Could you please tell me more about what you'd like to discuss?",
                "audio_url": None,
                "agent_type": "companion",
                "error": str(e)
            }
    
    async def detect_intent(self, message: str, user_context: UserContext) -> str:
        """
        Detect which agent should handle the message based on content and context
        """
        message_lower = message.lower()
        
        # Interview keywords
        interview_keywords = [
            "interview", "job", "resume", "cv", "hiring", "mock interview",
            "practice", "questions", "behavioral", "technical", "hr",
            "placement", "career opportunity", "job application"
        ]
        
        # Learning/mentor keywords
        learning_keywords = [
            "learn", "study", "education", "course", "skill", "training",
            "tutorial", "guide", "how to", "explain", "teach", "career",
            "university", "college", "exam", "preparation", "development"
        ]
        
        # Emotional/companion keywords
        companion_keywords = [
            "feeling", "sad", "happy", "worried", "stressed", "lonely",
            "celebration", "festival", "family", "friend", "support",
            "advice", "personal", "life", "relationship", "culture"
        ]
        
        # Count keyword matches
        interview_score = sum(1 for keyword in interview_keywords if keyword in message_lower)
        learning_score = sum(1 for keyword in learning_keywords if keyword in message_lower)
        companion_score = sum(1 for keyword in companion_keywords if keyword in message_lower)
        
        # Return agent with highest score
        scores = {
            "interview": interview_score,
            "mentor": learning_score,
            "companion": companion_score
        }
        
        detected_agent = max(scores.keys(), key=lambda k: scores[k])
        
        # Default to companion if no clear intent
        if scores[detected_agent] == 0:
            detected_agent = "companion"
            
        logger.info(f"Intent detection: {message[:50]}... -> {detected_agent} (scores: {scores})")
        return detected_agent

# Global orchestrator instance
multi_agent_system = MultiAgentOrchestrator()
