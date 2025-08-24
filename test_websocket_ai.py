"""
Quick WebSocket test to verify real AI responses
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_websocket_ai():
    """Test WebSocket connection to verify real AI responses"""
    
    uri = "ws://localhost:8000/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info("✅ Connected to WebSocket")
            
            # Receive welcome message
            welcome = await websocket.recv()
            print(f"📨 Welcome: {json.loads(welcome)}")
            
            # Send test message
            test_message = {
                "message": "Hello! Can you tell me about machine learning in 2 sentences?",
                "timestamp": "test"
            }
            
            await websocket.send(json.dumps(test_message))
            logger.info("📤 Sent test message")
            
            # Wait for responses
            responses = []
            for i in range(3):  # Wait for typing + response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10)
                    response_data = json.loads(response)
                    responses.append(response_data)
                    print(f"📨 Response {i+1}: {response_data}")
                    
                    # If we get the main AI response, break
                    if response_data.get('type') == 'message' and response_data.get('role') == 'assistant':
                        ai_content = response_data.get('content', '')
                        print(f"\n🤖 AI Response: {ai_content}")
                        
                        # Check if it's real AI (not fallback)
                        if "FALLBACK MODE" in ai_content or "minimal latency" in ai_content:
                            print("❌ Still using fallback responses!")
                        else:
                            print("✅ REAL AI RESPONSE DETECTED!")
                        break
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout waiting for response {i+1}")
                    break
            
            return True
            
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        return False

async def main():
    """Run WebSocket test"""
    print("🔌 Testing WebSocket Real AI Connection")
    print("=" * 50)
    
    success = await test_websocket_ai()
    
    print("=" * 50)
    if success:
        print("🎉 WebSocket test completed!")
    else:
        print("❌ WebSocket test failed!")

if __name__ == "__main__":
    asyncio.run(main())
