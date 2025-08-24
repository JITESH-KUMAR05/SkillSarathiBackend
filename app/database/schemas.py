from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Available agent types"""
    COMPANION = "companion"
    MENTOR = "mentor"
    INTERVIEW = "interview"


# Enhanced Chat Message Schema
class ChatMessage(BaseModel):
    content: str = Field(..., description="The message content")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    agent_type: Optional[str] = Field(None, description="Preferred agent type")
    document_id: Optional[str] = Field(None, description="Related document ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AgentSwitchRequest(BaseModel):
    conversation_id: Optional[str] = Field(None, description="Conversation to switch in")
    agent_type: str = Field(..., description="Target agent type")
    context: Optional[Dict[str, Any]] = Field(None, description="Switch context")


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, description="User's name")
    age: Optional[int] = Field(None, description="User's age")
    location: Optional[str] = Field(None, description="User's location")
    occupation: Optional[str] = Field(None, description="User's occupation")
    career_goal: Optional[str] = Field(None, description="Career aspirations")
    interests: Optional[List[str]] = Field(None, description="User interests")
    preferred_language: Optional[str] = Field("english", description="Preferred language")
    communication_style: Optional[str] = Field(None, description="Preferred communication style")
    learning_goals: Optional[List[str]] = Field(None, description="Learning objectives")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Arjun Sharma",
                "age": 25,
                "location": "Bangalore, India",
                "occupation": "Software Developer",
                "career_goal": "Senior Software Engineer at FAANG company",
                "interests": ["programming", "cricket", "bollywood movies"],
                "preferred_language": "english",
                "communication_style": "direct but respectful",
                "learning_goals": ["system design", "advanced algorithms", "leadership skills"]
            }
        }


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Agent Schemas
class AgentBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    agent_type: str = Field(..., max_length=50)
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    agent_type: Optional[str] = Field(None, max_length=50)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class Agent(AgentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Conversation Schemas
class ConversationBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    agent_id: int


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)


class Conversation(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Message Schemas
class MessageBase(BaseModel):
    content: str
    role: str = Field(..., pattern="^(user|assistant|system)$")
    message_metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    conversation_id: int


class Message(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Document Schemas
class DocumentBase(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    file_type: Optional[str] = Field(None, max_length=50)
    doc_metadata: Optional[Dict[str, Any]] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    doc_metadata: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    id: int
    user_id: int
    file_path: Optional[str] = None
    vector_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Enhanced Chat Schemas
class ChatMessage(BaseModel):
    content: str = Field(..., description="The message content")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    agent_type: Optional[str] = Field(None, description="Preferred agent type")
    document_id: Optional[str] = Field(None, description="Related document ID for context")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    message: str
    conversation_id: int
    agent_name: str
    metadata: Optional[Dict[str, Any]] = None
