from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database.base import get_db
from app.database.models import Agent as AgentModel, User
from app.database.schemas import Agent, AgentCreate, AgentUpdate
from app.auth.dependencies import get_current_active_user
from app.agents.base import create_agent, AGENT_TYPES

router = APIRouter()


@router.get("/", response_model=List[Agent])
async def get_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all available agents"""
    result = await db.execute(
        select(AgentModel)
        .where(AgentModel.is_active == True)
        .offset(skip)
        .limit(limit)
    )
    agents = result.scalars().all()
    return agents


@router.get("/types")
async def get_agent_types(current_user: User = Depends(get_current_active_user)):
    """Get available agent types"""
    return {
        "agent_types": list(AGENT_TYPES.keys()),
        "descriptions": {
            "research": "Specialized in research and information gathering",
            "creative": "Focused on creative tasks and content generation", 
            "coding": "Expert in programming and technical tasks",
            "general": "General-purpose conversational agent"
        }
    }


@router.post("/", response_model=Agent)
async def create_agent_endpoint(
    agent: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new agent"""
    # Validate agent type
    if agent.agent_type not in AGENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent type. Must be one of: {list(AGENT_TYPES.keys())}"
        )
    
    # Create agent in database
    db_agent = AgentModel(
        name=agent.name,
        description=agent.description,
        agent_type=agent.agent_type,
        config=agent.config,
        is_active=agent.is_active
    )
    
    db.add(db_agent)
    await db.commit()
    await db.refresh(db_agent)
    
    return db_agent


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific agent by ID"""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    return agent


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(
    agent_id: int,
    agent_update: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update an existing agent"""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Update fields
    update_data = agent_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)
    
    await db.commit()
    await db.refresh(agent)
    
    return agent


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an agent"""
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    await db.delete(agent)
    await db.commit()
    
    return {"message": "Agent deleted successfully"}
