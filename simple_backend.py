"""Simple backend for testing the chat endpoint without auth dependencies"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

app = FastAPI(title="Simple Backend Test")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Simple backend running"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is working"}

@app.post("/chat")
async def direct_chat(message: dict):
    """Direct chat endpoint for Streamlit interface"""
    try:
        user_message = message.get("message", "")
        agent_type = message.get("agent", "companion")
        
        if not user_message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Agent-specific responses
        agent_responses = {
            "companion": f"Hello! I'm Sakhi, your companion. You said: '{user_message}'. I'm here to support you with warmth and understanding. How are you feeling today?",
            "mentor": f"Greetings! I'm Guru, your mentor. Regarding your message: '{user_message}' - Let me provide you with some guidance and help you learn and grow professionally.",
            "interview": f"Welcome! I'm Parikshak, your interview coach. About your message: '{user_message}' - Let's work together to improve your interview skills and professional communication."
        }
        
        response = agent_responses.get(agent_type, agent_responses["companion"])
        
        return {
            "response": response,
            "agent": agent_type,
            "timestamp": "2024-01-01T00:00:00Z",
            "real_ai": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
