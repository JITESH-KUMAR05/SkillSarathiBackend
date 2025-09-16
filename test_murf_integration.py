import asyncio
import os
from app.murf_streaming import murf_service
from app.core.config import get_settings

async def test_integration():
    """Test the complete Murf integration"""
    print("🧪 Testing Murf AI Integration...")
    
    # Load settings
    settings = get_settings()
    
    # Check if API key is loaded from settings
    if not murf_service.api_key:
        murf_service.api_key = settings.MURF_API_KEY
        print(f"🔑 Loaded API key from settings: {murf_service.api_key[:8]}...")
    
    # Validate setup
    results = await murf_service.validate_setup()

    if results["api_key_present"]:
        print("✅ API key configured")
    else:
        print("❌ API key missing - check .env file")
        return

    if results["auth_token_valid"]:
        print("✅ Authentication working")
    else:
        print("❌ Authentication failed - check API key validity")
        print("ℹ️  Note: This is expected if the API key is invalid/expired")

    # Test each agent voice
    for agent in ["mitra", "guru", "parikshak"]:
        print(f"\n🎵 Testing {agent} voice...")
        
        test_text = f"Hello, I am {agent}, your AI companion. How can I help you today?"
        
        # Test HTTP generation
        audio_data = await murf_service.generate_speech_http(test_text, agent)
        if audio_data and len(audio_data) > 1000:
            print(f"   ✅ HTTP generation: {len(audio_data)} bytes")
        else:
            print(f"   ❌ HTTP generation failed")
        
        # Test streaming
        chunks = []
        async for chunk in murf_service.stream_speech_websocket(test_text, agent):
            chunks.append(chunk)
            if len(chunks) >= 3:  # Test first few chunks
                break
        
        total_size = sum(len(chunk) for chunk in chunks)
        if total_size > 0:
            print(f"   ✅ Streaming: {len(chunks)} chunks, {total_size} bytes")
        else:
            print(f"   ❌ Streaming failed")

    print("\n🎯 Integration test completed!")

if __name__ == "__main__":
    asyncio.run(test_integration())