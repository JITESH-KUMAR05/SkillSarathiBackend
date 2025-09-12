"""
Video Interview Service using Azure Sora
Advanced video generation for interview scenarios
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.llm.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)

class VideoInterviewService:
    """Service for generating interview scenario videos using Sora"""
    
    def __init__(self):
        self.azure_service = azure_openai_service
        
        # Pre-defined interview scenarios for quick generation
        self.interview_scenarios = {
            "technical": {
                "coding": "A professional coding interview setup with a clean office background, interviewer and candidate discussing algorithms on a whiteboard, realistic corporate environment",
                "system_design": "A system design interview with diagrams being drawn, professional meeting room with modern tech setup, natural conversation flow",
                "debugging": "A pair programming session showing code debugging, collaborative atmosphere with two people working on a problem together"
            },
            "behavioral": {
                "leadership": "A behavioral interview scene discussing leadership experiences, professional office setting with comfortable seating arrangement",
                "teamwork": "An interview focusing on teamwork scenarios, friendly corporate environment with natural gestures and expressions",
                "problem_solving": "A scenario-based interview discussing problem-solving approaches, engaging conversation in a modern office space"
            },
            "hr": {
                "introduction": "A friendly HR introduction interview, welcoming office environment with professional but warm atmosphere",
                "culture_fit": "A culture fit discussion interview, casual but professional setting showing company values alignment",
                "salary_negotiation": "A professional salary negotiation conversation, confident and respectful business meeting atmosphere"
            }
        }
    
    async def generate_interview_video(
        self, 
        scenario_type: str = "technical",
        scenario_subtype: str = "coding",
        custom_prompt: Optional[str] = None,
        duration: int = 10
    ) -> Dict[str, Any]:
        """
        Generate an interview scenario video
        
        Args:
            scenario_type: Type of interview (technical, behavioral, hr)
            scenario_subtype: Specific scenario within type
            custom_prompt: Custom video prompt (overrides preset)
            duration: Video duration in seconds (max 20)
            
        Returns:
            Dict with video generation job details
        """
        try:
            # Get video prompt
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self.interview_scenarios.get(scenario_type, {}).get(
                    scenario_subtype, 
                    self.interview_scenarios["technical"]["coding"]
                )
            
            # Add Indian context for cultural relevance
            prompt += " Include diverse Indian professional setting with appropriate cultural elements and modern office environment."
            
            logger.info(f"🎬 Generating {scenario_type} interview video: {scenario_subtype}")
            
            # Generate video using Sora
            result = await self.azure_service.generate_video(
                prompt=prompt,
                height=1080,
                width=1920,  # 16:9 aspect ratio for professional interviews
                duration=min(duration, 20),  # Cap at 20 seconds
                variants=1
            )
            
            return {
                "scenario_type": scenario_type,
                "scenario_subtype": scenario_subtype,
                "video_job": result,
                "prompt_used": prompt,
                "status": "generating"
            }
            
        except Exception as e:
            logger.error(f"❌ Interview video generation error: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def get_available_scenarios(self) -> Dict[str, Any]:
        """Get all available interview scenarios"""
        return {
            "scenarios": self.interview_scenarios,
            "custom_prompt_supported": True,
            "max_duration": 20,
            "recommended_duration": 10,
            "aspect_ratios": ["16:9", "9:16", "1:1"]
        }
    
    async def generate_practice_questions_video(
        self, 
        job_role: str,
        difficulty_level: str = "intermediate",
        question_count: int = 3
    ) -> Dict[str, Any]:
        """
        Generate a video with practice interview questions
        
        Args:
            job_role: Target job role (e.g., "Software Engineer", "Product Manager")
            difficulty_level: easy, intermediate, advanced
            question_count: Number of questions to include
            
        Returns:
            Video generation result with practice questions
        """
        try:
            # Create prompt for practice questions video
            prompt = f"""A professional interview coach presenting {question_count} {difficulty_level} level 
                        interview questions for {job_role} position. Clean office background, 
                        engaging presentation style with clear articulation. Include visual aids 
                        or slides showing the questions. Professional Indian setting with 
                        modern corporate environment."""
            
            logger.info(f"🎯 Generating practice questions video for {job_role}")
            
            result = await self.azure_service.generate_video(
                prompt=prompt,
                height=1080,
                width=1920,
                duration=15,  # Longer for multiple questions
                variants=1
            )
            
            return {
                "job_role": job_role,
                "difficulty_level": difficulty_level,
                "question_count": question_count,
                "video_job": result,
                "status": "generating"
            }
            
        except Exception as e:
            logger.error(f"❌ Practice questions video error: {e}")
            return {"error": str(e), "status": "failed"}

# Global service instance
video_interview_service = VideoInterviewService()
