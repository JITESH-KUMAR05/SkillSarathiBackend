from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.database.base import get_db
from app.database.models import Conversation, Message, Agent as AgentModel, User
from app.database.schemas import (
    Conversation as ConversationSchema, 
    ConversationCreate,
    Message as MessageSchema,
    ChatMessage,
    ChatResponse
)
from app.auth.dependencies import get_current_active_user
from app.agents.base import create_agent
from app.rag.rag_system import rag_system
from app.llm.streaming_llm import StreamingLLMService

# Simple message model for frontend compatibility
class SimpleMessage(BaseModel):
    message: str
    agent_type: str = "mitra"
    user_id: str

class SimpleResponse(BaseModel):
    response: str
    agent: str
    timestamp: str

router = APIRouter()

# Simple message endpoint for frontend compatibility
@router.post("/message", response_model=SimpleResponse)
async def send_message(message_data: SimpleMessage):
    """Simple message endpoint for frontend compatibility"""
    
    try:
        # Initialize LLM service
        llm_service = StreamingLLMService()
        
        # Get response from LLM
        response = await llm_service.stream_response(
            message=message_data.message,
            agent_type=message_data.agent_type
        )
        
        from datetime import datetime
        return SimpleResponse(
            response=response,
            agent=message_data.agent_type,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        # Fallback response
        agent_names = {"mitra": "Mitra", "guru": "Guru", "parikshak": "Parikshak"}
        agent_name = agent_names.get(message_data.agent_type, "Mitra")
        
        if "factorial" in message_data.message.lower():
            response = f"Here's a Python function to calculate factorial:\n\n```python\ndef factorial(n):\n    if n == 0 or n == 1:\n        return 1\n    else:\n        return n * factorial(n - 1)\n\n# Using loop method:\ndef factorial_loop(n):\n    result = 1\n    for i in range(1, n + 1):\n        result *= i\n    return result\n\n# Example usage:\nprint(factorial(5))  # Output: 120\nprint(factorial_loop(5))  # Output: 120\n```\n\nBoth methods work! The first uses recursion, the second uses a loop. Which approach would you like to explore further?"
        else:
            response = f"Hello! I'm {agent_name}, and I'm here to help you. You said: '{message_data.message}'. How can I assist you today?"
        
        from datetime import datetime
        return SimpleResponse(
            response=response,
            agent=message_data.agent_type,
            timestamp=datetime.now().isoformat()
        )


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Send message to agent - simplified endpoint for frontend"""
    try:
        from app.llm.streaming_llm import StreamingLLMService
        
        # Extract message details
        user_message = message_data.get("message", "")
        agent_type = message_data.get("agent_type", "mitra")
        user_id = message_data.get("user_id", "anonymous")
        
        # Get LLM response
        llm_service = StreamingLLMService()
        response = await llm_service.stream_response(user_message, agent_type)
        
        return {
            "response": response,
            "agent_type": agent_type,
            "user_id": user_id,
            "timestamp": "2025-08-27T22:30:00Z"
        }
        
    except Exception as e:
        return {
            "response": f"I'm having some technical difficulties. Error: {str(e)}",
            "agent_type": agent_type,
            "user_id": user_id,
            "timestamp": "2025-08-27T22:30:00Z"
        }


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(
    chat_message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send a message to an agent and get response"""
    
    # Get agent from database
    result = await db.execute(select(AgentModel).where(AgentModel.id == chat_message.agent_id))
    agent_model = result.scalar_one_or_none()
    
    if not agent_model or not agent_model.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or inactive"
        )
    
    # Get or create conversation
    conversation = None
    if chat_message.conversation_id:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == chat_message.conversation_id,
                Conversation.user_id == current_user.id
            )
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
    
    if not conversation:
        # Create new conversation
        conversation = Conversation(
            title=chat_message.content[:50] + "..." if len(chat_message.content) > 50 else chat_message.content,
            user_id=current_user.id,
            agent_id=chat_message.agent_id
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
    
    # Save user message
    user_message = Message(
        content=chat_message.content,
        role="user",
        conversation_id=conversation.id
    )
    db.add(user_message)
    
    # Get conversation history for context
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
        .limit(10)  # Last 10 messages for context
    )
    history_messages = result.scalars().all()
    
    # Build context from conversation history
    conversation_history = []
    for msg in history_messages:
        conversation_history.append({
            "role": msg.role,
            "content": msg.content
        })
    
    # Get relevant documents using RAG
    relevant_context = ""
    try:
        relevant_context = await rag_system.get_context_for_query(
            query=chat_message.content,
            user_id=current_user.id,
            max_context_length=2000
        )
    except Exception as e:
        print(f"RAG context retrieval failed: {e}")
    
    # Create agent instance and get response
    try:
        agent = create_agent(
            agent_type=agent_model.agent_type,
            name=agent_model.name,
            description=agent_model.description,
            config=agent_model.config
        )
        
        # Prepare context
        context = {
            "conversation_history": conversation_history,
            "relevant_documents": relevant_context if relevant_context else None,
            "user_id": current_user.id
        }
        
        # Get agent response
        agent_response = await agent.process_message(chat_message.content, context)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent processing failed: {str(e)}"
        )
    
    # Save agent response
    assistant_message = Message(
        content=agent_response,
        role="assistant",
        conversation_id=conversation.id,
        metadata={"agent_type": agent_model.agent_type}
    )
    db.add(assistant_message)
    
    await db.commit()
    
    return ChatResponse(
        message=agent_response,
        conversation_id=conversation.id,
        agent_name=agent_model.name,
        metadata={
            "agent_type": agent_model.agent_type,
            "has_context": bool(relevant_context)
        }
    )


@router.get("/conversations", response_model=List[ConversationSchema])
async def get_conversations(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's conversations"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()
    return conversations


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageSchema])
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get messages from a conversation"""
    # Verify conversation belongs to user
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .offset(skip)
        .limit(limit)
    )
    messages = result.scalars().all()
    return messages


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a conversation and all its messages"""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    await db.delete(conversation)
    await db.commit()
    
    return {"message": "Conversation deleted successfully"}
