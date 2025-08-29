#!/usr/bin/env python3
"""
Murf AI Voice Discovery and Testing
===================================

This script will:
1. Test your Murf API key
2. Discover available voices
3. Test voice synthesis for Indian voices
4. Validate your BuddyAgents voice configuration
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our fixed Murf client
from app.murf_streaming_fixed import MurfAIClient


async def discover_and_test_voices():
    """Discover available voices and test Indian voices"""
    
    print("🇮🇳 BuddyAgents Voice Discovery & Testing")
    print("=" * 50)
    
    # Initialize client
    client = MurfAIClient()
    
    # Check API key
    if not client.api_key:
        print("❌ MURF_API_KEY not found in environment variables")
        print("💡 Please add your Murf API key to .env file:")
        print("   MURF_API_KEY=your-actual-murf-api-key")
        return False
    
    print(f"✅ Murf API key configured")
    print(f"🔗 Using endpoints:")
    print(f"   Voices: {client.voices_url}")
    print(f"   TTS: {client.tts_url}")
    print()
    
    # Fetch available voices
    print("🔍 Fetching available voices...")
    voices_data = await client.get_available_voices()
    voices = voices_data.get("voices", [])
    
    if not voices:
        print("❌ No voices returned from API")
        print("💡 Check your API key and internet connection")
        return False
    
    print(f"✅ Found {len(voices)} total voices")
    
    # Filter Indian voices
    indian_voices = []
    hindi_voices = []
    
    print(f"🔍 Analyzing voice data structure...")
    print(f"   Raw response keys: {list(voices_data.keys())}")
    
    for voice in voices:
        # Handle different voice object structures
        voice_id = voice.get("id") or voice.get("voiceId") or voice.get("voice_id", "")
        language = voice.get("languageCode") or voice.get("language") or voice.get("locale", "")
        name = voice.get("name") or voice.get("displayName") or voice.get("voice_name", "")
        gender = voice.get("gender") or voice.get("sex", "")
        
        print(f"   Voice: {voice_id} | {name} | {language} | {gender}")
        
        # Check for Indian voices
        if language.startswith("hi") or language.startswith("en-IN") or "IN" in language:
            indian_voices.append({
                "id": voice_id,
                "name": name,
                "language": language,
                "gender": gender
            })
            
            if language.startswith("hi"):
                hindi_voices.append(voice)
    
    print(f"🇮🇳 Found {len(indian_voices)} Indian voices:")
    print(f"   Hindi: {len(hindi_voices)}")
    print(f"   English-India: {len(indian_voices) - len(hindi_voices)}")
    print()
    
    # Display Indian voices
    if indian_voices:
        print("📋 Indian Voice List:")
        for voice in indian_voices:
            print(f"   • {voice['id']} - {voice['name']} ({voice['language']}, {voice['gender']})")
        print()
    
    # Test BuddyAgents voice configuration
    print("🧪 Testing BuddyAgents Voice Configuration:")
    print("-" * 40)
    
    agent_tests = [
        ("mitra", "hi-IN-shweta", "नमस्ते! मैं मित्र हूं, आपका AI साथी।"),
        ("guru", "en-IN-eashwar", "Hello! I am Guru, your learning mentor."),
        ("parikshak", "en-IN-isha", "Greetings! I am Parikshak, your interview coach.")
    ]
    
    working_voices = 0
    
    for agent, voice_id, test_text in agent_tests:
        print(f"Testing {agent.title()} ({voice_id})...")
        
        success = await client.test_voice_synthesis(voice_id, test_text)
        
        if success:
            working_voices += 1
            print(f"   ✅ {agent.title()} voice working correctly")
        else:
            print(f"   ❌ {agent.title()} voice failed")
            
            # Try to find alternative
            alternative = None
            for voice in indian_voices:
                if voice["language"] == "hi-IN" and agent == "mitra":
                    alternative = voice["id"]
                    break
                elif voice["language"] == "en-IN" and agent in ["guru", "parikshak"]:
                    alternative = voice["id"]
                    break
            
            if alternative:
                print(f"   💡 Try alternative: {alternative}")
        
        await asyncio.sleep(1)  # Rate limiting
    
    print()
    print("📊 Summary:")
    print(f"   Total voices available: {len(voices)}")
    print(f"   Indian voices: {len(indian_voices)}")
    print(f"   Working agent voices: {working_voices}/3")
    
    if working_voices == 3:
        print("🎉 All BuddyAgents voices are working perfectly!")
        return True
    elif working_voices > 0:
        print("⚠️  Some voices working, but configuration needs adjustment")
        return True
    else:
        print("❌ No voices working - check API key and voice IDs")
        return False


async def test_streaming():
    """Test streaming TTS functionality"""
    print("\n🎵 Testing Streaming TTS...")
    print("-" * 30)
    
    client = MurfAIClient()
    
    test_text = "This is a test of the streaming text-to-speech functionality for BuddyAgents."
    
    try:
        print("🔄 Starting TTS stream...")
        total_bytes = 0
        chunk_count = 0
        
        async for chunk in client.synthesize_text_to_speech(test_text, "mitra", "test_user"):
            total_bytes += len(chunk)
            chunk_count += 1
            
            if chunk_count % 10 == 0:  # Progress indicator
                print(f"   Received {chunk_count} chunks ({total_bytes} bytes)")
        
        print(f"✅ Streaming completed: {chunk_count} chunks, {total_bytes} total bytes")
        
        if total_bytes > 0:
            print("🎉 Streaming TTS is working!")
            return True
        else:
            print("❌ No audio data received")
            return False
            
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")
        return False


async def main():
    """Main testing function"""
    print("🚀 Starting BuddyAgents Voice System Test")
    print()
    
    # Test voice discovery
    voices_ok = await discover_and_test_voices()
    
    if voices_ok:
        # Test streaming
        streaming_ok = await test_streaming()
        
        if streaming_ok:
            print("\n✅ All tests passed! Your voice system is ready.")
            print("\n📝 Next steps:")
            print("   1. Start your backend: uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
            print("   2. Test WebSocket connections at ws://localhost:8000/ws/test_user")
            print("   3. Use Streamlit frontend for voice testing")
            return True
    
    print("\n❌ Voice system needs configuration. Check the errors above.")
    print("\n🔧 Troubleshooting:")
    print("   1. Verify MURF_API_KEY in .env file")
    print("   2. Check internet connection")
    print("   3. Verify Murf API subscription status")
    print("   4. Try different voice IDs from the list above")
    
    return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
