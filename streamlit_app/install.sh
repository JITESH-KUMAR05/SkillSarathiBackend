#!/bin/bash

# BuddyAgents Frontend Installation Script
# This script installs all dependencies for the Streamlit frontend

echo "🚀 Installing BuddyAgents Streamlit Frontend..."
echo "================================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv package manager not found"
    echo "Please install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Navigate to the frontend directory
cd "$(dirname "$0")"

echo "📦 Installing dependencies with uv..."

# Install core Streamlit dependencies
uv add streamlit
uv add streamlit-webrtc
uv add streamlit-option-menu
uv add streamlit-chat
uv add streamlit-extras

# Install communication dependencies
uv add requests
uv add websockets
uv add aiohttp

# Install video processing dependencies
uv add opencv-python
uv add aiortc

# Install audio processing dependencies
uv add numpy
uv add scipy

# Install authentication dependencies
uv add pyjwt
uv add cryptography

# Install data handling dependencies
uv add pydantic
uv add python-dotenv

echo "✅ Dependencies installed successfully!"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# BuddyAgents Frontend Configuration
BACKEND_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000
DEBUG=true
API_TIMEOUT=30

# Murf AI Configuration (optional - for voice features)
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# WebRTC Configuration
STUN_SERVER=stun:stun.l.google.com:19302
EOF
    echo "✅ Created .env file with default configuration"
    echo "⚠️  Please update the .env file with your actual API keys"
fi

echo ""
echo "🎉 Frontend installation complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Update .env file with your API keys"
echo "2. Start the backend server: cd .. && uv run main.py"
echo "3. Start the frontend: uv run streamlit run app.py"
echo ""
echo "🌐 Frontend will be available at: http://localhost:8501"
echo "🔗 Backend API at: http://localhost:8000"
echo ""
echo "🤖 Available Agents:"
echo "   • 🤗 Mitra - Emotional support and mental wellness"
echo "   • 🎓 Guru - Learning mentor and educational guide"  
echo "   • 💼 Parikshak - Interview coach with video analysis"
echo ""
