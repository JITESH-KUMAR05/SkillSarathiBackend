"""
Get valid Murf voices and test GitHub API
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_murf_voices():
    """Get available Murf voices"""
    
    murf_api_key = os.getenv("MURF_API_KEY")
    if not murf_api_key:
        logger.error("❌ No Murf API key found!")
        return
    
    try:
        url = "https://api.murf.ai/v1/speech/voices"
        headers = {
            "api-key": murf_api_key,
            "Content-Type": "application/json"
        }
        
        logger.info("🎵 Getting Murf voices...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("✅ Murf voices retrieved!")
                    
                    # Handle both array and object responses
                    voices = result if isinstance(result, list) else result.get('voices', [])
                    print(f"📋 Found {len(voices)} voices")
                    
                    # Show first few voices
                    for i, voice in enumerate(voices[:10]):  # Show first 10
                        voice_id = voice.get('voice_id') or voice.get('id', 'N/A')
                        name = voice.get('name', 'N/A')
                        language = voice.get('language', voice.get('lang', 'N/A'))
                        print(f"  {i+1}. {voice_id} - {name} ({language})")
                    
                    # Find English voices
                    english_voices = []
                    for v in voices:
                        voice_id = v.get('voice_id') or v.get('id', '')
                        if 'en' in voice_id.lower():
                            english_voices.append(v)
                    
                    print(f"\n🇺🇸 English voices ({len(english_voices)}):")
                    for voice in english_voices[:5]:
                        voice_id = voice.get('voice_id') or voice.get('id', 'N/A')
                        name = voice.get('name', 'N/A')
                        print(f"  - {voice_id} ({name})")
                    
                    return english_voices[0].get('voice_id') or english_voices[0].get('id') if english_voices else None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Murf voices error {response.status}: {error_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"❌ Error getting Murf voices: {e}")
        return None

async def test_github_detailed():
    """Test GitHub API with detailed error handling"""
    
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("❌ No GitHub token found!")
        return
    
    try:
        api_url = "https://models.inference.ai.azure.com/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Say hello"}],
            "max_tokens": 100
        }
        
        logger.info("🚀 Testing GitHub API...")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url, 
                headers=headers, 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"📊 GitHub API Response:")
                print(f"  Status: {status}")
                print(f"  Response: {response_text[:500]}...")
                
                if status == 200:
                    import json
                    result = json.loads(response_text)
                    content = result['choices'][0]['message']['content']
                    print(f"✅ Success! AI said: {content}")
                    return True
                else:
                    print(f"❌ Error {status}: {response_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ GitHub API error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run tests"""
    print("🔍 API Debugging")
    print("=" * 50)
    
    # Test GitHub in detail
    print("\n🧠 Testing GitHub API in detail...")
    await test_github_detailed()
    
    # Get Murf voices
    print("\n🎵 Getting Murf voices...")
    valid_voice = await get_murf_voices()
    
    if valid_voice:
        print(f"\n✅ Use this voice ID: {valid_voice}")

if __name__ == "__main__":
    asyncio.run(main())
