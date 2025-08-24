"""
Simple WebSocket Test Client for Skillsarathi AI Backend
"""

import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    
    try:
        print("🔗 Connecting to Skillsarathi AI backend...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Listen for welcome message
            welcome = await websocket.recv()
            welcome_data = json.loads(welcome)
            print(f"📩 Received: {welcome_data}")
            
            # Test messages
            test_messages = [
                "Hello! Can you help me?",
                "What is Python programming?",
                "I'm feeling stressed about exams",
                "Can you help me prepare for an interview?"
            ]
            
            for i, message in enumerate(test_messages, 1):
                print(f"\n🚀 Test {i}: Sending '{message}'")
                
                # Send message
                start_time = time.time()
                await websocket.send(json.dumps({
                    "message": message,
                    "timestamp": time.time()
                }))
                
                # Receive typing indicator
                typing_response = await websocket.recv()
                typing_data = json.loads(typing_response)
                print(f"⌨️  {typing_data.get('message', 'Typing...')}")
                
                # Receive actual response
                response = await websocket.recv()
                response_data = json.loads(response)
                end_time = time.time()
                
                latency = round((end_time - start_time) * 1000, 2)
                print(f"🤖 Response: {response_data.get('message', '')}")
                print(f"⚡ Latency: {latency}ms")
                
                # Wait a bit between messages
                await asyncio.sleep(1)
    
    except websockets.exceptions.ConnectionClosed:
        print("❌ Connection closed")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Skillsarathi AI - WebSocket Test Client")
    print("=" * 50)
    asyncio.run(test_websocket())
    print("\n✅ Test completed!")
