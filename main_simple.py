"""
Simple Skillsarathi AI Backend - Minimal setup for testing
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Skillsarathi AI - Minimal Backend",
    description="AI companion platform with minimal latency",
    version="1.0.0"
)

# Enable CORS for frontend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Skillsarathi AI Backend is running!",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        # Test LLM
        from app.llm.llm_factory import get_llm
        llm = get_llm()
        llm_status = "✅ Ready"
    except Exception as e:
        llm_status = f"❌ Error: {str(e)}"
    
    return {
        "status": "healthy",
        "components": {
            "llm": llm_status,
            "websocket": "✅ Ready",
            "active_connections": len(active_connections)
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    client_id = id(websocket)
    active_connections[client_id] = websocket
    
    # Send welcome message
    await websocket.send_text(json.dumps({
        "type": "system",
        "message": "Welcome to Skillsarathi AI! I'm ready to help with minimal latency.",
        "client_id": str(client_id)
    }))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message.strip():
                continue
            
            # Send typing indicator
            await websocket.send_text(json.dumps({
                "type": "typing",
                "message": "Thinking..."
            }))
            
            # Get AI response
            try:
                # Import and use the real LLM
                from app.llm.llm_factory import get_llm
                llm = get_llm()
                
                # Generate proper response using real AI
                messages = [{
                    "role": "user",
                    "content": user_message
                }]
                
                response = await llm.agenerate([messages])
                ai_response = response.generations[0][0].text
                
                # Send AI response
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": str(message_data.get("timestamp"))
                }))
                    # Use the simple LLM
                    response = await llm._agenerate([user_message])
                    ai_response = response.generations[0][0].message.content
                else:
                    # Fallback to simple response
                    ai_response = f"I received your message: '{user_message}'. I'm here to help you with minimal latency!"
            
            except Exception as e:
                logger.error(f"LLM error: {e}")
                ai_response = f"I understand you said: '{user_message}'. I'm here to help! (Note: Using fallback mode)"
            
            # Send response back to client
            await websocket.send_text(json.dumps({
                "type": "message",
                "message": ai_response,
                "client_id": str(client_id)
            }))
    
    except WebSocketDisconnect:
        if client_id in active_connections:
            del active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if client_id in active_connections:
            del active_connections[client_id]

if __name__ == "__main__":
    print("🚀 Starting Skillsarathi AI Backend (Minimal Mode)")
    print("🔗 WebSocket endpoint: ws://localhost:8000/ws")
    print("📖 API docs: http://localhost:8000/docs")
    print("💚 Health check: http://localhost:8000/health")
    
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
