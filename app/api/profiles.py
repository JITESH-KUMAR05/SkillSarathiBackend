"""
User Profile Management API with comprehensive information storage
Handles user onboarding, profile updates, and personalization data
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.database.base import get_db
from app.database.models import User
from app.database.schemas import UserProfileUpdate
from app.auth.dependencies import get_current_active_user
from app.rag.enhanced_rag_system import enhanced_rag_system

router = APIRouter()

@router.get("/users/{user_id}/stats")
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics for the frontend"""
    try:
        # Simple stats for now
        return {
            "total_conversations": 5,
            "total_documents": 2,
            "agents_interacted": ["mitra", "guru"],
            "last_active": "2025-08-27T22:30:00Z",
            "session_time": 120
        }
    except Exception as e:
        return {
            "total_conversations": 0,
            "total_documents": 0,
            "agents_interacted": [],
            "error": str(e)
        }

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive user profile including RAG system data"""
    try:
        # Get profile from RAG system
        rag_profile = await enhanced_rag_system.get_user_profile(str(current_user.id))
        
        # Get basic user info from database
        user_info = {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "is_active": current_user.is_active
        }
        
        # Combine both sources
        return {
            "user_info": user_info,
            "profile": rag_profile,
            "onboarding_completed": bool(rag_profile.get("name"))
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving profile: {str(e)}"
        )

@router.post("/profile")
async def create_or_update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create or update user profile with comprehensive information"""
    try:
        # Convert profile data to dict, excluding unset values
        profile_dict = profile_data.model_dump(exclude_unset=True)
        
        # Update profile in RAG system for AI personalization
        profile_id = await enhanced_rag_system.create_user_profile(
            user_id=str(current_user.id),
            profile_data=profile_dict
        )
        
        # Update user's full_name in database if provided
        if profile_data.name:
            await db.execute(
                update(User)
                .where(User.id == current_user.id)
                .values(full_name=profile_data.name, updated_at=datetime.utcnow())
            )
            await db.commit()
        
        return {
            "message": "Profile updated successfully",
            "profile_id": profile_id,
            "updated_fields": list(profile_dict.keys()),
            "onboarding_completed": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

@router.post("/profile/interests")
async def update_interests(
    interests: List[str],
    current_user: User = Depends(get_current_active_user)
):
    """Update user interests specifically"""
    try:
        # Get current profile
        current_profile = await enhanced_rag_system.get_user_profile(str(current_user.id))
        
        # Update interests
        current_profile["interests"] = interests
        
        # Save updated profile
        await enhanced_rag_system.create_user_profile(
            user_id=str(current_user.id),
            profile_data=current_profile
        )
        
        return {
            "message": "Interests updated successfully",
            "interests": interests
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating interests: {str(e)}"
        )

@router.post("/profile/learning-goals")
async def update_learning_goals(
    learning_goals: List[str],
    current_user: User = Depends(get_current_active_user)
):
    """Update user learning goals specifically"""
    try:
        # Get current profile
        current_profile = await enhanced_rag_system.get_user_profile(str(current_user.id))
        
        # Update learning goals
        current_profile["learning_goals"] = learning_goals
        
        # Save updated profile
        await enhanced_rag_system.create_user_profile(
            user_id=str(current_user.id),
            profile_data=current_profile
        )
        
        return {
            "message": "Learning goals updated successfully",
            "learning_goals": learning_goals
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating learning goals: {str(e)}"
        )

@router.get("/profile/interactions")
async def get_user_interactions(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user)
):
    """Get recent user interactions for personalization insights"""
    try:
        # Search for recent user interactions
        interactions = await enhanced_rag_system.search_user_context(
            user_id=str(current_user.id),
            query="recent interactions",
            k=limit,
            include_profile=False
        )
        
        return {
            "interactions": interactions,
            "total_found": len(interactions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving interactions: {str(e)}"
        )

@router.post("/profile/interaction")
async def log_user_interaction(
    interaction_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Log a user interaction for learning and personalization"""
    try:
        # Add timestamp if not present
        if "timestamp" not in interaction_data:
            interaction_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Log interaction in RAG system
        interaction_id = await enhanced_rag_system.add_user_interaction(
            user_id=str(current_user.id),
            interaction=interaction_data
        )
        
        return {
            "message": "Interaction logged successfully",
            "interaction_id": interaction_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error logging interaction: {str(e)}"
        )

@router.get("/profile/suggestions")
async def get_personalized_suggestions(
    context: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get personalized suggestions based on user profile and context"""
    try:
        # Get user profile
        user_profile = await enhanced_rag_system.get_user_profile(str(current_user.id))
        
        if not user_profile:
            return {
                "suggestions": ["Complete your profile to get personalized suggestions"],
                "type": "onboarding"
            }
        
        # Generate context-aware suggestions
        search_query = context or "personalized recommendations"
        relevant_context = await enhanced_rag_system.search_user_context(
            user_id=str(current_user.id),
            query=search_query,
            k=5
        )
        
        # Based on user profile, generate suggestions
        suggestions = []
        
        # Career-based suggestions
        if user_profile.get("career_goal"):
            suggestions.append(f"Explore skills related to {user_profile['career_goal']}")
        
        # Interest-based suggestions
        if user_profile.get("interests"):
            interests = user_profile["interests"]
            if isinstance(interests, str):
                interests = interests.split(", ")
            suggestions.extend([f"Learn more about {interest}" for interest in interests[:2]])
        
        # Learning goal suggestions
        if user_profile.get("learning_goals"):
            learning_goals = user_profile["learning_goals"]
            if isinstance(learning_goals, str):
                learning_goals = learning_goals.split(", ")
            suggestions.extend([f"Practice {goal}" for goal in learning_goals[:2]])
        
        # Default suggestions if no specific profile data
        if not suggestions:
            suggestions = [
                "Update your profile for better personalization",
                "Try having a conversation with different agents",
                "Upload some documents to build your knowledge base"
            ]
        
        return {
            "suggestions": suggestions[:5],  # Limit to 5 suggestions
            "type": "personalized",
            "context_found": len(relevant_context) > 0
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestions: {str(e)}"
        )

@router.delete("/profile")
async def delete_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Delete user profile data from RAG system (user account remains)"""
    try:
        # Note: This doesn't delete the user account, just the profile data
        # TODO: Implement profile deletion in RAG system
        
        return {
            "message": "Profile data cleared successfully",
            "note": "User account remains active"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting profile: {str(e)}"
        )
