#!/usr/bin/env python3
"""
Test script to verify audio fixes work correctly
"""

import requests
import io

def test_voice_generation():
    """Test the voice generation API"""
    
    # Test API endpoint
    url = "http://localhost:8000/api/chat/voice/generate"
    
    # Test data
    test_data = {
        "text": "Hello, this is a test message for voice generation",
        "agent_type": "mitra",
        "user_id": "test_user"
    }
    
    try:
        print("🔄 Testing voice generation API...")
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"📡 Response status: {response.status_code}")
        print(f"📡 Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            # Check if we got binary audio data
            audio_data = response.content
            print(f"🔊 Audio data size: {len(audio_data)} bytes")
            
            # Test BytesIO creation (this is what Streamlit will do)
            try:
                audio_io = io.BytesIO(audio_data)
                print(f"✅ BytesIO creation successful: {len(audio_io.getvalue())} bytes")
                
                # Save test file
                with open("test_voice_output.wav", "wb") as f:
                    f.write(audio_data)
                print("💾 Audio saved to test_voice_output.wav for manual testing")
                
                return True
                
            except Exception as io_error:
                print(f"❌ BytesIO creation failed: {io_error}")
                return False
        else:
            print(f"❌ API request failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Testing Audio Fix for BuddyAgents")
    print("=" * 50)
    
    if test_voice_generation():
        print("\n✅ Audio system test PASSED!")
        print("💡 The MediaFileHandler issue should be resolved.")
        print("💡 Test the Streamlit app now!")
    else:
        print("\n❌ Audio system test FAILED!")
        print("💡 Check backend logs for more details.")
