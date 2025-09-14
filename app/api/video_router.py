"""
Video Router for BuddyAgents Platform
Handles video generation using Sora and video processing
"""

import logging
import tempfile
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.core.config import get_settings, AgentConfig
from app.core.security import rate_limit_video, AuthenticationService, InputValidator
from app.services.azure_openai_service import azure_openai_service, RegionType

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Request/Response Models
class VideoGenerationRequest(BaseModel):
    """Video generation request for Sora"""
    prompt: str
    duration: int = 5
    resolution: str = "1080p"
    style: str = "realistic"
    agent_context: Optional[str] = None
    
    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v):
        return InputValidator.sanitize_text(v, max_length=500)
    
    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        if v < 1 or v > 30:
            raise ValueError("Duration must be between 1 and 30 seconds")
        return v
    
    @field_validator("resolution")
    @classmethod
    def validate_resolution(cls, v):
        if v not in ["720p", "1080p", "4k"]:
            raise ValueError("Resolution must be 720p, 1080p, or 4k")
        return v


class VideoGenerationResponse(BaseModel):
    """Video generation response"""
    generation_id: str
    status: str
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: int
    resolution: str
    file_size_mb: Optional[float]
    model_used: str
    timestamp: str
    estimated_completion: Optional[str]


class VideoAnalysisRequest(BaseModel):
    """Video analysis request"""
    analysis_type: str = "content"
    language: str = "en"
    
    @field_validator("analysis_type")
    @classmethod
    def validate_analysis_type(cls, v):
        if v not in ["content", "transcript", "summary", "emotions"]:
            raise ValueError("Analysis type must be: content, transcript, summary, or emotions")
        return v


@router.post("/generate")
@rate_limit_video
async def generate_video(
    request: VideoGenerationRequest,
    http_request: Request,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> VideoGenerationResponse:
    """
    Generate video using Sora AI model
    
    - **prompt**: Video description prompt (required)
    - **duration**: Video duration in seconds (1-30)
    - **resolution**: Video resolution (720p, 1080p, 4k)
    - **style**: Video style (realistic, animated, artistic)
    - **agent_context**: Optional agent context for themed videos
    """
    try:
        logger.info(f"Video generation request from user {user['user_id']}")
        
        generation_id = str(uuid.uuid4())
        
        # Call Azure OpenAI Sora service
        result = await azure_openai_service.generate_video(
            prompt=request.prompt,
            duration=request.duration
        )
        
        if result["status"] == "success":
            return VideoGenerationResponse(
                generation_id=generation_id,
                status="completed",
                video_url=result["video_url"],
                thumbnail_url=result.get("thumbnail_url"),
                duration_seconds=request.duration,
                resolution=request.resolution,
                file_size_mb=result.get("file_size_mb", 0.0),
                model_used=result["model"],
                timestamp=datetime.utcnow().isoformat(),
                estimated_completion=None
            )
        elif result["status"] == "processing":
            return VideoGenerationResponse(
                generation_id=generation_id,
                status="processing",
                video_url=None,
                thumbnail_url=None,
                duration_seconds=request.duration,
                resolution=request.resolution,
                file_size_mb=None,
                model_used=result["model"],
                timestamp=datetime.utcnow().isoformat(),
                estimated_completion=result.get("estimated_completion")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Video generation failed: {result.get('error', 'Unknown error')}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate video"
        )


@router.get("/generation/{generation_id}")
async def get_generation_status(
    generation_id: str,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> VideoGenerationResponse:
    """Check status of video generation"""
    try:
        logger.info(f"Checking video generation status: {generation_id}")
        
        # In production, this would check the actual generation status
        # For now, return a mock response
        return VideoGenerationResponse(
            generation_id=generation_id,
            status="completed",
            video_url=f"/static/videos/{generation_id}.mp4",
            thumbnail_url=f"/static/videos/{generation_id}_thumb.jpg",
            duration_seconds=10,
            resolution="1080p",
            file_size_mb=15.2,
            model_used="sora-buddyagents",
            timestamp=datetime.utcnow().isoformat(),
            estimated_completion=None
        )
        
    except Exception as e:
        logger.error(f"Error checking generation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check generation status"
        )


@router.post("/analyze")
@rate_limit_video
async def analyze_video(
    video_file: UploadFile = File(...),
    analysis_request: VideoAnalysisRequest = Depends(),
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """
    Analyze uploaded video content
    
    - **video_file**: Video file to analyze
    - **analysis_type**: Type of analysis (content, transcript, summary, emotions)
    - **language**: Language for analysis output
    """
    try:
        logger.info(f"Video analysis request from user {user['user_id']}")
        
        # Validate file
        if not video_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file size (100MB limit)
        file_content = await video_file.read()
        if len(file_content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 100MB limit"
            )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # For now, return mock analysis results
            # In production, this would use video analysis APIs
            analysis_results = {
                "content": {
                    "objects": ["person", "building", "sky"],
                    "scenes": ["outdoor", "urban"],
                    "activities": ["walking", "talking"],
                    "confidence": 0.92
                },
                "transcript": {
                    "text": "Sample transcript of video content...",
                    "language": analysis_request.language,
                    "confidence": 0.89
                },
                "summary": {
                    "text": "This video shows a person walking in an urban environment...",
                    "key_points": ["Urban setting", "Person movement", "Clear audio"],
                    "duration_seconds": 30
                },
                "emotions": {
                    "dominant_emotion": "neutral",
                    "emotion_scores": {
                        "happy": 0.2,
                        "neutral": 0.7,
                        "sad": 0.1
                    }
                }
            }
            
            return {
                "analysis_type": analysis_request.analysis_type,
                "results": analysis_results[analysis_request.analysis_type],
                "file_info": {
                    "filename": video_file.filename,
                    "size_mb": len(file_content) / (1024 * 1024),
                    "format": video_file.content_type
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze video"
        )


@router.get("/generations")
async def list_user_generations(
    limit: int = 10,
    offset: int = 0,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Get list of user's video generations"""
    try:
        # In production, this would query the database
        # For now, return mock data
        generations = []
        for i in range(limit):
            generations.append({
                "generation_id": f"gen_{i + offset + 1}",
                "prompt": f"Sample video prompt {i + 1}",
                "status": "completed",
                "video_url": f"/static/videos/gen_{i + offset + 1}.mp4",
                "thumbnail_url": f"/static/videos/gen_{i + offset + 1}_thumb.jpg",
                "duration_seconds": 10,
                "resolution": "1080p",
                "created_at": datetime.utcnow().isoformat(),
                "file_size_mb": 15.2
            })
        
        return {
            "generations": generations,
            "total": 50,  # Mock total count
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < 50
        }
        
    except Exception as e:
        logger.error(f"Error listing generations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generations"
        )


@router.delete("/generation/{generation_id}")
async def delete_generation(
    generation_id: str,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Delete a video generation"""
    try:
        logger.info(f"Deleting video generation: {generation_id}")
        
        # In production, this would delete from storage and database
        return {
            "message": "Video generation deleted successfully",
            "generation_id": generation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error deleting generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete generation"
        )


@router.get("/capabilities")
async def get_video_capabilities():
    """Get information about video processing capabilities"""
    try:
        return {
            "video_generation": {
                "enabled": True,
                "model": "sora-buddyagents",
                "max_duration": 30,
                "supported_resolutions": ["720p", "1080p", "4k"],
                "supported_styles": ["realistic", "animated", "artistic", "cinematic"],
                "max_prompt_length": 500,
                "estimated_time": "30-120 seconds per video"
            },
            "video_analysis": {
                "enabled": True,
                "max_file_size": "100MB",
                "supported_formats": ["mp4", "avi", "mov", "mkv", "webm"],
                "analysis_types": [
                    "content",
                    "transcript", 
                    "summary",
                    "emotions"
                ],
                "supported_languages": ["en", "hi", "bn", "ta", "te"]
            },
            "rate_limits": {
                "video_generation": "5 requests/minute",
                "video_analysis": "10 requests/minute",
                "concurrent_generations": "3 per user"
            },
            "storage": {
                "retention_days": 30,
                "max_storage_per_user": "1GB",
                "download_expiry": "24 hours"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting video capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video capabilities"
        )


@router.get("/templates")
async def get_video_templates():
    """Get pre-defined video templates for common use cases"""
    try:
        templates = [
            {
                "id": "educational",
                "name": "Educational Content",
                "description": "Perfect for tutorials and explanations",
                "suggested_prompts": [
                    "A teacher explaining mathematical concepts on a whiteboard",
                    "Scientific experiment demonstration in a laboratory",
                    "Historical timeline visualization"
                ],
                "optimal_duration": 15,
                "style": "realistic"
            },
            {
                "id": "cultural",
                "name": "Indian Culture",
                "description": "Showcasing Indian traditions and heritage",
                "suggested_prompts": [
                    "Traditional Indian dance performance in colorful costumes",
                    "Bustling Indian marketplace with vendors and customers",
                    "Festival celebration with lights and decorations"
                ],
                "optimal_duration": 10,
                "style": "cinematic"
            },
            {
                "id": "nature",
                "name": "Nature & Landscapes",
                "description": "Beautiful natural scenes and environments",
                "suggested_prompts": [
                    "Sunrise over the Himalayas with misty valleys",
                    "Peaceful river flowing through green forests",
                    "Wildlife in their natural habitat"
                ],
                "optimal_duration": 8,
                "style": "realistic"
            },
            {
                "id": "abstract",
                "name": "Abstract & Artistic",
                "description": "Creative and imaginative visuals",
                "suggested_prompts": [
                    "Flowing geometric patterns in vibrant colors",
                    "Digital art transformation sequence",
                    "Surreal dreamscape with floating elements"
                ],
                "optimal_duration": 12,
                "style": "artistic"
            }
        ]
        
        return {
            "templates": templates,
            "usage_tips": [
                "Be specific in your prompts for better results",
                "Consider lighting and camera angles",
                "Shorter videos (5-15 seconds) generate faster",
                "Use templates as starting points for custom prompts"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting video templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve video templates"
        )