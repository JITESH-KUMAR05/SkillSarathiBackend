"""
Enhanced Chat API with MCP Integration
=====================================

Integrates MCP for multi-agent management with voice generation.
Supports all three agents: Mitra, Guru, and Parikshak.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
from pydantic import BaseModel
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Import voice and agent systems
from app.murf_streaming import murf_client
from app.voice_performance import performance_monitor
import uuid
from app.voice_config import get_agent_voice, get_voice_info
from app.llm.azure_openai_service import azure_openai_service
from app.mcp_integration import mcp_manager, AgentType, CandidateProfile
from app.database.base import AsyncSessionLocal
from app.database import models

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class EnhancedChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None  # If provided, use existing session
    candidate_id: Optional[str] = None  # For new sessions
    agent_type: str = "mitra"
    voice_enabled: bool = False

class EnhancedChatResponse(BaseModel):
    response: str
    session_id: str
    candidate_id: str
    agent_type: str
    voice_id: str
    voice_info: Dict[str, Any]
    timestamp: str
    audio_available: bool = False
    message_id: str

# Agent configurations with detailed system prompts
AGENT_CONFIGS = {
    "mitra": {
        "name": "Mitra (मित्र)",
        "description": "Your friendly AI companion for emotional support and daily conversations",
        "personality": "warm, caring, empathetic, uses Hindi phrases naturally",
        "system_prompt": """You are Mitra (मित्र), a warm and caring AI friend for Indian users. 
        You provide emotional support, listen to problems, and offer friendly advice. 
        Speak in a mix of Hindi and English naturally. Be empathetic and understanding.
        
        Your role:
        - Provide emotional support and companionship
        - Listen actively to user concerns
        - Offer gentle advice and encouragement
        - Use Hindi phrases naturally (like "हाँ", "अच्छा", "समझ गया")
        - Be culturally sensitive to Indian context
        - Maintain a warm, friendly tone
        
        Keep responses conversational and supportive."""
    },
    "guru": {
        "name": "Guru (गुरु)",
        "description": "Your learning mentor for education and skill development",
        "personality": "knowledgeable, patient, encouraging, educational",
        "system_prompt": """You are Guru (गुरु), an AI learning mentor specializing in education and skill development for Indian students. 
        Help with studies, career guidance, and learning new skills. Be patient, encouraging, and provide structured learning advice.
        
        Your role:
        - Provide educational guidance and mentorship
        - Help with academic subjects and skill development
        - Offer career advice and learning paths
        - Break down complex topics into simple explanations
        - Encourage continuous learning and growth
        - Provide practical study tips and resources
        - Support Indian educational context and competitive exams
        
        Be patient, encouraging, and focus on practical learning outcomes."""
    },
    "parikshak": {
        "name": "Parikshak (परीक्षक)",
        "description": "Your interview coach and technical assessor",
        "personality": "professional, analytical, constructive, thorough",
        "system_prompt": """You are Parikshak (परीक्षक), an AI interview coach and technical assessor. 
        Help with interview preparation, conduct mock interviews, and provide technical assessments.
        
        Your role:
        - Conduct mock interviews and assessments
        - Provide constructive feedback on responses
        - Help improve communication and technical skills
        - Assess candidate readiness for interviews
        - Offer specific improvement suggestions
        - Guide on interview best practices
        - Evaluate technical knowledge and problem-solving
        
        Be professional, analytical, and provide actionable feedback."""
    }
}

async def generate_ai_response(
    agent_type: str, 
    message: str, 
    conversation_history: Optional[list] = None,
    user_profile: Optional[dict] = None
) -> str:
    """Generate AI response using the specified agent configuration with user context"""
    
    config = AGENT_CONFIGS.get(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    # Build enhanced system prompt with user context
    system_prompt = config["system_prompt"]
    
    # Add personalization context if user profile is available
    if user_profile:
        personalization_context = f"""

USER PROFILE CONTEXT:
- Name: {user_profile.get('name', 'User')}
- Skills/Interests: {', '.join(user_profile.get('skills', []))}
- Experience Level: {user_profile.get('experience_level', 'Not specified')}
- Target Role: {user_profile.get('target_role', 'Not specified')}
- Learning Goals: {user_profile.get('learning_goals', 'Not specified')}

Please use this information to provide personalized, relevant responses that match the user's background and goals. Reference their skills and interests when appropriate, and tailor your advice to their experience level."""
        
        system_prompt += personalization_context
    
    # Build conversation context
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history if available
    if conversation_history:
        # Add recent messages for context (limit to last 5 exchanges)
        recent_messages = conversation_history[-10:]  # Last 5 exchanges (user + assistant)
        for msg in recent_messages:
            if msg.role in ["user", "assistant"]:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
    
    # Add current user message
    messages.append({"role": "user", "content": message})
    
    try:
        # Generate response using Azure OpenAI
        response_generator = azure_openai_service.generate_response(
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        # Collect the response from the async generator
        response_parts = []
        async for chunk in response_generator:
            response_parts.append(chunk)
        
        response = "".join(response_parts)
        return response
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return f"I apologize, but I'm experiencing some technical difficulties. Please try again."

async def get_or_create_user_session(user_id: str, db: AsyncSession) -> models.User:
    """Get existing user or create anonymous session"""
    try:
        # Try to get existing user
        result = await db.execute(
            select(models.User).where(models.User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            return user
        
        # Create anonymous user session
        anonymous_user = models.User(
            id=user_id,
            username=f"user_{user_id[:8]}",
            email=f"{user_id}@temp.local",
            hashed_password="temp_hash",
            full_name="Anonymous User",
            is_active=True,
            is_verified=False
        )
        
        db.add(anonymous_user)
        await db.commit()
        await db.refresh(anonymous_user)
        
        logger.info(f"✅ Created anonymous session for {user_id}")
        return anonymous_user
        
    except Exception as e:
        logger.error(f"❌ User session error: {e}")
        await db.rollback()
        raise

@router.post("/enhanced", response_model=EnhancedChatResponse)
async def enhanced_chat(message_data: EnhancedChatMessage, background_tasks: BackgroundTasks):
    """Enhanced chat with MCP integration for all agents"""
    
    try:
        # Validate agent type
        try:
            agent_type_enum = AgentType(message_data.agent_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {message_data.agent_type}")
        
        session_id = message_data.session_id
        candidate_id = message_data.candidate_id
        
        # Handle session management
        if session_id:
            # Use existing session
            session_context = await mcp_manager.get_session_context(session_id)
            if not session_context:
                raise HTTPException(status_code=404, detail="Session not found")
            candidate_id = session_context.candidate_id
        else:
            # Create new session
            if not candidate_id:
                # Create anonymous candidate for testing
                candidate_id = f"anon_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Register in MCP first
                await mcp_manager.register_candidate(
                    name="Anonymous User",
                    email=f"{candidate_id}@temp.local"
                )
            else:
                # Check if candidate exists in MCP, if not register from database
                if candidate_id not in mcp_manager.candidate_profiles:
                    # Try to get user from database
                    async with AsyncSessionLocal() as db:
                        user = await db.get(models.User, candidate_id)
                        if user:
                            # Register in MCP using existing user info
                            from app.mcp_integration import CandidateProfile
                            # Convert user.interests from SQLAlchemy column to list
                            user_interests = []
                            try:
                                interests_value = getattr(user, 'interests', None)
                                if interests_value is not None:
                                    if isinstance(interests_value, str):
                                        import json
                                        user_interests = json.loads(interests_value)
                                    elif isinstance(interests_value, list):
                                        user_interests = interests_value
                            except:
                                user_interests = []
                            
                            candidate_profile = CandidateProfile(
                                candidate_id=candidate_id,
                                name=str(user.full_name or user.username or "User"),
                                email=str(user.email),
                                skills=user_interests
                            )
                            mcp_manager.candidate_profiles[candidate_id] = candidate_profile
                            logger.info(f"Registered existing user in MCP: {candidate_id}")
                        else:
                            raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found in database")
            
            # Create new session with the candidate
            session_context = await mcp_manager.start_session(
                candidate_id=candidate_id,
                agent_type=agent_type_enum
            )
            session_id = session_context.session_id
        
        # Get conversation history for context
        conversation_history = await mcp_manager.get_conversation_history(session_id, limit=10)
        
        # Get user profile for personalization
        user_profile = None
        if candidate_id in mcp_manager.candidate_profiles:
            profile = mcp_manager.candidate_profiles[candidate_id]
            user_profile = {
                'name': profile.name,
                'skills': profile.skills,
                'experience_level': getattr(profile, 'experience_level', 'Not specified'),
                'target_role': getattr(profile, 'target_role', 'Not specified'),
                'learning_goals': getattr(profile, 'learning_goals', 'Not specified')
            }
        
        # Add user message to MCP
        user_message = await mcp_manager.add_message(
            session_id=session_id,
            role="user",
            content=message_data.message,
            agent_type=agent_type_enum
        )
        
        # Generate AI response with user context
        ai_response = await generate_ai_response(
            agent_type=message_data.agent_type,
            message=message_data.message,
            conversation_history=conversation_history,
            user_profile=user_profile
        )
        
        # Get voice configuration
        voice_config = get_agent_voice(message_data.agent_type)
        voice_id = voice_config.get("voice_id", "hi-IN-shweta")
        voice_info = get_voice_info(voice_id) or voice_config
        
        # Add AI response to MCP
        response_metadata = {
            "voice_id": voice_id,
            "voice_enabled": message_data.voice_enabled,
            "agent_config": AGENT_CONFIGS[message_data.agent_type]["name"]
        }
        
        ai_message = await mcp_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            agent_type=agent_type_enum,
            metadata=response_metadata
        )
        
        response_data = EnhancedChatResponse(
            response=ai_response,
            session_id=session_id,
            candidate_id=candidate_id,
            agent_type=message_data.agent_type,
            voice_id=voice_id,
            voice_info=voice_info,
            timestamp=datetime.now().isoformat(),
            audio_available=False,
            message_id=ai_message.message_id
        )
        
        # Generate voice in background if enabled
        if message_data.voice_enabled:
            background_tasks.add_task(
                generate_voice_optimized,
                ai_response,
                message_data.agent_type,
                candidate_id
            )
            response_data.audio_available = True
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")

async def generate_voice_optimized(text: str, agent_type: str, user_id: str) -> Optional[bytes]:
    """
    Optimized voice generation with <500ms latency target
    Uses direct streaming for immediate response
    """
    session_id = str(uuid.uuid4())
    metrics = performance_monitor.start_session(session_id, agent_type, text)
    
    try:
        logger.info(f"🎤 Starting optimized voice generation for {agent_type}")
        
        # Use streaming client for ultra-low latency
        audio_chunks = []
        chunk_count = 0
        first_chunk_recorded = False
        
        async for chunk in murf_client.stream_text_to_speech(
            text=text,
            user_id=user_id,
            agent_type=agent_type
        ):
            if chunk and len(chunk) > 0:
                audio_chunks.append(chunk)
                chunk_count += 1
                
                # Record performance metrics
                if not first_chunk_recorded:
                    performance_monitor.record_first_chunk(session_id, len(chunk))
                    first_chunk_recorded = True
                else:
                    performance_monitor.record_chunk(session_id, len(chunk))
        
        # Combine all chunks
        if audio_chunks:
            total_audio = b''.join(audio_chunks)
            performance_monitor.complete_session(session_id, success=True)
            logger.info(f"✅ Voice generation completed, {len(total_audio)} bytes")
            return total_audio
        else:
            performance_monitor.complete_session(session_id, success=False, error="No audio chunks received")
            logger.warning("❌ No audio chunks received from streaming")
            return None
            
    except Exception as e:
        performance_monitor.complete_session(session_id, success=False, error=str(e))
        logger.error(f"❌ Voice generation failed: {str(e)}")
        return None

@router.get("/agents/info")
async def get_agent_info():
    """Get information about all available agents"""
    
    agents = []
    for agent_type, config in AGENT_CONFIGS.items():
        voice_config = get_agent_voice(agent_type)
        voice_id = voice_config.get("voice_id", "hi-IN-shweta")
        voice_info = get_voice_info(voice_id) or voice_config
        
        agents.append({
            "agent_type": agent_type,
            "name": config["name"],
            "description": config["description"],
            "personality": config["personality"],
            "voice_id": voice_id,
            "voice_name": voice_info.get("description", "Unknown"),
            "language": voice_info.get("language", "Unknown"),
            "accent": voice_info.get("gender", "Unknown")
        })
    
    return {"agents": agents}

@router.get("/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get a summary of the session including key metrics"""
    
    try:
        # Get session context
        session_context = await mcp_manager.get_session_context(session_id)
        if not session_context:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get conversation history
        messages = await mcp_manager.get_conversation_history(session_id, limit=0)  # Get all messages
        
        # Calculate metrics
        user_messages = [msg for msg in messages if msg.role == "user"]
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        
        duration = (datetime.now() - session_context.started_at).total_seconds()
        
        summary = {
            "session_id": session_id,
            "candidate_id": session_context.candidate_id,
            "agent_type": session_context.agent_type.value,
            "started_at": session_context.started_at.isoformat(),
            "duration_seconds": duration,
            "current_phase": session_context.current_phase,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "agent_info": AGENT_CONFIGS.get(session_context.agent_type.value, {})
        }
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get session summary")

# Legacy endpoint for backward compatibility
@router.post("/", response_model=EnhancedChatResponse)
@router.post("/send", response_model=EnhancedChatResponse)
async def legacy_chat(message_data: EnhancedChatMessage, background_tasks: BackgroundTasks):
    """Legacy chat endpoint for backward compatibility"""
    return await enhanced_chat(message_data, background_tasks)