"""
Working Real AI Integration - GitHub LLM + Murf TTS
"""

import asyncio
import logging
import os
from typing import Optional
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkingGitHubLLM:
    """Working GitHub Models API LLM"""
    
    def __init__(self, github_token: str, model: str = "gpt-4o"):
        self.github_token = github_token
        self.model = model
        self.api_url = "https://models.inference.ai.azure.com/chat/completions"
        self._llm_type = "github"
    
    async def agenerate(self, messages_list, **kwargs):
        """Generate response using GitHub Models API"""
        from langchain.schema import ChatGeneration, LLMResult, AIMessage
        
        try:
            # Get first message list
            messages = messages_list[0] if messages_list else []
            
            # Convert messages to API format
            api_messages = []
            for msg in messages:
                if hasattr(msg, 'content'):
                    if msg.__class__.__name__ == 'HumanMessage':
                        api_messages.append({"role": "user", "content": msg.content})
                    elif msg.__class__.__name__ == 'AIMessage':
                        api_messages.append({"role": "assistant", "content": msg.content})
                else:
                    api_messages.append({"role": "user", "content": str(msg)})
            
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        generation = ChatGeneration(message=AIMessage(content=content))
                        return LLMResult(generations=[[generation]])
                    else:
                        error_text = await response.text()
                        logger.error(f"GitHub API error {response.status}: {error_text}")
                        # Return error as AI message
                        generation = ChatGeneration(message=AIMessage(content=f"I'm experiencing technical issues: {error_text}"))
                        return LLMResult(generations=[[generation]])
                        
        except Exception as e:
            logger.error(f"GitHub LLM error: {e}")
            generation = ChatGeneration(message=AIMessage(content=f"Sorry, I'm having trouble right now: {str(e)}"))
            return LLMResult(generations=[[generation]])

class WorkingMurfTTS:
    """Working Murf TTS with correct voice IDs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.murf.ai/v1"
        self.default_voice = "en-UK-hazel"  # Using the voice from debug
    
    async def synthesize(self, text: str, voice_id: Optional[str] = None) -> bytes:
        """Generate TTS audio using correct Murf API"""
        
        voice_to_use = voice_id or self.default_voice
        
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "voiceId": voice_to_use,  # Correct field name
            "text": text,
            "format": "mp3",
            "style": "Conversational"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/speech/generate",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"✅ TTS generated: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        error_text = await response.text()
                        logger.error(f"Murf TTS error {response.status}: {error_text}")
                        return b""
                        
        except Exception as e:
            logger.error(f"Murf TTS error: {e}")
            return b""

def get_working_llm():
    """Get working LLM instance"""
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        logger.info("✅ Creating working GitHub LLM")
        return WorkingGitHubLLM(github_token)
    else:
        logger.error("❌ No GitHub token found")
        return None

def get_working_tts():
    """Get working TTS instance"""
    murf_key = os.getenv("MURF_API_KEY")
    if murf_key:
        logger.info("✅ Creating working Murf TTS")
        return WorkingMurfTTS(murf_key)
    else:
        logger.error("❌ No Murf API key found")
        return None

async def test_working_integration():
    """Test the working integration"""
    
    print("🚀 Testing Working AI Integration")
    print("=" * 50)
    
    # Test LLM
    print("\n🧠 Testing GitHub LLM...")
    llm = get_working_llm()
    if llm:
        from langchain.schema import HumanMessage
        messages = [HumanMessage(content="Hello! Can you help me learn about AI? Give a brief overview.")]
        
        try:
            result = await llm.agenerate([messages])
            ai_response = result.generations[0][0].text
            print(f"✅ AI Response: {ai_response[:200]}...")
            
            # Test TTS with AI response
            print("\n🔊 Testing Murf TTS...")
            tts = get_working_tts()
            if tts:
                audio_data = await tts.synthesize("Hello! I'm your AI assistant. This is a test of text to speech.")
                if audio_data:
                    # Save audio file
                    with open("test_tts.mp3", "wb") as f:
                        f.write(audio_data)
                    print(f"✅ TTS Success: Generated {len(audio_data)} bytes, saved as test_tts.mp3")
                else:
                    print("❌ TTS failed")
            
        except Exception as e:
            print(f"❌ LLM test failed: {e}")
    
    print("\n🎉 Integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_working_integration())
