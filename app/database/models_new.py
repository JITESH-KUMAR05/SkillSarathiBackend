"""
Enhanced Database Models for Skillsarathi AI
Supports users, conversations, documents, interviews, and system analytics
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from app.database.base import Base

class User(Base):
    """Enhanced user model with comprehensive profile data"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile information
    full_name = Column(String(100))
    age = Column(Integer)
    location = Column(String(100), default="India")
    profession = Column(String(100))
    interests = Column(JSON)  # List of interests
    learning_goals = Column(JSON)  # List of learning goals
    
    # Preferences
    preferred_language = Column(String(10), default="en")
    notification_preferences = Column(JSON)
    privacy_settings = Column(JSON)
    
    # System fields
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    documents = relationship("Document", back_populates="user")
    interview_sessions = relationship("InterviewSession", back_populates="user")
    user_analytics = relationship("UserAnalytics", back_populates="user")

class Conversation(Base):
    """Store conversation history with context and metadata"""
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Conversation metadata
    agent_type = Column(String(20), nullable=False)  # companion, mentor, interview
    session_id = Column(String)  # For grouping related messages
    title = Column(String(200))  # Auto-generated or user-defined title
    
    # Message content
    message_type = Column(String(20), default="chat")  # chat, system, error
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # AI response metadata
    response_metadata = Column(JSON)  # Model info, confidence, etc.
    audio_url = Column(String(500))  # TTS audio URL if generated
    
    # Context and state
    user_context = Column(JSON)  # User state at time of message
    conversation_context = Column(JSON)  # Conversation-specific context
    
    # Analytics
    response_time_ms = Column(Float)
    tokens_used = Column(Integer)
    model_used = Column(String(50))
    
    # System fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")

class Document(Base):
    """Store uploaded documents and their processing status"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Document metadata
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(500))  # Storage path
    
    # Processing status
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text)
    
    # Content and embeddings
    extracted_text = Column(Text)
    summary = Column(Text)
    key_topics = Column(JSON)  # Extracted topics/keywords
    
    # Vector storage references
    vector_store_id = Column(String)  # ChromaDB collection ID
    embedding_model = Column(String(100))
    chunk_count = Column(Integer, default=0)
    
    # System fields
    uploaded_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    last_accessed = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    rag_queries = relationship("RAGQuery", back_populates="document")

class RAGQuery(Base):
    """Track RAG queries and their performance"""
    __tablename__ = "rag_queries"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    document_id = Column(String, ForeignKey("documents.id"))
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_embedding = Column(LargeBinary)  # Serialized embedding vector
    
    # Results
    results_found = Column(Integer, default=0)
    top_similarity_score = Column(Float)
    retrieved_chunks = Column(JSON)  # List of chunk IDs and scores
    
    # Performance metrics
    query_time_ms = Column(Float)
    embedding_time_ms = Column(Float)
    retrieval_time_ms = Column(Float)
    
    # System fields
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    document = relationship("Document", back_populates="rag_queries")

class InterviewSession(Base):
    """Store interview session data and analytics"""
    __tablename__ = "interview_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    interview_type = Column(String(50), nullable=False)  # technical, behavioral, hr, etc.
    session_status = Column(String(20), default="active")  # active, completed, abandoned
    
    # Content and progress
    questions_asked = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    current_phase = Column(String(20), default="introduction")
    
    # Performance tracking
    total_duration_seconds = Column(Integer)
    average_response_time = Column(Float)
    
    # AI Assessment (generated at end of session)
    overall_score = Column(Float)  # 0-100 score
    communication_score = Column(Float)
    technical_score = Column(Float)
    confidence_score = Column(Float)
    
    strengths = Column(JSON)  # List of identified strengths
    areas_for_improvement = Column(JSON)  # List of improvement areas
    detailed_feedback = Column(Text)
    recommendations = Column(JSON)  # Personalized recommendations
    
    # System fields
    started_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    interview_responses = relationship("InterviewResponse", back_populates="session")

class InterviewResponse(Base):
    """Individual responses within an interview session"""
    __tablename__ = "interview_responses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    
    # Question and response
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=False)
    
    # Response analysis
    response_time_seconds = Column(Float)
    word_count = Column(Integer)
    confidence_indicators = Column(JSON)  # Detected confidence markers
    
    # AI Assessment
    relevance_score = Column(Float)  # How relevant was the answer
    clarity_score = Column(Float)  # How clear was the communication
    depth_score = Column(Float)  # How detailed/thorough
    
    feedback = Column(Text)  # Specific feedback for this response
    improvement_suggestions = Column(JSON)
    
    # System fields
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    session = relationship("InterviewSession", back_populates="interview_responses")

class UserAnalytics(Base):
    """Track user behavior and system performance analytics"""
    __tablename__ = "user_analytics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Date for aggregation
    date = Column(DateTime, nullable=False)
    
    # Usage metrics
    total_messages = Column(Integer, default=0)
    companion_messages = Column(Integer, default=0)
    mentor_messages = Column(Integer, default=0)
    interview_messages = Column(Integer, default=0)
    
    # Session metrics
    total_session_time_minutes = Column(Float, default=0)
    total_sessions = Column(Integer, default=0)
    
    # Document interactions
    documents_uploaded = Column(Integer, default=0)
    rag_queries = Column(Integer, default=0)
    
    # Interview activities
    interviews_started = Column(Integer, default=0)
    interviews_completed = Column(Integer, default=0)
    
    # Performance metrics
    average_response_time_ms = Column(Float)
    total_tokens_used = Column(Integer, default=0)
    
    # System fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_analytics")

class SystemMetrics(Base):
    """Store system-wide performance and usage metrics"""
    __tablename__ = "system_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Timestamp for aggregation
    timestamp = Column(DateTime, default=func.now())
    metric_type = Column(String(20), nullable=False)  # hourly, daily, realtime
    
    # System performance
    active_connections = Column(Integer, default=0)
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    disk_usage_percent = Column(Float)
    
    # Request metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    average_response_time_ms = Column(Float)
    
    # AI model usage
    llm_requests = Column(Integer, default=0)
    llm_tokens_consumed = Column(Integer, default=0)
    tts_requests = Column(Integer, default=0)
    embedding_requests = Column(Integer, default=0)
    
    # Agent-specific metrics
    companion_sessions = Column(Integer, default=0)
    mentor_sessions = Column(Integer, default=0)
    interview_sessions = Column(Integer, default=0)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    error_rate_percent = Column(Float)
    critical_errors = Column(JSON)  # List of critical error details

class APIKey(Base):
    """Store and manage API keys securely"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Key metadata
    service_name = Column(String(50), nullable=False)  # github, murf, openai, azure
    key_name = Column(String(100), nullable=False)
    encrypted_key = Column(Text, nullable=False)  # Encrypted API key
    
    # Status and validation
    is_active = Column(Boolean, default=True)
    is_valid = Column(Boolean, default=True)
    last_validated = Column(DateTime)
    validation_error = Column(Text)
    
    # Usage tracking
    requests_made = Column(Integer, default=0)
    last_used = Column(DateTime)
    monthly_usage_limit = Column(Integer)
    monthly_usage_count = Column(Integer, default=0)
    
    # System fields
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Create indexes for better performance
from sqlalchemy import Index

# User indexes
Index('idx_users_username', User.username)
Index('idx_users_email', User.email)
Index('idx_users_created_at', User.created_at)

# Conversation indexes
Index('idx_conversations_user_id', Conversation.user_id)
Index('idx_conversations_agent_type', Conversation.agent_type)
Index('idx_conversations_session_id', Conversation.session_id)
Index('idx_conversations_created_at', Conversation.created_at)

# Document indexes
Index('idx_documents_user_id', Document.user_id)
Index('idx_documents_status', Document.processing_status)
Index('idx_documents_uploaded_at', Document.uploaded_at)

# Analytics indexes
Index('idx_user_analytics_user_date', UserAnalytics.user_id, UserAnalytics.date)
Index('idx_system_metrics_timestamp', SystemMetrics.timestamp)
Index('idx_system_metrics_type', SystemMetrics.metric_type)
