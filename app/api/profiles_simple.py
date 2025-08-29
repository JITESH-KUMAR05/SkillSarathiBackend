"""
Simple Profiles API for BuddyAgents
===================================
Basic user profile management without RAG dependencies
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Profile(BaseModel):
    id: str
    name: str
    email: str
    preferences: Dict[str, Any] = {}
    created_at: str
    updated_at: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class ProfileResponse(BaseModel):
    profile: Profile

router = APIRouter()

# In-memory storage for demo (replace with database later)
_profiles = {}

@router.get("/", response_model=List[Profile])
async def list_profiles():
    """List all profiles"""
    
    try:
        return list(_profiles.values())
    except Exception as e:
        logger.error(f"Error listing profiles: {e}")
        raise HTTPException(status_code=500, detail="Failed to list profiles")

@router.post("/", response_model=ProfileResponse)
async def create_profile(name: str, email: str, preferences: Optional[Dict[str, Any]] = None):
    """Create a new profile"""
    
    try:
        profile_id = f"profile_{len(_profiles) + 1}"
        
        profile = Profile(
            id=profile_id,
            name=name,
            email=email,
            preferences=preferences or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        _profiles[profile_id] = profile
        
        return ProfileResponse(profile=profile)
        
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to create profile")

@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str):
    """Get a specific profile"""
    
    try:
        if profile_id not in _profiles:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return ProfileResponse(profile=_profiles[profile_id])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")

@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: str, update: ProfileUpdate):
    """Update a profile"""
    
    try:
        if profile_id not in _profiles:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = _profiles[profile_id]
        
        if update.name is not None:
            profile.name = update.name
        
        if update.preferences is not None:
            profile.preferences.update(update.preferences)
        
        profile.updated_at = datetime.now().isoformat()
        
        return ProfileResponse(profile=profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@router.delete("/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete a profile"""
    
    try:
        if profile_id not in _profiles:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        del _profiles[profile_id]
        
        return {"message": "Profile deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile")

@router.get("/health")
async def profiles_health():
    """Health check for profiles system"""
    
    return {
        "status": "healthy",
        "total_profiles": len(_profiles),
        "timestamp": datetime.now().isoformat()
    }
