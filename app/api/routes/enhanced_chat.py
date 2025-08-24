"""
Enhanced Multi-Agent Chat API
Supports Mitra (Companion), Guru (Mentor), and Parikshak (Interview) agents
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
import json
import asyncio
from datetime import datetime

from app.database.base import get_db
from app.database import models, schemas
from app.auth.dependencies import get_current_active_user
from app.agents.multi_agent_system import MultiAgentOrchestrator, AgentType
from app.rag.enhanced_rag_system import enhanced_rag_system

router = APIRouter()


@router.post("/chat/message", response_class=StreamingResponse)
async def send_message(
    message_data: schemas.ChatMessage,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send a message to the multi-agent system with streaming response
    Automatically routes to appropriate agent (Mitra/Guru/Parikshak)
    """
    try:
        # Initialize multi-agent orchestrator
        orchestrator = MultiAgentOrchestrator(enhanced_rag_system)
        
        # Create or get conversation
        conversation = await _get_or_create_conversation(
            db, current_user.id, message_data.conversation_id, message_data.agent_type
        )
        
        # Prepare session context
        session_context = {
            "conversation_type": message_data.agent_type or "general",
            "user_preferences": message_data.context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add any document analysis context if provided
        if message_data.document_id:
            doc_context = await _get_document_context(db, message_data.document_id, current_user.id)
            if doc_context:
                session_context["document_analysis"] = doc_context
        
        # Store user message in database
        user_message = models.Message(
            conversation_id=conversation.id,
            sender_type="user",
            content=message_data.content,
            timestamp=datetime.utcnow()
        )
        db.add(user_message)
        await db.commit()
        
        # Process through multi-agent system with streaming
        async def generate_response():
            accumulated_response = ""
            
            async for chunk in orchestrator.process_message(
                user_id=str(current_user.id),
                conversation_id=str(conversation.id),
                message=message_data.content,
                session_context=session_context
            ):
                accumulated_response += chunk
                yield f"data: {json.dumps({'content': chunk, 'type': 'chunk'})}\n\n"
            
            # Store agent response in database
            agent_message = models.Message(
                conversation_id=conversation.id,
                sender_type="agent",
                content=accumulated_response,
                timestamp=datetime.utcnow(),
                metadata={"agent_type": session_context.get("conversation_type", "general")}
            )
            db.add(agent_message)
            await db.commit()
            
            # Add conversation context to RAG
            await enhanced_rag_system.add_conversation_context(
                user_id=str(current_user.id),
                conversation_id=str(conversation.id),
                content=f"User: {message_data.content}\nAgent: {accumulated_response}"
            )
            
            yield f"data: {json.dumps({'type': 'done', 'message_id': agent_message.id})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


@router.post("/chat/agent-switch")
async def switch_agent(
    switch_data: schemas.AgentSwitchRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Explicitly switch to a specific agent (Mitra/Guru/Parikshak)
    """
    try:
        # Validate agent type
        if switch_data.agent_type not in [AgentType.COMPANION, AgentType.MENTOR, AgentType.INTERVIEW]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid agent type. Must be 'companion', 'mentor', or 'interview'"
            )
        
        # Get or create conversation for the specific agent
        conversation = await _get_or_create_conversation(
            db, current_user.id, switch_data.conversation_id, switch_data.agent_type
        )
        
        # Get agent-specific greeting and context
        orchestrator = MultiAgentOrchestrator(enhanced_rag_system)
        
        # Generate context-aware greeting
        user_profile = await enhanced_rag_system.get_user_profile(str(current_user.id))
        
        agent_greetings = {
            AgentType.COMPANION: f"Hi! I'm Mitra, your personal companion. Great to see you again! How are you feeling today?",
            AgentType.MENTOR: f"Hello! I'm Guru, your professional mentor. Ready to work on your career goals and skill development?",
            AgentType.INTERVIEW: f"Hi! I'm Parikshak, your interview coach. Let's prepare you for success! What interview are you preparing for?"
        }
        
        greeting = agent_greetings.get(switch_data.agent_type, "Hello! How can I help you today?")
        
        # Store agent greeting as message
        agent_message = models.Message(
            conversation_id=conversation.id,
            sender_type="agent",
            content=greeting,
            timestamp=datetime.utcnow(),
            metadata={"agent_type": switch_data.agent_type, "message_type": "greeting"}
        )
        db.add(agent_message)
        await db.commit()
        
        return {
            "conversation_id": conversation.id,
            "agent_type": switch_data.agent_type,
            "greeting": greeting,
            "agent_capabilities": _get_agent_capabilities(switch_data.agent_type)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching agent: {str(e)}"
        )


@router.get("/chat/agent-suggestions")
async def get_agent_suggestions(
    conversation_id: Optional[str] = None,
    current_user: models.User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized suggestions for agent interactions based on user profile
    """
    try:
        orchestrator = MultiAgentOrchestrator(enhanced_rag_system)
        
        # Get recent conversation context if provided
        current_context = ""
        if conversation_id:
            recent_messages = await _get_recent_conversation_context(db, conversation_id)
            current_context = " ".join(recent_messages)
        
        suggestions = await orchestrator.get_agent_suggestions(
            user_id=str(current_user.id),
            current_context=current_context
        )
        
        return {
            "suggestions": suggestions,
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting suggestions: {str(e)}"
        )


@router.post("/chat/update-profile")
async def update_user_profile(
    profile_data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Update user profile for personalized agent interactions
    """
    try:
        # Convert Pydantic model to dict
        profile_dict = profile_data.dict(exclude_unset=True)
        
        # Update profile in RAG system
        profile_id = await enhanced_rag_system.create_user_profile(
            user_id=str(current_user.id),
            profile_data=profile_dict
        )
        
        return {
            "profile_id": profile_id,
            "message": "Profile updated successfully",
            "updated_fields": list(profile_dict.keys())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )


@router.get("/chat/interaction-summary")
async def get_interaction_summary(
    days: int = 30,
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get summary of user interactions with different agents
    """
    try:
        summary = await enhanced_rag_system.get_user_interaction_summary(
            user_id=str(current_user.id),
            days=days
        )
        
        return {
            "summary": summary,
            "user_id": current_user.id,
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )


# Helper functions

async def _get_or_create_conversation(
    db: AsyncSession, 
    user_id: int, 
    conversation_id: Optional[str], 
    agent_type: Optional[str]
) -> models.Conversation:
    """Get existing conversation or create new one"""
    
    if conversation_id:
        # Try to get existing conversation
        result = await db.execute(
            "SELECT * FROM conversations WHERE id = :id AND user_id = :user_id",
            {"id": conversation_id, "user_id": user_id}
        )
        conversation = result.first()
        if conversation:
            return conversation
    
    # Create new conversation
    conversation = models.Conversation(
        user_id=user_id,
        title=f"Chat with {agent_type or 'AI Assistant'}",
        created_at=datetime.utcnow(),
        metadata={"agent_type": agent_type or "general"}
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    
    return conversation


async def _get_document_context(db: AsyncSession, document_id: str, user_id: int) -> Optional[str]:
    """Get document context for analysis"""
    try:
        result = await db.execute(
            "SELECT content, doc_metadata FROM documents WHERE id = :id AND user_id = :user_id",
            {"id": document_id, "user_id": user_id}
        )
        document = result.first()
        
        if document:
            return f"Document analysis context: {document.content[:500]}..."
        
    except Exception:
        pass
    
    return None


async def _get_recent_conversation_context(db: AsyncSession, conversation_id: str) -> List[str]:
    """Get recent messages from conversation for context"""
    try:
        result = await db.execute(
            """
            SELECT content FROM messages 
            WHERE conversation_id = :conversation_id 
            ORDER BY timestamp DESC 
            LIMIT 5
            """,
            {"conversation_id": conversation_id}
        )
        messages = result.fetchall()
        return [msg.content for msg in messages]
        
    except Exception:
        return []


def _get_agent_capabilities(agent_type: str) -> Dict[str, Any]:
    """Get agent-specific capabilities and features"""
    capabilities = {
        AgentType.COMPANION: [
            "Personal conversation and emotional support",
            "Cultural context and Indian communication patterns",
            "Family and relationship discussions",
            "Lifestyle and hobby conversations",
            "Bilingual support (English/Hindi)",
            "Festival and cultural event discussions"
        ],
        AgentType.MENTOR: [
            "Career guidance and planning",
            "Technical concept explanations",
            "Skill development recommendations",
            "Resume and LinkedIn optimization",
            "Indian job market insights",
            "Learning path creation",
            "Professional communication coaching"
        ],
        AgentType.INTERVIEW: [
            "Mock technical interviews",
            "Behavioral interview practice",
            "Communication skills assessment",
            "Performance feedback and scoring",
            "Company-specific interview prep",
            "Real-time interview simulation",
            "Improvement recommendations"
        ]
    }
    
    agent_names = {
        AgentType.COMPANION: "Mitra (Companion)",
        AgentType.MENTOR: "Guru (Mentor)", 
        AgentType.INTERVIEW: "Parikshak (Interviewer)"
    }
    
    return {
        "features": capabilities.get(AgentType(agent_type), []),
        "agent_name": agent_names.get(AgentType(agent_type), "AI Assistant")
    }
