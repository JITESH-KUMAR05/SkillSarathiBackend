"""
Simple working test with real GitHub LLM
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_real_github_llm():
    """Test the real GitHub LLM directly"""
    
    # Get GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("❌ No GitHub token found!")
        return
    
    logger.info(f"✅ GitHub token found: {github_token[:10]}...")
    
    try:
        import aiohttp
        from langchain.schema import ChatGeneration, LLMResult, AIMessage, HumanMessage
        
        # GitHub API details
        api_url = "https://models.inference.ai.azure.com/chat/completions"
        model = "gpt-4o"
        
        # Test message
        messages = [{"role": "user", "content": "Hello! Can you help me learn about AI?"}]
        
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        logger.info("🚀 Calling GitHub Models API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url, 
                headers=headers, 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info("✅ GitHub API response received!")
                    print(f"🤖 AI Response: {content[:200]}...")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ GitHub API error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False

async def test_murf_tts():
    """Test Murf TTS API"""
    
    murf_api_key = os.getenv("MURF_API_KEY")
    if not murf_api_key:
        logger.error("❌ No Murf API key found!")
        return
    
    logger.info(f"✅ Murf API key found: {murf_api_key[:10]}...")
    
    try:
        import aiohttp
        
        url = "https://api.murf.ai/v1/speech/generate"
        headers = {
            "api-key": murf_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "voice_id": "en-US-sarah", 
            "text": "Hello! This is a test of Murf AI text to speech.",
            "format": "mp3",
            "sample_rate": 24000
        }
        
        logger.info("🎵 Testing Murf TTS API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    logger.info("✅ Murf TTS working!")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Murf API error {response.status}: {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Murf TTS error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Direct API Testing")
    print("=" * 50)
    
    # Test GitHub LLM
    print("\n🧠 Testing GitHub LLM...")
    github_success = await test_real_github_llm()
    
    # Test Murf TTS
    print("\n🔊 Testing Murf TTS...")
    murf_success = await test_murf_tts()
    
    print("\n" + "=" * 50)
    print(f"📊 Results:")
    print(f"GitHub LLM: {'✅ Working' if github_success else '❌ Failed'}")
    print(f"Murf TTS: {'✅ Working' if murf_success else '❌ Failed'}")
    
    if github_success and murf_success:
        print("🎉 All APIs are working! Your app should work perfectly!")
    else:
        print("⚠️  Some APIs need fixing. Check your tokens and API endpoints.")

if __name__ == "__main__":
    asyncio.run(main())
