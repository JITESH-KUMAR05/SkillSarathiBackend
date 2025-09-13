"""
Advanced AI Features API
Endpoints for video generation, audio transcription, and model capabilities
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import os
import tempfile

from app.llm.azure_openai_service import azure_openai_service
from app.services.video_interview_service import video_interview_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai-features", tags=["Advanced AI Features"])

# Request/Response Models
class VideoGenerationRequest(BaseModel):
    prompt: str
    height: int = 1080
    width: int = 1080
    duration: int = 5
    variants: int = 1

class InterviewVideoRequest(BaseModel):
    scenario_type: str = "technical"
    scenario_subtype: str = "coding"
    custom_prompt: Optional[str] = None
    duration: int = 10

class PracticeQuestionsRequest(BaseModel):
    job_role: str
    difficulty_level: str = "intermediate"
    question_count: int = 3

class TranscriptionResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration: float

@router.get("/capabilities")
async def get_ai_capabilities():
    """Get information about available AI models and capabilities"""
    try:
        capabilities = await azure_openai_service.get_model_capabilities()
        return {
            "status": "success",
            "capabilities": capabilities,
            "features": {
                "model_router": "Automatic model selection (GPT-5, GPT-4.1, etc.)",
                "video_generation": "Sora-powered video creation",
                "audio_transcription": "GPT-4o-Transcribe with 16k context",
                "realtime_audio": "Speech-to-speech conversations",
                "interview_scenarios": "Pre-built interview video templates"
            }
        }
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/generate")
async def generate_video(request: VideoGenerationRequest):
    """Generate video using Sora model"""
    try:
        result = await azure_openai_service.generate_video(
            prompt=request.prompt,
            height=request.height,
            width=request.width,
            duration=request.duration,
            variants=request.variants
        )
        
        return {
            "status": "success",
            "video_job": result,
            "message": "Video generation started. Check job status for completion."
        }
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/interview-scenario")
async def generate_interview_video(request: InterviewVideoRequest):
    """Generate interview scenario video using pre-built templates"""
    try:
        result = await video_interview_service.generate_interview_video(
            scenario_type=request.scenario_type,
            scenario_subtype=request.scenario_subtype,
            custom_prompt=request.custom_prompt,
            duration=request.duration
        )
        
        return {
            "status": "success",
            "interview_video": result,
            "message": "Interview scenario video generation started."
        }
    except Exception as e:
        logger.error(f"Interview video error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/video/practice-questions")
async def generate_practice_questions_video(request: PracticeQuestionsRequest):
    """Generate practice interview questions video"""
    try:
        result = await video_interview_service.generate_practice_questions_video(
            job_role=request.job_role,
            difficulty_level=request.difficulty_level,
            question_count=request.question_count
        )
        
        return {
            "status": "success",
            "practice_video": result,
            "message": "Practice questions video generation started."
        }
    except Exception as e:
        logger.error(f"Practice questions video error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/scenarios")
async def get_interview_scenarios():
    """Get available interview scenarios"""
    try:
        scenarios = await video_interview_service.get_available_scenarios()
        return {
            "status": "success",
            "scenarios": scenarios
        }
    except Exception as e:
        logger.error(f"Error getting scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/audio/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language: str = Form("en")
):
    """Transcribe audio using GPT-4o-Transcribe"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Transcribe audio
            result = await azure_openai_service.transcribe_audio(
                audio_file_path=tmp_file_path,
                language=language
            )
            
            return {
                "status": "success",
                "transcription": result,
                "original_filename": audio_file.filename,
                "language": language
            }
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/enhanced")
async def enhanced_chat(
    message: str,
    agent_type: str = "mitra",
    stream: bool = False,
    max_tokens: int = 500,
    temperature: float = 0.7
):
    """Enhanced chat with model router - automatically selects best model"""
    try:
        messages = [{"role": "user", "content": message}]
        
        if stream:
            # For streaming, return SSE response
            from fastapi.responses import StreamingResponse
            import json
            
            async def generate_stream():
                async for chunk in azure_openai_service.generate_response(
                    messages=messages,
                    agent_type=agent_type,
                    stream=True,
                    max_tokens=max_tokens,
                    temperature=temperature
                ):
                    yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # Non-streaming response
            response_chunks = []
            async for chunk in azure_openai_service.generate_response(
                messages=messages,
                agent_type=agent_type,
                stream=False,
                max_tokens=max_tokens,
                temperature=temperature
            ):
                response_chunks.append(chunk)
            
            return {
                "status": "success",
                "response": "".join(response_chunks),
                "agent_type": agent_type,
                "model_router": "Automatically selected best model for this query"
            }
            
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Check health of all AI services"""
    try:
        azure_health = await azure_openai_service.health_check()
        
        return {
            "status": "healthy" if azure_health else "degraded",
            "services": {
                "azure_openai": azure_health,
                "model_router": azure_health,
                "sora_video": azure_health,
                "transcription": azure_health
            },
            "timestamp": "2025-09-12T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-09-12T12:00:00Z"
        }
