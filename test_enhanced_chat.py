#!/usr/bin/env python3
"""
Test script for Enhanced Chat API with all three agents
Tests MCP integration and voice functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def test_enhanced_chat():
    base_url = 'http://localhost:8000'
    
    print('🧪 Testing Enhanced Chat API with all agents...')
    print('=' * 60)
    
    # Test data for each agent
    test_cases = [
        {
            'agent': 'mitra',
            'message': 'मैं आज बहुत stressed हूँ। कोई सुझाव दे सकते हैं?',
            'description': 'Emotional support in Hindi'
        },
        {
            'agent': 'guru', 
            'message': 'Can you help me learn Python programming? I am a beginner.',
            'description': 'Learning guidance'
        },
        {
            'agent': 'parikshak',
            'message': 'I have an interview tomorrow for a software engineer position. Can you help me prepare?',
            'description': 'Interview preparation'
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        # First, register a test candidate
        print('📝 Registering test candidate...')
        candidate_data = {
            "name": "Test User",
            "email": "testuser@example.com",
            "experience_level": "intermediate", 
            "target_role": "Software Engineer",
            "skills": ["Python", "JavaScript", "React"]
        }
        
        try:
            async with session.post(f'{base_url}/api/v1/candidates/register', json=candidate_data) as resp:
                if resp.status == 200:
                    candidate_response = await resp.json()
                    candidate_id = candidate_response['candidate_id']
                    print(f'✅ Candidate registered: {candidate_id}')
                else:
                    error_text = await resp.text()
                    print(f'❌ Candidate registration failed: {resp.status} - {error_text}')
                    return
        except Exception as e:
            print(f'❌ Candidate registration error: {e}')
            return
        
        print()
        
        # Test each agent
        for i, test_case in enumerate(test_cases, 1):
            agent = test_case['agent']
            message = test_case['message']
            description = test_case['description']
            
            print(f'🤖 Test {i}/3: {agent.upper()} - {description}')
            print(f'👤 User: {message}')
            
            # Prepare chat request
            chat_data = {
                "message": message,
                "candidate_id": candidate_id,
                "agent_type": agent,
                "voice_enabled": False  # Disable voice for testing
            }
            
            try:
                async with session.post(f'{base_url}/api/v1/chat/enhanced', json=chat_data) as resp:
                    if resp.status == 200:
                        response = await resp.json()
                        print(f'🤖 {agent.title()}: {response["response"]}')
                        print(f'📊 Session: {response["session_id"][:8]}...')
                        print(f'🎵 Voice: {response["voice_id"]}')
                        print('✅ Success!')
                    else:
                        error_text = await resp.text()
                        print(f'❌ Failed: {resp.status} - {error_text}')
                        
            except Exception as e:
                print(f'❌ Error: {e}')
            
            print('-' * 40)
        
        # Test agent info endpoint
        print('📋 Testing agent info endpoint...')
        try:
            async with session.get(f'{base_url}/api/v1/chat/agents/info') as resp:
                if resp.status == 200:
                    agents_info = await resp.json()
                    print(f'✅ Found {len(agents_info["agents"])} agents:')
                    for agent_info in agents_info["agents"]:
                        print(f'  - {agent_info["name"]}: {agent_info["voice_id"]} ({agent_info["language"]})')
                else:
                    error_text = await resp.text()
                    print(f'❌ Failed: {resp.status} - {error_text}')
        except Exception as e:
            print(f'❌ Error: {e}')
        
        print()
        
        # Test candidate progress
        print('📊 Testing candidate progress tracking...')
        try:
            async with session.get(f'{base_url}/api/v1/candidates/candidate/{candidate_id}/progress') as resp:
                if resp.status == 200:
                    progress = await resp.json()
                    print(f'✅ Progress tracked:')
                    print(f'  - Total sessions: {progress["total_sessions"]}')
                    print(f'  - Total messages: {progress["total_messages"]}')
                    print(f'  - Agents interacted: {progress["agents_interacted"]}')
                else:
                    error_text = await resp.text()
                    print(f'❌ Failed: {resp.status} - {error_text}')
        except Exception as e:
            print(f'❌ Error: {e}')
    
    print()
    print('🎉 Testing completed!')
    print('=' * 60)

if __name__ == "__main__":
    asyncio.run(test_enhanced_chat())