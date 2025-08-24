"""
Debug Murf API response structure
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
import aiohttp
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_murf_response():
    """Debug the exact Murf API response"""
    
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
        
        logger.info("🎵 Getting raw Murf response...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Save the raw response to a file for inspection
                    with open('murf_voices_debug.json', 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    print("📋 Raw response structure:")
                    print(f"Type: {type(result)}")
                    
                    if isinstance(result, dict):
                        print(f"Keys: {list(result.keys())}")
                        for key, value in result.items():
                            if isinstance(value, list):
                                print(f"  {key}: list with {len(value)} items")
                                if value:
                                    print(f"    First item: {type(value[0])}")
                                    if isinstance(value[0], dict):
                                        print(f"    First item keys: {list(value[0].keys())}")
                                        print(f"    Sample: {value[0]}")
                            else:
                                print(f"  {key}: {type(value)}")
                    
                    elif isinstance(result, list):
                        print(f"List with {len(result)} items")
                        if result:
                            print(f"First item type: {type(result[0])}")
                            if isinstance(result[0], dict):
                                print(f"First item keys: {list(result[0].keys())}")
                                print(f"Sample: {result[0]}")
                    
                    print("\n✅ Response saved to murf_voices_debug.json")
                    
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Murf error {response.status}: {error_text}")
                    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_murf_response())
