"""
Test GitHub LLM Integration with Real API
"""

import asyncio
import logging
from app.llm.llm_factory import get_llm
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_github_llm():
    """Test GitHub LLM with real API call"""
    print("🧪 Testing GitHub LLM Integration")
    print("=" * 50)
    
    # Check if GitHub token is available
    if not settings.GITHUB_TOKEN:
        print("❌ No GitHub token found in settings")
        return
    
    print(f"✅ GitHub token found: {settings.GITHUB_TOKEN[:10]}...")
    
    try:
        # Get LLM instance
        llm = get_llm()
        print(f"✅ LLM initialized: {llm._llm_type}")
        
        # Test messages
        test_messages = [
            "Hello! Can you help me?",
            "What is machine learning?",
            "I'm preparing for a software engineering interview. Can you help?",
            "I'm feeling stressed about my exams. Any advice?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n🚀 Test {i}: '{message}'")
            
            # Create message format
            from langchain.schema import HumanMessage
            messages = [HumanMessage(content=message)]
            
            # Test async generation
            try:
                import time
                start_time = time.time()
                
                response = await llm._agenerate(messages)
                ai_response = response.generations[0][0].message.content
                
                end_time = time.time()
                latency = round((end_time - start_time) * 1000, 2)
                
                print(f"🤖 Response: {ai_response[:100]}...")
                print(f"⚡ Latency: {latency}ms")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                
            # Wait between requests
            await asyncio.sleep(1)
    
    except Exception as e:
        print(f"❌ Failed to test GitHub LLM: {e}")

async def test_murf_integration():
    """Test Murf AI TTS integration"""
    print("\n🔊 Testing Murf AI TTS Integration")
    print("=" * 50)
    
    if not settings.MURF_API_KEY:
        print("❌ No Murf API key found")
        return
    
    print(f"✅ Murf API key found: {settings.MURF_API_KEY[:10]}...")
    
    try:
        from app.murf_tts import MurfHTTPTTS
        
        tts = MurfHTTPTTS(settings.MURF_API_KEY)
        
        # Test TTS
        test_text = "Hello! I'm Skillsarathi AI, your intelligent companion."
        print(f"🎵 Generating TTS for: '{test_text}'")
        
        audio_data = await tts.synthesize(test_text)
        
        if audio_data:
            print(f"✅ TTS generated successfully! Audio size: {len(audio_data)} bytes")
        else:
            print("❌ TTS generation failed")
            
    except Exception as e:
        print(f"❌ Murf TTS error: {e}")

if __name__ == "__main__":
    print("🚀 Skillsarathi AI - API Integration Test")
    print("=" * 60)
    
    asyncio.run(test_github_llm())
    asyncio.run(test_murf_integration())
    
    print("\n✅ Integration tests completed!")
    print("\n🎯 Next Steps:")
    print("1. Backend is running at: http://localhost:8000")
    print("2. Advanced interface at: http://localhost:8502")
    print("3. Test WebSocket at: ws://localhost:8000/ws")
    print("4. Use the interface to test all three agents!")
