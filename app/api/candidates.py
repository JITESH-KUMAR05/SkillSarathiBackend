"""
Candidate Registration and Management API
========================================

Provides endpoints for candidate registration, profile management,
and progress tracking using MCP integration.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
import logging

from app.mcp_integration import mcp_manager, AgentType, SessionType, CandidateProfile

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class CandidateRegistrationRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    experience_level: Optional[str] = None
    target_role: Optional[str] = None
    skills: Optional[List[str]] = None

class CandidateLoginRequest(BaseModel):
    email: EmailStr

class CandidateResponse(BaseModel):
    candidate_id: str
    name: str
    email: str
    phone: Optional[str] = None
    experience_level: Optional[str] = None
    target_role: Optional[str] = None
    skills: List[str]
    preferences: Dict[str, Any]
    created_at: str

class SessionStartRequest(BaseModel):
    candidate_id: str
    agent_type: str  # mitra, guru, parikshak
    session_type: str = "chat"  # chat, interview, assessment, learning

class SessionResponse(BaseModel):
    session_id: str
    candidate_id: str
    agent_type: str
    session_type: str
    started_at: str
    current_phase: str

class ProgressResponse(BaseModel):
    candidate_profile: Dict[str, Any]
    total_sessions: int
    total_messages: int
    agents_interacted: List[str]
    recent_sessions: List[Dict[str, Any]]

@router.post("/register", response_model=CandidateResponse)
async def register_candidate(request: CandidateRegistrationRequest):
    """Register a new candidate and return their profile with unique ID"""
    
    try:
        candidate = await mcp_manager.register_candidate(
            name=request.name,
            email=request.email,
            phone=request.phone,
            experience_level=request.experience_level,
            target_role=request.target_role,
            skills=request.skills
        )
        
        return CandidateResponse(
            candidate_id=candidate.candidate_id,
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            experience_level=candidate.experience_level,
            target_role=candidate.target_role,
            skills=candidate.skills or [],
            preferences=candidate.preferences or {},
            created_at=candidate.created_at.isoformat() if candidate.created_at else datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error registering candidate: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to register candidate")

@router.post("/session/start", response_model=SessionResponse)
async def start_session(request: SessionStartRequest):
    """Start a new session with specified agent for a candidate"""
    
    try:
        # Validate agent type
        try:
            agent_type = AgentType(request.agent_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}")
        
        # Validate session type
        try:
            session_type = SessionType(request.session_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid session type: {request.session_type}")
        
        session = await mcp_manager.start_session(
            candidate_id=request.candidate_id,
            agent_type=agent_type,
            session_type=session_type
        )
        
        return SessionResponse(
            session_id=session.session_id,
            candidate_id=session.candidate_id,
            agent_type=session.agent_type.value,
            session_type=session.session_type.value,
            started_at=session.started_at.isoformat(),
            current_phase=session.current_phase
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start session")

@router.get("/candidate/{candidate_id}/progress", response_model=ProgressResponse)
async def get_candidate_progress(candidate_id: str):
    """Get comprehensive progress data for a candidate"""
    
    try:
        progress = await mcp_manager.get_candidate_progress(candidate_id)
        
        if not progress:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        return ProgressResponse(**progress)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate progress: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get progress data")

@router.get("/session/{session_id}/context")
async def get_session_context(session_id: str):
    """Get current session context"""
    
    try:
        context = await mcp_manager.get_session_context(session_id)
        
        if not context:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": context.session_id,
            "candidate_id": context.candidate_id,
            "agent_type": context.agent_type.value,
            "session_type": context.session_type.value,
            "started_at": context.started_at.isoformat(),
            "current_phase": context.current_phase,
            "messages_count": context.messages_count,
            "context_data": context.context_data or {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session context: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session context")

@router.get("/session/{session_id}/history")
async def get_conversation_history(session_id: str, limit: int = 10):
    """Get conversation history for a session"""
    
    try:
        messages = await mcp_manager.get_conversation_history(session_id, limit)
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "message_id": msg.message_id,
                    "agent_type": msg.agent_type.value,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata or {},
                    "audio_url": msg.audio_url
                }
                for msg in messages
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get conversation history")

@router.post("/session/{session_id}/switch/{new_agent_type}")
async def switch_agent(session_id: str, new_agent_type: str, transition_message: Optional[str] = None):
    """Switch to a different agent while maintaining context"""
    
    try:
        # Validate new agent type
        try:
            agent_type = AgentType(new_agent_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {new_agent_type}")
        
        new_session = await mcp_manager.switch_agent(
            current_session_id=session_id,
            new_agent_type=agent_type,
            transition_message=transition_message
        )
        
        return SessionResponse(
            session_id=new_session.session_id,
            candidate_id=new_session.candidate_id,
            agent_type=new_session.agent_type.value,
            session_type=new_session.session_type.value,
            started_at=new_session.started_at.isoformat(),
            current_phase=new_session.current_phase
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error switching agent: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to switch agent")

@router.post("/session/{session_id}/end")
async def end_session(session_id: str, summary: Optional[str] = None):
    """End a session and generate summary"""
    
    try:
        session_summary = await mcp_manager.end_session(session_id, summary)
        return session_summary
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to end session")

@router.get("/candidates")
async def list_candidates():
    """List all registered candidates"""
    
    try:
        candidates = []
        for candidate_id, candidate in mcp_manager.candidate_profiles.items():
            candidates.append({
                "candidate_id": candidate.candidate_id,
                "name": candidate.name,
                "email": candidate.email,
                "experience_level": candidate.experience_level,
                "target_role": candidate.target_role,
                "created_at": candidate.created_at.isoformat() if candidate.created_at else datetime.now().isoformat()
            })
        
        return {"candidates": candidates}
        
    except Exception as e:
        logger.error(f"Error listing candidates: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list candidates")

@router.post("/login")
async def login_candidate(request: CandidateLoginRequest):
    """
    Login existing candidate by email
    Returns candidate profile if found
    """
    try:
        # Check if candidate exists in database
        from app.database.base import AsyncSessionLocal
        from app.database.models import User
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as db:
            # Find user by email
            result = await db.execute(select(User).where(User.email == request.email))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=404, 
                    detail="Candidate not found. Please register first."
                )
            
            # Update last login
            user.last_login = datetime.now()
            await db.commit()
            
            # Return candidate information
            try:
                import json
                skills = json.loads(user.interests) if user.interests else []  # type: ignore
            except:
                skills = []
            
            return {
                "candidate_id": user.id,
                "name": user.full_name or "",
                "email": user.email,
                "phone": getattr(user, 'phone', None),
                "experience_level": getattr(user, 'experience_level', 'beginner'),
                "target_role": user.profession or "",
                "skills": skills,
                "created_at": str(user.created_at) if user.created_at else None,  # type: ignore
                "last_login": str(user.last_login) if user.last_login else None  # type: ignore
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/health")
async def health_check():
    """Health check endpoint for MCP system"""
    return {
        "status": "healthy",
        "mcp_manager": "active",
        "active_sessions": len(mcp_manager.active_sessions),
        "registered_candidates": len(mcp_manager.candidate_profiles),
        "timestamp": datetime.now().isoformat()
    }