"""
Streaming Chat API for Real-time Azure OpenAI Responses
"""

import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import logging

from app.llm.azure_openai_service import azure_openai_service

logger = logging.getLogger(__name__)
router = APIRouter()

class StreamChatRequest(BaseModel):
    message: str
    agent_type: str = "mitra"
    user_id: str = "default"

@router.post("/stream")
async def stream_chat_response(request: StreamChatRequest):
    """Stream chat response for real-time user experience"""
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            # Validate agent type
            valid_agents = ["mitra", "guru", "parikshak"]
            if request.agent_type not in valid_agents:
                yield f"data: {json.dumps({'error': 'Invalid agent type'})}\n\n"
                return
            
            # Prepare messages
            messages = [{"role": "user", "content": request.message}]
            
            # Stream response from Azure OpenAI
            async for chunk in azure_openai_service.generate_response(
                messages=messages,
                agent_type=request.agent_type,
                stream=True,
                max_tokens=500,
                temperature=0.7
            ):
                # Format as Server-Sent Events
                data = json.dumps({"content": chunk, "agent": request.agent_type})
                yield f"data: {data}\n\n"
                
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)
            
            # Send completion signal
            yield f"data: {json.dumps({'content': '[DONE]', 'agent': request.agent_type})}\n\n"
            
        except Exception as e:
            error_msg = f"Streaming error: {str(e)}"
            logger.error(error_msg)
            yield f"data: {json.dumps({'error': error_msg})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )
