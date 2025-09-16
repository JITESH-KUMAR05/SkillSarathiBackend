"""
Configuration Management for BuddyAgents Platform
Handles all environment variables and application settings with validation
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation and type checking"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False
    )
    
    # Application Configuration
    app_name: str = "BuddyAgents Platform"
    app_version: str = "2.0.0"
    environment: str = "development"  # development, staging, production
    debug: bool = False
    log_level: str = "INFO"
    max_file_size: int = 10485760  # 10MB
    rate_limit_per_minute: int = 60
    
    @property
    def DEBUG(self) -> bool:
        """Alias for debug property for compatibility"""
        return self.debug
    
    # Security Configuration
    jwt_secret_key: str = "your-super-secure-jwt-secret-key-change-this"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./buddyagents.db"
    redis_url: str = "redis://localhost:6379"
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL"""
        return self.database_url
    
    # Azure OpenAI - Primary Resource (East US 2)
    azure_openai_api_key_primary: str = ""
    azure_openai_endpoint_primary: str = ""
    
    # Azure OpenAI - Secondary Resource (Sweden Central)
    azure_openai_api_key_secondary: str = ""
    azure_openai_endpoint_secondary: str = ""
    
    # Model Deployments
    model_router_deployment: str = "buddyagents-model-router"
    sora_deployment: str = "sora-buddyagents"
    gpt_realtime_deployment: str = "gpt-realtime-buddyagents"
    gpt_transcribe_deployment: str = "gpt-4o-transcribe-buddyagents"
    
    # API Versions
    azure_openai_api_version_chat: str = "2025-01-01-preview"
    azure_openai_api_version_realtime: str = "2024-10-01-preview"
    azure_openai_api_version_transcribe: str = "2025-03-01-preview"
    azure_openai_api_version_video: str = "preview"
    
    # Optional Services
    murf_api_key: Optional[str] = None
    github_token: Optional[str] = None
    
    @property
    def MURF_API_KEY(self) -> str:
        """Legacy support for MURF_API_KEY with fallback to murf_api_key"""
        return self.murf_api_key or ""
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "https://buddyagents.vercel.app",
        "https://buddyagents.com"
    ]
    
    # Legacy support for existing code
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4"
    AZURE_OPENAI_API_VERSION: str = "2023-05-15"
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings()


# Agent Configuration
class AgentConfig:
    """Configuration for each AI agent"""
    
    AGENTS = {
        "mitra": {
            "name": "Mitra",
            "display_name": "मित्र (Friend)",
            "description": "Your caring AI friend for emotional support",
            "color_primary": "#f97316",  # Orange
            "color_secondary": "#fed7aa",
            "system_prompt": """You are Mitra (मित्र), a warm and caring AI friend for Indian users. 
                               Provide emotional support, listen to problems, and offer friendly advice. 
                               Mix Hindi and English naturally (Hinglish). Be empathetic, understanding, and culturally aware.
                               Keep responses conversational and supportive, typically 2-3 sentences unless more detail is needed.
                               The model router will automatically select the best model for the conversation complexity.""",
            "voice_id": "alloy",
            "max_tokens": 500,
            "temperature": 0.8
        },
        "guru": {
            "name": "Guru",
            "display_name": "गुरु (Mentor)",
            "description": "Your AI learning mentor for education and growth",
            "color_primary": "#1e40af",  # Blue
            "color_secondary": "#dbeafe",
            "system_prompt": """You are Guru (गुरु), an AI learning mentor specializing in education and skill development. 
                              Help with studies, career guidance, interview preparation, and learning new skills. 
                              Be patient, encouraging, and provide structured, actionable learning advice.
                              Use examples relevant to Indian context. Keep responses informative and comprehensive.
                              The model router will select GPT-5 for complex teaching scenarios, GPT-4.1 for coding tutorials.""",
            "voice_id": "echo",
            "max_tokens": 800,
            "temperature": 0.7
        },
        "parikshak": {
            "name": "Parikshak",
            "display_name": "परीक्षक (Assessor)",
            "description": "Your AI interview coach and career assessor",
            "color_primary": "#1f2937",  # Dark Gray
            "color_secondary": "#f3f4f6",
            "system_prompt": """You are Parikshak (परीक्षक), an AI interview coach and technical assessor. 
                              Help with interview preparation, conduct mock interviews, and provide technical assessments. 
                              Be professional, provide constructive feedback, and help improve interview skills.
                              Focus on Indian job market context and common interview practices.
                              The model router will use GPT-4.1 for technical assessments, GPT-5 for behavioral coaching.""",
            "voice_id": "onyx",
            "max_tokens": 600,
            "temperature": 0.6
        }
    }
    
    @classmethod
    def get_agent_config(cls, agent_type: str) -> dict:
        """Get configuration for a specific agent"""
        return cls.AGENTS.get(agent_type, cls.AGENTS["mitra"])
    
    @classmethod
    def get_all_agents(cls) -> List[str]:
        """Get list of all available agents"""
        return list(cls.AGENTS.keys())
    
    @classmethod
    def is_valid_agent(cls, agent_type: str) -> bool:
        """Check if agent type is valid"""
        return agent_type in cls.AGENTS


# Create settings instance
settings = Settings()
