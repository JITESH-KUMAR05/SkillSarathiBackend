"""
Enhanced Backend API for Advanced Multi-Agent Platform
Supports voice, video, RAG, and interview monitoring
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import json
import base64
from datetime import datetime
import os
import tempfile
import uuid
import logging

# Get logger
logger = logging.getLogger(__name__)

# Import existing modules
from app.llm.llm_factory import get_llm
from app.rag.enhanced_rag_system import EnhancedRAGSystem
from app.database.models import User, Conversation, Message, Document
from app.database.base import get_async_session

# Pydantic models for API
class ChatRequest(BaseModel):
    message: str
    agent: str
    user_id: Optional[str] = "default_user"
    context: Optional[str] = ""
    voice_enabled: Optional[bool] = False
    
class ChatResponse(BaseModel):
    response: str
    agent: str
    success: bool
    user_id: str
    timestamp: str
    conversation_id: Optional[str] = None

class UserProfile(BaseModel):
    name: str
    skills: List[str]
    experience: str
    goals: List[str]
    
class VoiceRequest(BaseModel):
    audio_data: str  # Base64 encoded audio
    agent: str
    user_id: Optional[str] = "default_user"
    
class VideoFrame(BaseModel):
    frame_data: str  # Base64 encoded image
    timestamp: str
    user_id: str

class InterviewSession(BaseModel):
    user_id: str
    question_type: str
    duration: int
    monitoring_enabled: bool

# Initialize RAG system
rag_system = EnhancedRAGSystem()

class AdvancedAPIEndpoints:
    """Enhanced API endpoints for advanced features"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.setup_routes()
        
    def setup_routes(self):
        """Setup all enhanced API routes"""
        
        @self.app.post("/api/chat/enhanced", response_model=ChatResponse)
        async def enhanced_chat(request: ChatRequest):
            """Enhanced chat with RAG context and user profiling"""
            try:
                # Use user_id safely
                user_id_safe = request.user_id or "default_user"
                
                # Build context from RAG system
                context_chunks = []
                if request.context:
                    context_chunks.append(f"Current context: {request.context}")
                
                # Query RAG system for relevant context
                try:
                    rag_context = rag_system.query_with_context(
                        query=request.message,
                        user_id=user_id_safe,
                        agent_context=request.agent,
                        max_results=3
                    )
                    
                    if rag_context:
                        context_chunks.extend([doc["content"][:300] for doc in rag_context])
                except Exception as e:
                    logger.warning(f"RAG query failed: {e}")
                
                # Build enhanced prompt
                full_context = "\n".join(context_chunks)
                enhanced_message = f"""
                Context from previous conversations and knowledge:
                {full_context}
                
                Current user message: {request.message}
                
                Respond as {request.agent} agent with awareness of the above context.
                """
                
                # Get LLM response
                llm = get_llm()
                ai_response = llm.generate_response(enhanced_message)
                
                # Store in RAG system for future context
                try:
                    rag_system.add_conversation(
                        user_id=user_id_safe,
                        agent_type=request.agent,
                        user_message=request.message,
                        ai_response=ai_response,
                        metadata={
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    logger.warning(f"RAG storage failed: {e}")
                
                return ChatResponse(
                    response=ai_response,
                    agent=request.agent,
                    success=True,
                    user_id=user_id_safe,
                    timestamp=datetime.now().isoformat(),
                    conversation_id=str(uuid.uuid4())
                )
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
        
        @self.app.post("/api/user/profile")
        async def update_user_profile(user_id: str, profile: UserProfile):
            """Update user profile for RAG context"""
            try:
                # Store profile in RAG system
                profile_data = {
                    "name": profile.name,
                    "skills": profile.skills,
                    "experience": profile.experience,
                    "goals": profile.goals,
                    "updated_at": datetime.now().isoformat()
                }
                
                rag_system.store_user_profile(user_id, profile_data)
                
                return {"status": "success", "message": "Profile updated"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Profile update error: {str(e)}")
        
        @self.app.get("/api/user/profile/{user_id}")
        async def get_user_profile(user_id: str):
            """Get user profile and conversation summary"""
            try:
                # Get profile from RAG
                profile = rag_system.get_user_profile(user_id)
                
                # Return simplified stats for now
                stats = {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "agents_used": ["mentor", "therapist", "interview"],
                    "recent_activity": datetime.now().isoformat()
                }
                
                return {
                    "profile": profile or {},
                    "stats": stats
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Profile retrieval error: {str(e)}")
        
        @self.app.post("/api/voice/transcribe")
        async def transcribe_voice(request: VoiceRequest):
            """Transcribe voice input to text"""
            try:
                # Decode audio data
                audio_data = base64.b64decode(request.audio_data)
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                    tmp_file.write(audio_data)
                    tmp_file_path = tmp_file.name
                
                # Here you would integrate with a speech-to-text service
                # For now, return a placeholder
                transcribed_text = "Voice transcription would be processed here"
                
                # Clean up
                os.unlink(tmp_file_path)
                
                return {
                    "transcribed_text": transcribed_text,
                    "user_id": request.user_id,
                    "agent": request.agent,
                    "status": "success"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Voice transcription error: {str(e)}")
        
        @self.app.post("/api/video/analyze")
        async def analyze_video_frame(frame: VideoFrame):
            """Analyze video frame for interview monitoring"""
            try:
                # Decode image data
                image_data = base64.b64decode(frame.frame_data)
                
                # Here you would integrate with computer vision for:
                # - Face detection
                # - Multiple person detection
                # - Eye tracking
                # - Phone/device detection
                
                analysis_result = {
                    "faces_detected": 1,
                    "multiple_people": False,
                    "looking_away": False,
                    "device_detected": False,
                    "cheating_score": 0.1,
                    "alerts": [],
                    "timestamp": frame.timestamp
                }
                
                return analysis_result
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Video analysis error: {str(e)}")
        
        @self.app.post("/api/interview/start")
        async def start_interview_session(session: InterviewSession):
            """Start an interview session with monitoring"""
            try:
                # Store interview session data
                interview_data = {
                    "user_id": session.user_id,
                    "question_type": session.question_type,
                    "duration": session.duration,
                    "monitoring_enabled": session.monitoring_enabled,
                    "started_at": datetime.now().isoformat(),
                    "status": "active"
                }
                
                # Store in RAG for context
                try:
                    rag_system.store_interview_session(session.user_id, interview_data)
                except Exception as e:
                    logger.warning(f"RAG interview storage failed: {e}")
                
                return {
                    "session_id": str(uuid.uuid4()),
                    "status": "started",
                    "message": "Interview session initialized"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Interview start error: {str(e)}")
        
        @self.app.post("/api/documents/upload")
        async def upload_document(file: UploadFile = File(...), user_id: str = "default_user"):
            """Upload and process documents for RAG"""
            try:
                # Read file content
                content = await file.read()
                
                # Save file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp_file:
                    tmp_file.write(content)
                    tmp_file_path = tmp_file.name
                
                # Process with RAG system
                await rag_system.add_document(
                    content=content.decode('utf-8'),
                    user_id=user_id,
                    metadata={
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "uploaded_at": datetime.now().isoformat()
                    }
                )
                
                # Clean up
                os.unlink(tmp_file_path)
                
                return {
                    "status": "success",
                    "filename": file.filename,
                    "message": "Document processed and stored"
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Document upload error: {str(e)}")
        
        @self.app.get("/api/rag/search")
        async def search_rag_context(query: str, user_id: str = "default_user", limit: int = 5):
            """Search RAG system for relevant context"""
            try:
                results = rag_system.query_with_context(
                    query=query,
                    user_id=user_id,
                    max_results=limit
                )
                
                return {
                    "query": query,
                    "results": results,
                    "count": len(results)
                }
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"RAG search error: {str(e)}")

# Function to add enhanced endpoints to existing app
def add_enhanced_endpoints(app: FastAPI):
    """Add enhanced endpoints to the main FastAPI app"""
    enhanced_api = AdvancedAPIEndpoints(app)
    return app
