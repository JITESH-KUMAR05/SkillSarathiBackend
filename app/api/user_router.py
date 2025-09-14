"""
User Router for BuddyAgents Platform
Handles user authentication, profile management, and settings
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr, field_validator

from app.core.config import get_settings
from app.core.security import AuthenticationService, InputValidator

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()
security = HTTPBearer()

# Request/Response Models
class UserRegistration(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str
    full_name: str
    preferred_language: str = "en"
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v
    
    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        return InputValidator.sanitize_text(v, max_length=100)
    
    @field_validator("preferred_language")
    @classmethod
    def validate_language(cls, v):
        supported_languages = ["en", "hi", "bn", "ta", "te", "gu", "mr", "kn", "ml", "pa"]
        if v not in supported_languages:
            raise ValueError(f"Language must be one of: {', '.join(supported_languages)}")
        return v


class UserLogin(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    """User profile response"""
    user_id: str
    email: str
    full_name: str
    preferred_language: str
    avatar_url: Optional[str]
    created_at: str
    last_login: Optional[str]
    subscription_tier: str
    usage_stats: Dict[str, Any]


class ProfileUpdate(BaseModel):
    """Profile update request"""
    full_name: Optional[str] = None
    preferred_language: Optional[str] = None
    avatar_url: Optional[str] = None
    
    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v):
        if v is not None:
            return InputValidator.sanitize_text(v, max_length=100)
        return v


class PasswordChange(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserSettings(BaseModel):
    """User settings"""
    notifications_enabled: bool = True
    email_updates: bool = True
    preferred_agent: str = "mitra"
    theme: str = "light"
    voice_enabled: bool = True
    auto_save_conversations: bool = True


@router.post("/register")
async def register_user(registration: UserRegistration, request: Request):
    """
    Register a new user account
    
    - **email**: Valid email address
    - **password**: Password (minimum 8 characters)
    - **full_name**: User's full name
    - **preferred_language**: Language preference (en, hi, bn, etc.)
    """
    try:
        logger.info(f"User registration attempt for email: {registration.email}")
        
        # Check if user already exists
        existing_user = await AuthenticationService.get_user_by_email(registration.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Create new user
        user_data = await AuthenticationService.create_user(
            email=registration.email,
            password=registration.password,
            full_name=registration.full_name,
            preferred_language=registration.preferred_language
        )
        
        if user_data["status"] == "success":
            # Generate access token
            access_token = AuthenticationService.create_access_token(
                data={"sub": user_data["user"]["user_id"]}
            )
            
            return {
                "message": "User registered successfully",
                "user": {
                    "user_id": user_data["user"]["user_id"],
                    "email": user_data["user"]["email"],
                    "full_name": user_data["user"]["full_name"],
                    "preferred_language": user_data["user"]["preferred_language"]
                },
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=user_data.get("error", "Failed to create user")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login")
async def login_user(login_data: UserLogin, request: Request):
    """
    Login with email and password
    
    - **email**: Registered email address
    - **password**: User password
    """
    try:
        logger.info(f"Login attempt for email: {login_data.email}")
        
        # Authenticate user
        auth_result = await AuthenticationService.authenticate_user(
            email=login_data.email,
            password=login_data.password
        )
        
        if auth_result["status"] == "success":
            user = auth_result["user"]
            
            # Generate access token
            access_token = AuthenticationService.create_access_token(
                data={"sub": user["user_id"]}
            )
            
            # Update last login
            await AuthenticationService.update_last_login(user["user_id"])
            
            return {
                "message": "Login successful",
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "preferred_language": user["preferred_language"]
                },
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/{user_id}/profile")
async def get_user_profile(
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> UserProfile:
    """Get current user's profile information"""
    try:
        # Get detailed user information
        user_details = await AuthenticationService.get_user_details(user["user_id"])
        
        if user_details["status"] == "success":
            user_data = user_details["user"]
            
            return UserProfile(
                user_id=user_data["user_id"],
                email=user_data["email"],
                full_name=user_data["full_name"],
                preferred_language=user_data["preferred_language"],
                avatar_url=user_data.get("avatar_url"),
                created_at=user_data["created_at"],
                last_login=user_data.get("last_login"),
                subscription_tier=user_data.get("subscription_tier", "free"),
                usage_stats=user_data.get("usage_stats", {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "voice_minutes": 0,
                    "videos_generated": 0
                })
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.put("/{user_id}/profile")
async def update_user_profile(
    profile_update: ProfileUpdate,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Update user profile information"""
    try:
        logger.info(f"Profile update for user {user['user_id']}")
        
        # Update profile
        update_result = await AuthenticationService.update_user_profile(
            user_id=user["user_id"],
            updates=profile_update.dict(exclude_none=True)
        )
        
        if update_result["status"] == "success":
            return {
                "message": "Profile updated successfully",
                "updated_fields": list(profile_update.dict(exclude_none=True).keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=update_result.get("error", "Failed to update profile")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Change user password"""
    try:
        logger.info(f"Password change request for user {user['user_id']}")
        
        # Change password
        change_result = await AuthenticationService.change_password(
            user_id=user["user_id"],
            current_password=password_change.current_password,
            new_password=password_change.new_password
        )
        
        if change_result["status"] == "success":
            return {
                "message": "Password changed successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=change_result.get("error", "Failed to change password")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.get("/settings")
async def get_user_settings(
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
) -> UserSettings:
    """Get user settings and preferences"""
    try:
        # Get user settings
        settings_result = await AuthenticationService.get_user_settings(user["user_id"])
        
        if settings_result["status"] == "success":
            settings_data = settings_result["settings"]
            
            return UserSettings(
                notifications_enabled=settings_data.get("notifications_enabled", True),
                email_updates=settings_data.get("email_updates", True),
                preferred_agent=settings_data.get("preferred_agent", "mitra"),
                theme=settings_data.get("theme", "light"),
                voice_enabled=settings_data.get("voice_enabled", True),
                auto_save_conversations=settings_data.get("auto_save_conversations", True)
            )
        else:
            # Return default settings if none found
            return UserSettings()
        
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        # Return default settings on error
        return UserSettings()


@router.put("/settings")
async def update_user_settings(
    settings: UserSettings,
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Update user settings and preferences"""
    try:
        logger.info(f"Settings update for user {user['user_id']}")
        
        # Update settings
        update_result = await AuthenticationService.update_user_settings(
            user_id=user["user_id"],
            settings=settings.dict()
        )
        
        if update_result["status"] == "success":
            return {
                "message": "Settings updated successfully",
                "settings": settings.dict(),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=update_result.get("error", "Failed to update settings")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )


@router.get("/usage-stats")
async def get_usage_statistics(
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Get detailed usage statistics for the user"""
    try:
        # Get usage statistics
        stats_result = await AuthenticationService.get_usage_statistics(user["user_id"])
        
        if stats_result["status"] == "success":
            return {
                "user_id": user["user_id"],
                "statistics": stats_result["stats"],
                "current_period": {
                    "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "limits": {
                    "monthly_messages": 1000,
                    "monthly_voice_minutes": 60,
                    "monthly_videos": 10
                }
            }
        else:
            # Return default stats if none found
            return {
                "user_id": user["user_id"],
                "statistics": {
                    "total_conversations": 0,
                    "total_messages": 0,
                    "voice_minutes": 0,
                    "videos_generated": 0,
                    "monthly_usage": {
                        "messages": 0,
                        "voice_minutes": 0,
                        "videos": 0
                    }
                },
                "current_period": {
                    "start_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                },
                "limits": {
                    "monthly_messages": 1000,
                    "monthly_voice_minutes": 60,
                    "monthly_videos": 10
                }
            }
        
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage statistics"
        )


@router.delete("/account")
async def delete_user_account(
    user: Dict[str, Any] = Depends(AuthenticationService.get_current_user)
):
    """Delete user account (soft delete)"""
    try:
        logger.info(f"Account deletion request for user {user['user_id']}")
        
        # Soft delete account
        delete_result = await AuthenticationService.delete_user_account(user["user_id"])
        
        if delete_result["status"] == "success":
            return {
                "message": "Account deletion initiated successfully",
                "deletion_scheduled": "30 days from now",
                "recovery_period": "You can recover your account within 30 days",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=delete_result.get("error", "Failed to delete account")
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )