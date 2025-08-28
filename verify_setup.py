#!/usr/bin/env python3
"""
BuddyAgents Backend Setup Verification
=====================================
"""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['GITHUB_TOKEN', 'MURF_API_KEY']
    optional_vars = ['OPENAI_API_KEY', 'DATABASE_URL']
    
    print("🔍 Checking environment variables...")
    
    # Check required variables
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
            print(f"❌ {var}: Not set")
        else:
            print(f"✅ {var}: {'*' * 20}")
    
    # Check optional variables
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ {var}: {'*' * 20}")
        else:
            print(f"⚠️  {var}: Not set (optional)")
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please set them in your .env file")
        return False
    
    print("\n✅ All required environment variables are set!")
    return True

def check_files():
    """Check if all required files exist"""
    required_files = [
        'app/main.py',
        'app/murf_streaming.py',
        'app/agents/multi_agent_system.py',
        'app/database/models.py',
        'app/rag/advanced_rag_system.py',
        '.env'
    ]
    
    print("\n🔍 Checking required files...")
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("\n✅ All required files are present!")
    return True

def main():
    """Main verification function"""
    print("🚀 BuddyAgents Backend Setup Verification\n")
    
    env_ok = check_environment()
    files_ok = check_files()
    
    if env_ok and files_ok:
        print("\n🎉 Setup verification completed successfully!")
        print("\n📋 Next steps:")
        print("1. uv sync")
        print("2. uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        print("3. Open http://localhost:8000/docs")
        print("\n🌟 Your BuddyAgents backend is ready!")
        return True
    else:
        print("\n❌ Setup verification failed!")
        print("Please fix the issues above before running the backend.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
