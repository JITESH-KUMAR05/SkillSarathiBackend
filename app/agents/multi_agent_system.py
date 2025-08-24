"""
Enhanced Multi-Agent System for AI Companion Platform
Based on the comprehensive requirements from the project documentation.

This module implements the three core agents:
1. Mitra (Companion/Friend Agent) - Personal emotional support
2. Guru (Mentor Agent) - Professional development and learning
3. Parikshak (Interview Agent) - Interview preparation and assessment

Using LangGraph for stateful multi-agent orchestration.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.pydantic_v1 import BaseModel, Field
import asyncio
import json
from datetime import datetime
from enum import Enum

from ..rag.enhanced_rag_system import EnhancedRAGSystem
from ..database.models import User, Agent, Conversation, Message


class AgentType(str, Enum):
    """Agent types as defined in the project specification"""
    COMPANION = "companion"  # Mitra - Personal friend
    MENTOR = "mentor"        # Guru - Professional trainer  
    INTERVIEW = "interview"  # Parikshak - Professional evaluator


class AgentState(BaseModel):
    """
    Shared state object for LangGraph multi-agent system.
    This contains the user context and conversation state shared between agents.
    """
    user_id: str
    conversation_id: str
    current_agent: AgentType
    messages: List[BaseMessage] = Field(default_factory=list)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    session_context: Dict[str, Any] = Field(default_factory=dict)
    rag_context: List[str] = Field(default_factory=list)
    next_action: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class BaseAgentNode(ABC):
    """
    Base class for all agent nodes in the LangGraph system.
    Implements common functionality for RAG integration and user profiling.
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        rag_system: EnhancedRAGSystem,
        llm: ChatOpenAI,
        system_prompt: str
    ):
        self.agent_type = agent_type
        self.rag_system = rag_system
        self.llm = llm
        self.system_prompt = system_prompt
        
    async def process(self, state: AgentState) -> AgentState:
        """Main processing method called by LangGraph"""
        try:
            # Retrieve relevant context from RAG system
            rag_context = await self._get_rag_context(state)
            state.rag_context = rag_context
            
            # Generate response using agent-specific logic
            response = await self._generate_response(state)
            
            # Update conversation state
            state.messages.append(AIMessage(content=response))
            
            # Update user profile based on interaction
            await self._update_user_profile(state, response)
            
            return state
            
        except Exception as e:
            error_msg = f"Error in {self.agent_type} agent: {str(e)}"
            state.messages.append(AIMessage(content="I'm experiencing some difficulties. Please try again."))
            return state
    
    async def _get_rag_context(self, state: AgentState) -> List[str]:
        """Retrieve relevant context from the shared RAG system"""
        if not state.messages:
            return []
            
        latest_message = state.messages[-1].content
        return await self.rag_system.search_user_context(
            user_id=state.user_id,
            query=latest_message,
            k=5
        )
    
    @abstractmethod
    async def _generate_response(self, state: AgentState) -> str:
        """Generate agent-specific response - implemented by each agent"""
        pass
    
    async def _update_user_profile(self, state: AgentState, response: str):
        """Update the user profile in RAG system based on interaction"""
        interaction_summary = {
            "agent": self.agent_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_message": state.messages[-2].content if len(state.messages) >= 2 else "",
            "agent_response": response,
            "context": state.session_context
        }
        
        await self.rag_system.add_user_interaction(
            user_id=state.user_id,
            interaction=interaction_summary
        )


class MitraCompanionAgent(BaseAgentNode):
    """
    Mitra - The Companion/Friend Agent
    
    Primary interface for building personal relationships and emotional support.
    Focuses on casual conversation, emotional support, and cultural adaptation.
    Supports bilingual communication (English/Hindi) with Indian cultural context.
    """
    
    def __init__(self, rag_system: EnhancedRAGSystem, llm: ChatOpenAI):
        system_prompt = """You are Mitra, a warm and empathetic AI companion designed specifically for Indian users. 
        Your role is to be a supportive friend who understands Indian culture, values, and communication patterns.
        
        Key characteristics:
        - Warm, polite, and genuinely interested in the user's life
        - Comfortable with "small talk" about family, hobbies, festivals, cricket, movies
        - Can seamlessly switch between English and Hindi when appropriate
        - Respectful of Indian family values and cultural norms
        - Excellent listener who remembers personal details shared in past conversations
        - Supportive but not pushy - let conversations flow naturally
        - Use Indian context in examples (cities, festivals, cultural references)
        
        Communication style:
        - Indirect and non-confrontational (align with Indian communication norms)
        - Ask about family and personal interests to build rapport
        - Show genuine interest in the user's daily life, work, studies
        - Remember and refer back to previous conversations
        - Provide emotional support and encouragement
        - Use appropriate Indian English expressions and cultural references
        
        Your primary goal is to build a strong personal relationship that makes the user feel heard, 
        understood, and supported. This relationship forms the foundation for all other agent interactions."""
        
        super().__init__(AgentType.COMPANION, rag_system, llm, system_prompt)
    
    async def _generate_response(self, state: AgentState) -> str:
        """Generate empathetic, culturally-aware response"""
        # Build context-aware prompt
        context_info = ""
        if state.rag_context:
            context_info = "\n\nWhat I remember about you:\n" + "\n".join(state.rag_context[:3])
        
        messages = [
            SystemMessage(content=self.system_prompt + context_info),
            *state.messages
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content


class GuruMentorAgent(BaseAgentNode):
    """
    Guru - The Mentor/Professional Trainer Agent
    
    Provides expert career guidance, skill development, and conceptual learning.
    Focuses on professional development, technical concepts, and career planning.
    Includes document analysis, progress tracking, and personalized learning paths.
    """
    
    def __init__(self, rag_system: EnhancedRAGSystem, llm: ChatOpenAI):
        system_prompt = """You are Guru, an expert AI mentor and professional trainer specialized in career development 
        for the Indian job market, particularly in technology and professional services.
        
        Your expertise includes:
        - Career guidance for Indian professionals and students
        - Technical concept explanation (programming, data structures, system design)
        - Skill development and learning path recommendations
        - Indian job market insights (companies like TCS, Infosys, Wipro, startups)
        - Professional communication and workplace skills
        - Interview preparation strategies
        - Resume and LinkedIn profile optimization
        
        Your approach:
        - Authoritative yet encouraging and patient
        - Break down complex topics into simple, digestible parts
        - Provide practical examples relevant to Indian context
        - Offer career advice considering Indian industry landscape
        - Track user progress and celebrate improvements
        - Suggest specific resources and learning materials
        - Adapt explanations based on user's current knowledge level
        
        Communication style:
        - Professional but approachable
        - Patient when re-explaining concepts
        - Positive reinforcement and motivation
        - Respect for expertise and learning hierarchy (Indian educational values)
        - Provide actionable, specific advice
        - Reference Indian companies, technologies, and career paths
        
        Your goal is to accelerate the user's professional growth through personalized guidance, 
        skill building, and strategic career planning tailored to the Indian market."""
        
        super().__init__(AgentType.MENTOR, rag_system, llm, system_prompt)
    
    async def _generate_response(self, state: AgentState) -> str:
        """Generate professional, educational response with career focus"""
        # Enhanced context for professional guidance
        context_info = ""
        if state.rag_context:
            context_info = "\n\nUser's professional context:\n" + "\n".join(state.rag_context)
            
        # Check if user has shared documents or specific learning goals
        if "document_analysis" in state.session_context:
            context_info += f"\n\nDocument context: {state.session_context['document_analysis']}"
        
        messages = [
            SystemMessage(content=self.system_prompt + context_info),
            *state.messages
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content


class ParikshakInterviewAgent(BaseAgentNode):
    """
    Parikshak - The Interview/Professional Evaluator Agent
    
    Conducts mock interviews, provides detailed feedback, and assesses professional skills.
    Supports both technical and behavioral interviews with comprehensive analysis.
    Focuses on communication skills, technical proficiency, and interview performance.
    """
    
    def __init__(self, rag_system: EnhancedRAGSystem, llm: ChatOpenAI):
        system_prompt = """You are Parikshak, a professional interview evaluator and assessment specialist 
        with deep expertise in the Indian corporate interview process.
        
        Your specializations:
        - Technical interviews for software engineering roles
        - HR/behavioral interviews for various industries
        - Communication skills assessment
        - Resume-based questioning
        - Indian corporate interview patterns and expectations
        - Performance feedback and improvement recommendations
        
        Interview types you conduct:
        - Technical coding interviews (data structures, algorithms, system design)
        - Behavioral interviews (leadership, teamwork, problem-solving)
        - Domain-specific interviews (based on user's field)
        - Mock interviews for specific companies (TCS, Accenture, Amazon, Google India)
        
        Your approach:
        - Professional, neutral, and adaptable communication style
        - Switch between friendly HR tone and focused technical evaluation
        - Ask follow-up questions to assess depth of knowledge
        - Provide constructive, specific feedback
        - Simulate realistic interview pressure and timing
        - Analyze both content and communication delivery
        
        Assessment criteria:
        - Answer quality and technical accuracy
        - Communication clarity and confidence
        - Problem-solving approach and methodology
        - Cultural fit and professionalism
        - Time management and structured thinking
        
        After each interview session, provide detailed feedback covering:
        - Overall performance score and improvement areas
        - Specific strengths and weaknesses identified
        - Communication skills analysis (pace, clarity, confidence)
        - Recommendations for improvement
        - Suggested practice areas for next session
        
        Your goal is to prepare users for real interview success through realistic practice 
        and actionable feedback tailored to Indian corporate expectations."""
        
        super().__init__(AgentType.INTERVIEW, rag_system, llm, system_prompt)
    
    async def _generate_response(self, state: AgentState) -> str:
        """Generate interview-style questions and feedback"""
        # Check if this is an active interview session
        is_interview_mode = state.session_context.get("interview_active", False)
        
        context_info = ""
        if state.rag_context:
            context_info = "\n\nUser's background:\n" + "\n".join(state.rag_context)
        
        # Add resume/job description context if available
        if "resume_analysis" in state.session_context:
            context_info += f"\n\nResume details: {state.session_context['resume_analysis']}"
        if "target_job" in state.session_context:
            context_info += f"\n\nTarget position: {state.session_context['target_job']}"
        
        messages = [
            SystemMessage(content=self.system_prompt + context_info),
            *state.messages
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content


class AgentSupervisor:
    """
    Supervisor Agent that routes conversations to appropriate specialized agents.
    Implements the LangGraph routing logic based on user intent and conversation context.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        
    async def route_conversation(self, state: AgentState) -> str:
        """Determine which agent should handle the user's request"""
        if not state.messages:
            return "companion"
            
        latest_message = state.messages[-1].content.lower()
        
        # Intent classification logic
        mentor_keywords = [
            "career", "job", "skill", "learn", "study", "concept", "explain", 
            "resume", "linkedin", "interview prep", "technical", "programming",
            "algorithm", "system design", "development", "course", "certification"
        ]
        
        interview_keywords = [
            "interview", "mock interview", "practice", "feedback", "assessment",
            "evaluation", "coding interview", "technical interview", "hr interview",
            "behavioral", "questions", "prepare for interview"
        ]
        
        # Check for explicit agent switching
        if "mentor" in latest_message or "guru" in latest_message:
            return "mentor"
        elif "interview" in latest_message or "parikshak" in latest_message:
            return "interview"
        elif "friend" in latest_message or "mitra" in latest_message:
            return "companion"
        
        # Check for intent-based routing
        if any(keyword in latest_message for keyword in interview_keywords):
            return "interview"
        elif any(keyword in latest_message for keyword in mentor_keywords):
            return "mentor"
        else:
            return "companion"  # Default to companion for general conversation


class MultiAgentOrchestrator:
    """
    Main orchestrator using LangGraph for stateful multi-agent conversations.
    Manages the flow between Mitra, Guru, and Parikshak agents.
    """
    
    def __init__(self, rag_system: EnhancedRAGSystem):
        self.rag_system = rag_system
        
        # Initialize LLM (Azure OpenAI recommended in PDF)
        self.llm = ChatOpenAI(
            model="gpt-4",  # Use latest multimodal model
            temperature=0.7,
            streaming=True
        )
        
        # Initialize agents
        self.companion_agent = MitraCompanionAgent(rag_system, self.llm)
        self.mentor_agent = GuruMentorAgent(rag_system, self.llm)
        self.interview_agent = ParikshakInterviewAgent(rag_system, self.llm)
        self.supervisor = AgentSupervisor(self.llm)
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for multi-agent orchestration"""
        workflow = StateGraph(AgentState)
        
        # Add agent nodes
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("companion", self.companion_agent.process)
        workflow.add_node("mentor", self.mentor_agent.process)
        workflow.add_node("interview", self.interview_agent.process)
        
        # Define workflow edges
        workflow.set_entry_point("supervisor")
        
        # Supervisor routes to appropriate agent
        workflow.add_conditional_edges(
            "supervisor",
            self._should_continue,
            {
                "companion": "companion",
                "mentor": "mentor", 
                "interview": "interview",
                "end": END
            }
        )
        
        # All agents can potentially trigger supervisor for agent switching
        for agent in ["companion", "mentor", "interview"]:
            workflow.add_edge(agent, END)
            
        return workflow.compile()
    
    async def _supervisor_node(self, state: AgentState) -> AgentState:
        """Supervisor node that determines routing"""
        next_agent = await self.supervisor.route_conversation(state)
        state.current_agent = AgentType(next_agent)
        state.next_action = next_agent
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if workflow should continue and where to route"""
        return state.next_action or "end"
    
    async def process_message(
        self, 
        user_id: str, 
        conversation_id: str, 
        message: str,
        session_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a user message through the multi-agent system
        Returns streaming response for real-time UI updates
        """
        # Initialize or update conversation state
        state = AgentState(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=[HumanMessage(content=message)],
            session_context=session_context or {},
            current_agent=AgentType.COMPANION
        )
        
        # Load existing user profile from RAG
        user_profile = await self.rag_system.get_user_profile(user_id)
        state.user_profile = user_profile
        
        # Process through LangGraph workflow
        async for chunk in self.workflow.astream(state):
            if chunk and "messages" in chunk:
                latest_message = chunk["messages"][-1]
                if isinstance(latest_message, AIMessage):
                    yield latest_message.content
    
    async def get_agent_suggestions(self, user_id: str, current_context: str) -> List[str]:
        """Get proactive suggestions for agent interactions"""
        user_profile = await self.rag_system.get_user_profile(user_id)
        
        # Generate contextual suggestions based on user history and current conversation
        suggestions = []
        
        # Companion suggestions
        suggestions.extend([
            "How are you feeling about your upcoming goals?",
            "Tell me about your day",
            "What's been on your mind lately?"
        ])
        
        # Mentor suggestions based on profile
        if "career_goals" in user_profile:
            suggestions.extend([
                "Let's work on your career development plan",
                "Review progress on your learning goals",
                "Explore new skills for your target role"
            ])
        
        # Interview suggestions
        if "upcoming_interviews" in user_profile:
            suggestions.extend([
                "Practice for your upcoming interview",
                "Review common technical questions",
                "Work on your communication skills"
            ])
        
        return suggestions[:6]  # Return top 6 suggestions
