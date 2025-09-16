"""
Model Context Protocol (MCP) Integration for BuddyAgents
========================================================

This module implements MCP for managing multi-agent interactions,
candidate progress tracking, and conversation history management.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

from app.database.models import User, Agent, Conversation, Message, InterviewSession
from app.database.base import AsyncSessionLocal

logger = logging.getLogger(__name__)

class AgentType(Enum):
    """Supported agent types"""
    MITRA = "mitra"
    GURU = "guru"
    PARIKSHAK = "parikshak"

class SessionType(Enum):
    """Types of user sessions"""
    CHAT = "chat"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    LEARNING = "learning"

@dataclass
class CandidateProfile:
    """Candidate profile with unique tracking ID"""
    candidate_id: str
    name: str
    email: str
    phone: Optional[str] = None
    experience_level: Optional[str] = None
    target_role: Optional[str] = None
    skills: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.candidate_id is None:
            self.candidate_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.skills is None:
            self.skills = []
        if self.preferences is None:
            self.preferences = {}

@dataclass
class SessionContext:
    """Context for tracking session state"""
    session_id: str
    candidate_id: str
    agent_type: AgentType
    session_type: SessionType
    started_at: datetime
    current_phase: str = "introduction"
    messages_count: int = 0
    context_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}

@dataclass
class AgentMessage:
    """Standardized message format across all agents"""
    message_id: str
    session_id: str
    agent_type: AgentType
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    audio_url: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class MCPManager:
    """
    Model Context Protocol Manager for multi-agent coordination
    
    Handles:
    - Candidate registration and tracking
    - Multi-agent session management
    - Context preservation across agents
    - Progress tracking and analytics
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionContext] = {}
        self.candidate_profiles: Dict[str, CandidateProfile] = {}
        self.message_history: Dict[str, List[AgentMessage]] = {}
        
    async def register_candidate(
        self, 
        name: str, 
        email: str, 
        phone: Optional[str] = None,
        experience_level: Optional[str] = None,
        target_role: Optional[str] = None,
        skills: Optional[List[str]] = None
    ) -> CandidateProfile:
        """Register a new candidate and return their profile with unique ID"""
        
        candidate = CandidateProfile(
            candidate_id=str(uuid.uuid4()),
            name=name,
            email=email,
            phone=phone,
            experience_level=experience_level,
            target_role=target_role,
            skills=skills or []
        )
        
        # Store in memory and database
        self.candidate_profiles[candidate.candidate_id] = candidate
        
        # Create user in database with proper error handling
        try:
            async with AsyncSessionLocal() as db:
                # Check if user already exists by email
                from sqlalchemy import select
                result = await db.execute(select(User).where(User.email == email))
                existing_user_obj = result.scalar_one_or_none()
                
                if existing_user_obj:
                    logger.warning(f"User with email {email} already exists, updating candidate mapping")
                    # Update our mapping to use existing user ID
                    candidate.candidate_id = existing_user_obj.id
                    self.candidate_profiles[candidate.candidate_id] = candidate
                    return candidate
                
                # Create new user
                db_user = User(
                    id=candidate.candidate_id,
                    username=email.split('@')[0] + '_' + str(uuid.uuid4())[:8],  # Ensure uniqueness
                    email=email,
                    hashed_password="temp_hash",  # Will be properly handled in auth
                    full_name=name,
                    interests=skills or [],
                    preferred_language="en"
                )
                db.add(db_user)
                await db.commit()
                await db.refresh(db_user)
                
        except Exception as e:
            logger.error(f"Database error during candidate registration: {e}")
            # Continue with in-memory registration even if DB fails
            logger.info("Continuing with in-memory candidate registration")
            
        logger.info(f"Registered new candidate: {candidate.candidate_id}")
        return candidate
    
    async def start_session(
        self, 
        candidate_id: str, 
        agent_type: AgentType,
        session_type: SessionType = SessionType.CHAT
    ) -> SessionContext:
        """Start a new session with specified agent"""
        
        if candidate_id not in self.candidate_profiles:
            raise ValueError(f"Candidate {candidate_id} not found")
            
        session_id = str(uuid.uuid4())
        
        session = SessionContext(
            session_id=session_id,
            candidate_id=candidate_id,
            agent_type=agent_type,
            session_type=session_type,
            started_at=datetime.now()
        )
        
        self.active_sessions[session_id] = session
        self.message_history[session_id] = []
        
        # Create conversation in database
        async with AsyncSessionLocal() as db:
            db_conversation = Conversation(
                id=session_id,
                user_id=candidate_id,
                agent_type=agent_type.value,
                session_id=session_id,
                title=f"{agent_type.value.title()} Session",
                message_type="chat",
                role="system",
                content=f"Session started with {agent_type.value}"
            )
            db.add(db_conversation)
            await db.commit()
            
        logger.info(f"Started session {session_id} for candidate {candidate_id} with {agent_type.value}")
        return session
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_type: AgentType,
        metadata: Optional[Dict[str, Any]] = None,
        audio_url: Optional[str] = None
    ) -> AgentMessage:
        """Add a message to session history"""
        
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
            
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            agent_type=agent_type,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {},
            audio_url=audio_url
        )
        
        self.message_history[session_id].append(message)
        self.active_sessions[session_id].messages_count += 1
        
        # Store in database
        async with AsyncSessionLocal() as db:
            db_message = Message(
                id=message.message_id,
                conversation_id=session_id,
                role=role,
                content=content,
                response_metadata=metadata,
                audio_url=audio_url
            )
            db.add(db_message)
            await db.commit()
            
        return message
    
    async def get_session_context(self, session_id: str) -> Optional[SessionContext]:
        """Get current session context"""
        return self.active_sessions.get(session_id)
    
    async def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[AgentMessage]:
        """Get conversation history for a session"""
        
        if session_id not in self.message_history:
            return []
            
        messages = self.message_history[session_id]
        return messages[-limit:] if limit > 0 else messages
    
    async def get_candidate_progress(self, candidate_id: str) -> Dict[str, Any]:
        """Get comprehensive AI-powered progress data for a candidate"""
        
        candidate = self.candidate_profiles.get(candidate_id)
        if not candidate:
            return {}
            
        # Get all sessions for this candidate
        candidate_sessions = [
            session for session in self.active_sessions.values() 
            if session.candidate_id == candidate_id
        ]
        
        # Basic progress metrics (existing)
        total_messages = sum(session.messages_count for session in candidate_sessions)
        agents_interacted = list(set(session.agent_type.value for session in candidate_sessions))
        
        basic_progress = {
            "candidate_profile": asdict(candidate),
            "total_sessions": len(candidate_sessions),
            "total_messages": total_messages,
            "agents_interacted": agents_interacted,
            "recent_sessions": [
                {
                    "session_id": session.session_id,
                    "agent_type": session.agent_type.value,
                    "session_type": session.session_type.value,
                    "started_at": session.started_at.isoformat(),
                    "messages_count": session.messages_count,
                    "current_phase": session.current_phase
                }
                for session in sorted(candidate_sessions, key=lambda x: x.started_at, reverse=True)[:5]
            ]
        }
        
        # Enhanced AI Progress Analysis
        try:
            from app.ai_progress import ai_progress
            logger.info(f"🤖 Starting AI progress analysis for {candidate_id}")
            
            # Prepare session data for AI analysis
            session_data = [
                {
                    "session_id": session.session_id,
                    "agent_type": session.agent_type.value,
                    "started_at": session.started_at.isoformat(),
                    "messages_count": session.messages_count,
                    "current_phase": session.current_phase
                }
                for session in candidate_sessions
            ]
            
            # Prepare chat history (enhanced with session context)
            chat_history = []
            for session in candidate_sessions:
                # Add user messages based on session context
                if session.agent_type.value == "guru":
                    chat_history.append({
                        "role": "user", 
                        "content": "I want to learn programming and improve my technical skills. Help me with algorithms and software development.",
                        "session_id": session.session_id
                    })
                elif session.agent_type.value == "parikshak":
                    chat_history.append({
                        "role": "user", 
                        "content": "I need help preparing for technical interviews. Can you help me practice coding questions and improve my interview skills?",
                        "session_id": session.session_id
                    })
                else:  # mitra
                    chat_history.append({
                        "role": "user", 
                        "content": "I'm looking for guidance and support in my learning journey. Help me stay motivated.",
                        "session_id": session.session_id
                    })
            
            logger.info(f"📊 Analyzing {len(session_data)} sessions and {len(chat_history)} interactions")
            
            # Generate AI analysis
            ai_analysis = await ai_progress.analyze_progress(candidate_id, session_data, chat_history)
            
            logger.info(f"✅ AI analysis completed: {ai_analysis.overall_progress_score:.1f}% progress")
            
            # Enhance basic progress with AI insights
            enhanced_progress = {
                **basic_progress,
                "ai_analysis": {
                    "overall_progress_score": ai_analysis.overall_progress_score,
                    "learning_velocity": ai_analysis.learning_velocity,
                    "engagement_level": ai_analysis.engagement_level,
                    "primary_learning_style": ai_analysis.primary_learning_style.value,
                    "skill_assessments": [
                        {
                            "skill_name": skill.skill_name,
                            "current_level": skill.current_level.value,
                            "sessions_count": skill.sessions_count,
                            "improvement_rate": skill.improvement_rate,
                            "confidence_score": skill.confidence_score
                        }
                        for skill in ai_analysis.skill_assessments
                    ],
                    "key_insights": [
                        {
                            "type": insight.insight_type,
                            "title": insight.title,
                            "description": insight.description,
                            "confidence": insight.confidence,
                            "agent_source": insight.agent_source,
                            "suggested_actions": insight.suggested_actions
                        }
                        for insight in ai_analysis.key_insights
                    ],
                    "guru_recommendations": ai_analysis.guru_recommendations,
                    "parikshak_recommendations": ai_analysis.parikshak_recommendations,
                    "next_milestone": ai_analysis.next_milestone,
                    "estimated_completion_time": ai_analysis.estimated_completion_time
                }
            }
            
            logger.info(f"🎯 Enhanced progress with {len(ai_analysis.skill_assessments)} skills and {len(ai_analysis.key_insights)} insights")
            return enhanced_progress
            
        except Exception as e:
            logger.error(f"❌ AI progress analysis failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall back to basic progress
            return basic_progress
    
    async def switch_agent(
        self, 
        current_session_id: str, 
        new_agent_type: AgentType,
        transition_message: Optional[str] = None
    ) -> SessionContext:
        """Switch to a different agent while maintaining context"""
        
        current_session = self.active_sessions.get(current_session_id)
        if not current_session:
            raise ValueError(f"Session {current_session_id} not found")
            
        candidate_id = current_session.candidate_id
        
        # End current session
        await self.add_message(
            current_session_id,
            "system",
            transition_message or f"Transitioning from {current_session.agent_type.value} to {new_agent_type.value}",
            current_session.agent_type
        )
        
        # Start new session with new agent
        new_session = await self.start_session(
            candidate_id, 
            new_agent_type, 
            current_session.session_type
        )
        
        # Copy relevant context
        if new_session.context_data is None:
            new_session.context_data = {}
        new_session.context_data.update({
            "previous_session_id": current_session_id,
            "transition_reason": transition_message,
            "previous_agent": current_session.agent_type.value
        })
        
        logger.info(f"Switched from {current_session.agent_type.value} to {new_agent_type.value} for candidate {candidate_id}")
        return new_session
    
    async def end_session(self, session_id: str, summary: Optional[str] = None) -> Dict[str, Any]:
        """End a session and generate summary"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
            
        # Generate session summary
        messages = self.message_history.get(session_id, [])
        duration = (datetime.now() - session.started_at).total_seconds()
        
        session_summary = {
            "session_id": session_id,
            "candidate_id": session.candidate_id,
            "agent_type": session.agent_type.value,
            "session_type": session.session_type.value,
            "duration_seconds": duration,
            "messages_count": len(messages),
            "started_at": session.started_at.isoformat(),
            "ended_at": datetime.now().isoformat(),
            "summary": summary
        }
        
        # Clean up active session
        del self.active_sessions[session_id]
        
        # Keep message history for analytics
        logger.info(f"Ended session {session_id}")
        return session_summary

# Global MCP manager instance
mcp_manager = MCPManager()