from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base


class User(Base):
    """User model for authentication and profile management"""
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    documents = relationship("Document", back_populates="user")


class Agent(Base):
    """Agent model for different AI agents"""
    __tablename__ = "agents"
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=False)  # research, creative, coding, etc.
    config = Column(JSON, nullable=True)  # Agent-specific configuration
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="agent")


class Conversation(Base):
    """Conversation model to track user-agent interactions"""
    __tablename__ = "conversations"
    
    title = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Message model for conversation history"""
    __tablename__ = "messages"
    
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Additional message metadata
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")


class Document(Base):
    """Document model for RAG system"""
    __tablename__ = "documents"
    
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vector_id = Column(String(100), nullable=True)  # Reference to vector database
    doc_metadata = Column(JSON, nullable=True)  # Document metadata
    
    # Relationships
    user = relationship("User", back_populates="documents")
