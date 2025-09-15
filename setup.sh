#!/bin/bash

# BuddyAgents Backend Setup Script
# This script sets up the Python environment and installs dependencies

echo "🚀 Setting up BuddyAgents Backend Environment..."

# Check if Python 3.8+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p static/videos
mkdir -p static/audio
mkdir -p static/images
mkdir -p logs

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔑 Creating .env file..."
    cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=sqlite:///./buddyagents.db

# Azure OpenAI Configuration - Primary Region (East US 2)
AZURE_OPENAI_ENDPOINT_PRIMARY=https://buddyagentstest.openai.azure.com/
AZURE_OPENAI_API_KEY_PRIMARY=your-primary-api-key
AZURE_OPENAI_API_VERSION_CHAT=2024-02-15-preview
AZURE_OPENAI_API_VERSION_VIDEO=2024-06-01
AZURE_OPENAI_API_VERSION_TRANSCRIBE=2024-02-15-preview

# Azure OpenAI Configuration - Secondary Region (Sweden Central)
AZURE_OPENAI_ENDPOINT_SECONDARY=https://jites-mfjdgyq9-swedencentral.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY_SECONDARY=your-secondary-api-key

# Model Deployments
MODEL_DEPLOYMENT_CHAT=buddyagents-model-router
MODEL_DEPLOYMENT_VIDEO=sora-buddyagents
MODEL_DEPLOYMENT_TRANSCRIPTION=gpt-4o-transcribe-buddyagents
MODEL_DEPLOYMENT_REALTIME=gpt-realtime-buddyagents

# CORS and Security
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080","https://your-domain.com"]
ALLOWED_HOSTS=["localhost","127.0.0.1","your-domain.com"]

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0
EOF
    echo "⚠️ Please update the .env file with your actual API keys and configuration!"
fi

echo "✅ Backend environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your Azure OpenAI API keys"
echo "2. Activate the environment: source venv/bin/activate"
echo "3. Run the application: python -m uvicorn app.main:app --reload"
echo ""
echo "🎉 Happy coding with BuddyAgents!"