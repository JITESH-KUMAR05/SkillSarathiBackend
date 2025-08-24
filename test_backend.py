"""
Test GitHub LLM Implementation
Quick test to verify GitHub token fallback is working
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.llm.llm_factory import get_llm
from app.core.config import settings

async def test_github_llm():
    """Test GitHub LLM functionality"""
    print("🧪 Testing Skillsarathi AI - GitHub LLM Integration")
    print("=" * 50)
    
    # Check environment
    print(f"🔑 GitHub Token: {'✅ Set' if settings.GITHUB_TOKEN else '❌ Missing'}")
    print(f"🔑 OpenAI Key: {'✅ Set' if settings.OPENAI_API_KEY else '❌ Not Set (using GitHub fallback)'}")
    print(f"🔑 Murf API Key: {'✅ Set' if settings.MURF_API_KEY else '❌ Missing'}")
    print()
    
    try:
        # Get LLM instance
        print("🤖 Initializing LLM...")
        llm = get_llm()
        print(f"✅ LLM Type: {type(llm).__name__}")
        print()
        
        # Test simple generation
        print("💭 Testing simple generation...")
        test_prompt = "Hello! I am testing Skillsarathi AI. Please respond with a brief introduction about yourself as an AI assistant for India."
        
        print(f"📝 Prompt: {test_prompt}")
        print("⏳ Generating response...")
        
        response = await llm.agenerate_prompt([test_prompt])
        response_text = response.generations[0][0].text
        
        print("✅ Response generated successfully!")
        print(f"📄 Response: {response_text}")
        print()
        
        # Test conversation-style interaction
        print("💬 Testing conversation-style interaction...")
        
        from langchain.schema import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="You are Skillsarathi AI, an AI assistant designed specifically for users in India. You understand Indian culture, languages, and context."),
            HumanMessage(content="Can you help me with career guidance in the Indian job market?")
        ]
        
        conv_response = await llm.agenerate([messages])
        conv_text = conv_response.generations[0][0].text
        
        print("✅ Conversation response generated!")
        print(f"📄 Response: {conv_text}")
        print()
        
        print("🎉 GitHub LLM test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing GitHub LLM: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_multi_agent_system():
    """Test the multi-agent system"""
    print("\n🤖 Testing Multi-Agent System")
    print("=" * 30)
    
    try:
        from app.agents.skillsarathi_agents import multi_agent_system, UserContext
        
        # Create test user context
        user_context = UserContext(
            user_id="test_user_123",
            name="Test User",
            age=25,
            location="Mumbai, India",
            profession="Software Engineer",
            interests=["AI", "Technology", "Learning"],
            learning_goals=["Machine Learning", "Career Growth"]
        )
        
        print(f"👤 User Context: {user_context.name} from {user_context.location}")
        
        # Test companion agent
        print("\n🤗 Testing Companion Agent...")
        companion_response = await multi_agent_system.process_message(
            message="I'm feeling stressed about my career. Can you help me?",
            user_context=user_context,
            agent_type="companion"
        )
        
        print(f"✅ Companion Response: {companion_response.get('text', 'No response')[:100]}...")
        
        # Test mentor agent
        print("\n👨‍🏫 Testing Mentor Agent...")
        mentor_response = await multi_agent_system.process_message(
            message="How can I learn machine learning effectively?",
            user_context=user_context,
            agent_type="mentor"
        )
        
        print(f"✅ Mentor Response: {mentor_response.get('text', 'No response')[:100]}...")
        
        # Test auto-detection
        print("\n🎯 Testing Auto-Detection...")
        auto_response = await multi_agent_system.process_message(
            message="I want to practice for a job interview",
            user_context=user_context,
            agent_type="auto"
        )
        
        print(f"✅ Auto-detected Agent: {auto_response.get('agent_type', 'unknown')}")
        print(f"✅ Response: {auto_response.get('text', 'No response')[:100]}...")
        
        print("🎉 Multi-agent system test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing multi-agent system: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Skillsarathi AI Backend Test Suite")
    print("=" * 40)
    
    # Test 1: GitHub LLM
    llm_success = await test_github_llm()
    
    # Test 2: Multi-agent system
    if llm_success:
        agent_success = await test_multi_agent_system()
    else:
        print("⏭️ Skipping multi-agent test due to LLM failure")
        agent_success = False
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 20)
    print(f"🤖 GitHub LLM: {'✅ PASS' if llm_success else '❌ FAIL'}")
    print(f"👥 Multi-Agent: {'✅ PASS' if agent_success else '❌ FAIL'}")
    
    if llm_success and agent_success:
        print("\n🎉 All tests passed! Backend is ready to start.")
        print("\n🚀 Next steps:")
        print("1. Run: uv run main.py (to start the backend)")
        print("2. Run: streamlit run streamlit_test.py (to start testing interface)")
        print("3. Open: http://localhost:8000/docs (to see API documentation)")
    else:
        print("\n⚠️ Some tests failed. Please check the configuration.")
    
    return llm_success and agent_success

if __name__ == "__main__":
    asyncio.run(main())
