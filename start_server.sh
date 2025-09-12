#!/bin/bash

# Ensure we're in the backend directory
cd "$(dirname "$0")"

echo "🚀 Starting BuddyAgents Backend Server"
echo "📁 Current directory: $(pwd)"
echo "🐍 Python path: $(which python)"

# Set Python path and start server
export PYTHONPATH="$(pwd):$PYTHONPATH"
echo "🔧 PYTHONPATH: $PYTHONPATH"

# Start the server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
