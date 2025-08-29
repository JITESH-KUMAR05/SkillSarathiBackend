# 🇮🇳 BuddyAgents Voice System Setup Guide

## Step-by-Step Implementation Guide

### Prerequisites ✅

1. **Murf AI API Key**: Sign up at [murf.ai](https://murf.ai) and get your API key
2. **GitHub Token**: For GitHub Copilot LLM access (if you have GitHub Student Pack)
3. **Python 3.11+** with `uv` package manager

### Step 1: Configure Environment Variables

Edit your `.env` file and add your API keys:

```bash
# Required for voice features
MURF_API_KEY=your-actual-murf-api-key-here

# Required for LLM (use GitHub Student Pack)
GITHUB_TOKEN=your-github-token-here

# Optional but recommended
OPENAI_API_KEY=your-openai-key (if available)
```

### Step 2: Test Voice System

Run the voice discovery and testing script:

```bash
# Test your Murf API configuration
python test_voice_system.py
```

This will:
- ✅ Verify your API key works
- 🔍 Discover available Indian voices  
- 🧪 Test voice synthesis for each agent
- 📊 Show configuration status

Expected output:
```
🇮🇳 BuddyAgents Voice Discovery & Testing
==================================================
✅ Murf API key configured
🔍 Fetching available voices...
✅ Found 50+ total voices
🇮🇳 Found 8 Indian voices:
   Hindi: 3
   English-India: 5

🧪 Testing BuddyAgents Voice Configuration:
----------------------------------------
Testing Mitra (hi-IN-shweta)...
   ✅ Mitra voice working correctly
Testing Guru (en-IN-eashwar)...
   ✅ Guru voice working correctly  
Testing Parikshak (en-IN-isha)...
   ✅ Parikshak voice working correctly

📊 Summary:
   Working agent voices: 3/3
🎉 All BuddyAgents voices are working perfectly!
```

### Step 3: Start the Backend

```bash
# Install dependencies
uv sync

# Start the backend server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected startup logs:
```
🚀 Starting BuddyAgents backend...
✅ Database tables created
✅ Murf AI configured - 3/3 agent voices working
✅ Advanced RAG system initialized  
🟢 BuddyAgents backend ready!
```

### Step 4: Test API Endpoints

Open your browser to test:

1. **Backend Status**: http://localhost:8000
2. **API Documentation**: http://localhost:8000/docs
3. **Health Check**: http://localhost:8000/health

### Step 5: Test WebSocket Voice Streaming

Test the WebSocket connection with a simple script:

```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/test_user"
    
    async with websockets.connect(uri) as websocket:
        # Start voice streaming
        await websocket.send(json.dumps({
            "type": "start_voice_streaming",
            "agent": "mitra"
        }))
        
        # Send a chat message
        await websocket.send(json.dumps({
            "type": "chat_message", 
            "message": "Hello Mitra!",
            "agent": "mitra"
        }))
        
        # Listen for responses
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data['type']}")
            
            if data['type'] == 'agent_response':
                print(f"Agent said: {data['message']}")
            elif data['type'] == 'audio_stream_start':
                print("🎵 Audio streaming started")
                # Audio chunks will come as binary data
                break

asyncio.run(test_websocket())
```

### Step 6: Launch Streamlit Frontend (for testing)

```bash
# Start Streamlit app for voice testing
uv run streamlit run multi_agent_app.py --server.port 8501
```

Open http://localhost:8501 to test voice features interactively.

## Troubleshooting 🔧

### Issue: "0 Indian voices found"
**Solution**: 
1. Check your Murf API key is valid
2. Verify internet connection
3. Check if your Murf subscription includes Indian voices

### Issue: "WebSocket connection failed with 404"
**Solution**: 
1. Murf may not support WebSocket streaming yet
2. Our implementation uses HTTP API with chunked streaming
3. This provides good real-time performance

### Issue: "Agent voices not working"
**Solution**:
1. Run `python test_voice_system.py` to find working voice IDs
2. Update voice IDs in `app/murf_streaming_fixed.py`
3. Use voice IDs returned by the discovery script

### Issue: "No audio output in frontend"
**Solution**:
1. Check browser audio permissions
2. Verify WebSocket connection in browser dev tools
3. Test with simple audio playback first

## Voice ID Configuration 🎵

Current working voice IDs (update based on your test results):

```python
agent_voices = {
    "mitra": "hi-IN-shweta",      # Hindi female - warm, caring
    "guru": "en-IN-eashwar",      # English-Indian male - professional  
    "parikshak": "en-IN-isha"     # English-Indian female - clear
}
```

To find alternative voice IDs, check the output of `test_voice_system.py`.

## Production Deployment 🚀

For production:

1. **Use environment variables** for all API keys
2. **Enable HTTPS** for WebSocket connections
3. **Configure rate limiting** for Murf API calls
4. **Add audio caching** to reduce API calls
5. **Monitor API usage** and costs

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Backend status page |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |
| `/ws/{user_id}` | WebSocket | Real-time chat + voice |
| `/api/chat/send` | POST | Send text message |
| `/api/agents/{agent_type}/voice` | POST | Generate voice audio |

## Next Steps 🎯

1. ✅ Get voice system working
2. 🎨 Implement frontend voice UI
3. 📹 Add video chat for Parikshak agent
4. 🧠 Enhance RAG personalization  
5. 🚀 Deploy to production

---

**Need help?** Check the logs and run `python test_voice_system.py` for diagnostics.
