"""
Agent Orchestrator for managing multiple AI agents
Handles routing, context, and specialized responses for Indian market
Supports WebSocket streaming for minimal latency
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from langchain.schema import HumanMessage, SystemMessage
from app.llm.streaming_llm import StreamingLLMWrapper
from app.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    def __init__(self):
        self.agents = {
            "mitra": MitraAgent(),
            "guru": GuruAgent(), 
            "parikshak": ParikshakAgent()
        }
        self.user_contexts: Dict[str, Dict[str, Any]] = {}
    
    async def process_message(
        self, 
        message: str, 
        agent_type: str, 
        user_id: str,
        streaming_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """
        Process message through selected agent
        
        Args:
            message: The user's message
            agent_type: Which agent to use (mitra, guru, parikshak)
            user_id: Unique identifier for the user
            streaming_callback: Optional callback for streaming responses via WebSocket
            
        Returns:
            The agent's response as a string
        """
        try:
            # Get or create user context
            if user_id not in self.user_contexts:
                self.user_contexts[user_id] = {
                    "conversation_history": [],
                    "preferences": {},
                    "created_at": datetime.now()
                }
            
            user_context = self.user_contexts[user_id]
            
            # Add message to history
            user_context["conversation_history"].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now(),
                "agent": agent_type
            })
            
            # Get agent
            agent = self.agents.get(agent_type)
            if not agent:
                return f"Agent '{agent_type}' not found. Available agents: {list(self.agents.keys())}"
            
            # If streaming callback is provided, use streaming mode
            if streaming_callback:
                # Create a direct streaming message to LLM
                response = await self.stream_agent_response(
                    agent=agent,
                    message=message,
                    user_context=user_context,
                    streaming_callback=streaming_callback
                )
            else:
                # Traditional non-streaming mode
                response = await agent.process_message(message, user_context)
            
            # Add response to history
            user_context["conversation_history"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(),
                "agent": agent_type
            })
            
            # Keep only last 20 messages to manage memory
            if len(user_context["conversation_history"]) > 20:
                user_context["conversation_history"] = user_context["conversation_history"][-20:]
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error processing your message: {str(e)}"
    
    async def route_message(self, message: str, agent_type: str = "mitra", user_id: str = "test_user") -> str:
        """
        Simple routing method for testing and basic usage
        
        Args:
            message: The user's message
            agent_type: Which agent to use (default: mitra)
            user_id: User identifier (default: test_user)
            
        Returns:
            The agent's response
        """
        return await self.process_message(message, agent_type, user_id)
            
    async def stream_agent_response(
        self,
        agent,
        message: str,
        user_context: Dict[str, Any],
        streaming_callback: Callable[[Dict[str, Any]], None]
    ) -> str:
        """
        Stream agent response with minimal latency via WebSocket
        
        Args:
            agent: The agent to use
            message: The user's message
            user_context: The user's context
            streaming_callback: Callback for streaming responses via WebSocket
            
        Returns:
            The complete response as a string
        """
        try:
            # Get the system prompt from the agent
            system_prompt = agent._get_system_prompt() if hasattr(agent, '_get_system_prompt') else f"You are {agent.name}, a helpful assistant with expertise in {agent.expertise}."
            
            # Convert conversation history to LangChain message format
            messages = [SystemMessage(content=system_prompt)]
            
            # Add conversation history if available (last 5 messages for context)
            if user_context.get("conversation_history"):
                history = user_context["conversation_history"][-5:]  # Last 5 messages
                for msg in history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(SystemMessage(content=msg["content"]))
            
            # Add the current message
            messages.append(HumanMessage(content=message))
            
            # Create a streaming LLM
            llm = LLMFactory.create_llm(
                model_name="gpt-4o",
                temperature=0.7,
                config={"streaming": True}  # Enable streaming
            )
            
            # Wrap the LLM for streaming
            streaming_llm = StreamingLLMWrapper(llm)
            
            # Stream the response
            full_response = await streaming_llm.stream_chat(
                messages=messages,
                websocket_sender=streaming_callback
            )
            
            return full_response
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            await streaming_callback({
                "type": "error",
                "content": f"Error generating streaming response: {str(e)}"
            })
            return f"Sorry, I encountered an error processing your message: {str(e)}"

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, personality: str, expertise: str):
        self.name = name
        self.personality = personality
        self.expertise = expertise
    
    async def process_message(self, message: str, user_context: Dict[str, Any]) -> str:
        """Override in subclasses"""
        return "Base agent response"
    
    def get_context_summary(self, user_context: Dict[str, Any]) -> str:
        """Get conversation context summary"""
        history = user_context.get("conversation_history", [])
        if not history:
            return "No previous conversation"
        
        recent_messages = history[-5:]  # Last 5 messages
        context_parts = []
        
        for msg in recent_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")[:100]  # Truncate long messages
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)

class MitraAgent(BaseAgent):
    """Cultural Guide & Personal Assistant - Warm, culturally aware companion"""
    
    def __init__(self):
        super().__init__(
            name="Mitra",
            personality="Warm, culturally aware, helpful companion",
            expertise="Cultural insights, festivals, traditions, personal assistance"
        )
    
    async def process_message(self, message: str, user_context: Dict[str, Any]) -> str:
        """Process message with cultural context and warmth"""
        try:
            # Get conversation context
            context = self.get_context_summary(user_context)
            
            # Simulate AI processing with cultural awareness
            if any(word in message.lower() for word in ["festival", "celebration", "tradition", "culture"]):
                response = await self._handle_cultural_query(message, context)
            elif any(word in message.lower() for word in ["help", "assist", "support", "guide"]):
                response = await self._handle_assistance_request(message, context)
            else:
                response = await self._handle_general_conversation(message, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Mitra agent error: {e}")
            return "Namaste! I'm here to help you with cultural insights and personal assistance. How can I guide you today?"
    
    async def _handle_cultural_query(self, message: str, context: str) -> str:
        """Handle cultural and festival-related queries"""
        cultural_responses = {
            "diwali": "Diwali, the Festival of Lights, is one of the most celebrated festivals in India! 🪔 It symbolizes the victory of light over darkness. Would you like to know about celebration traditions or preparation tips?",
            "holi": "Holi, the Festival of Colors, celebrates the arrival of spring! 🌈 It's a time of joy, forgiveness, and new beginnings. Are you planning to celebrate or learning about the traditions?",
            "navratri": "Navratri is a beautiful nine-night festival honoring the Divine Feminine! 💃 Each day has special significance with different colors and rituals. Which aspect interests you most?",
            "tradition": "Indian traditions are rich and diverse, varying by region and community. 🕉️ From daily rituals to life celebrations, each has deep meaning. What specific tradition would you like to explore?"
        }
        
        for keyword, response in cultural_responses.items():
            if keyword in message.lower():
                return response
        
        return "Indian culture is incredibly rich with festivals, traditions, and customs! 🇮🇳 Each region has its unique practices. What specific cultural aspect would you like to learn about?"
    
    async def _handle_assistance_request(self, message: str, context: str) -> str:
        """Handle personal assistance requests"""
        return f"I'm here to help you, friend! 🤝 As your cultural companion, I can assist with:\n\n• Festival planning and traditions\n• Cultural etiquette and customs\n• Personal guidance with Indian context\n• Daily life assistance\n\nWhat would you like help with today?"
    
    async def _handle_general_conversation(self, message: str, context: str) -> str:
        """Handle general conversation with warmth"""
        return f"Namaste! 🙏 I'm Mitra, your cultural companion. I love helping people connect with Indian traditions and providing warm, personal assistance. How can I make your day better?"

class GuruAgent(BaseAgent):
    """Knowledge & Education Expert - Wise, patient, encouraging teacher"""
    
    def __init__(self):
        super().__init__(
            name="Guru",
            personality="Wise, patient, encouraging teacher",
            expertise="Education, learning paths, skill development, academic guidance"
        )
    
    async def process_message(self, message: str, user_context: Dict[str, Any]) -> str:
        """Process educational and learning-related queries"""
        try:
            context = self.get_context_summary(user_context)
            
            if any(word in message.lower() for word in ["learn", "study", "education", "skill", "course"]):
                response = await self._handle_learning_query(message, context)
            elif any(word in message.lower() for word in ["career", "job", "profession", "future"]):
                response = await self._handle_career_guidance(message, context)
            else:
                response = await self._handle_knowledge_sharing(message, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Guru agent error: {e}")
            return "Namaste, dear student! 📚 I'm here to guide your learning journey. What knowledge are you seeking today?"
    
    async def _handle_learning_query(self, message: str, context: str) -> str:
        """Handle learning and education queries"""
        return f"Excellent! Learning is a lifelong journey. 🎓 I can help you with:\n\n• Study strategies and techniques\n• Skill development paths\n• Course recommendations\n• Academic planning\n• Exam preparation\n\nWhat specific area would you like to explore? Remember, every expert was once a beginner!"
    
    async def _handle_career_guidance(self, message: str, context: str) -> str:
        """Handle career and professional development"""
        return f"Career planning is crucial for success! 💼 Let me guide you through:\n\n• Skills assessment\n• Industry insights\n• Growth opportunities\n• Educational pathways\n• Professional development\n\nWhat's your field of interest or current challenge? Together we'll chart your path to success!"
    
    async def _handle_knowledge_sharing(self, message: str, context: str) -> str:
        """Share knowledge and insights"""
        return f"Knowledge is power, and sharing it multiplies its value! 🧠 I'm here to:\n\n• Answer your questions\n• Explain complex concepts\n• Provide learning resources\n• Offer study guidance\n\nWhat would you like to learn about today?"

class ParikshakAgent(BaseAgent):
    """Business & Career Advisor - Strategic, analytical, results-oriented mentor"""
    
    def __init__(self):
        super().__init__(
            name="Parikshak",
            personality="Strategic, analytical, results-oriented mentor",
            expertise="Career guidance, business insights, professional development"
        )
    
    async def process_message(self, message: str, user_context: Dict[str, Any]) -> str:
        """Process business and career-related queries"""
        try:
            context = self.get_context_summary(user_context)
            
            if any(word in message.lower() for word in ["business", "startup", "entrepreneur", "company"]):
                response = await self._handle_business_query(message, context)
            elif any(word in message.lower() for word in ["career", "job", "interview", "promotion"]):
                response = await self._handle_career_strategy(message, context)
            else:
                response = await self._handle_professional_guidance(message, context)
            
            return response
            
        except Exception as e:
            logger.error(f"Parikshak agent error: {e}")
            return "Greetings! 💼 I'm Parikshak, your strategic business and career advisor. Let's discuss your professional goals!"
    
    async def _handle_business_query(self, message: str, context: str) -> str:
        """Handle business and entrepreneurship queries"""
        return f"Business success requires strategic thinking! 📈 I can help with:\n\n• Business planning and strategy\n• Market analysis\n• Startup guidance\n• Growth strategies\n• Financial planning\n• Risk assessment\n\nWhat's your business challenge or opportunity? Let's create a winning strategy together!"
    
    async def _handle_career_strategy(self, message: str, context: str) -> str:
        """Handle career development and strategy"""
        return f"Career success is about strategic planning and execution! 🎯 I'll help you with:\n\n• Career path planning\n• Interview preparation\n• Skill gap analysis\n• Network building\n• Promotion strategies\n• Leadership development\n\nWhat's your current career focus? Let's build your success roadmap!"
    
    async def _handle_professional_guidance(self, message: str, context: str) -> str:
        """Provide general professional guidance"""
        return f"Professional excellence comes from continuous improvement! 💪 I offer:\n\n• Strategic planning\n• Performance optimization\n• Leadership coaching\n• Industry insights\n• Goal setting\n\nWhat professional challenge can I help you tackle today?"

# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()
