# Skillsarathi AI - Backend

Advanced Multi-Agent AI Platform for India with real-time streaming, document understanding, and video interview capabilities.

## Features

- 🤖 Multi-Agent System (Companion, Mentor, Interview)
- 🔄 Real-time WebSocket streaming
- 📚 Document ingestion with RAG
- 🎥 Video interview capabilities
- 🗣️ Text-to-Speech with Murf AI
- 🔐 Secure authentication
- 💾 Persistent user memory

## Quick Start

```bash
# Install dependencies
uv add -r requirements.txt

# Set environment variables
export GITHUB_TOKEN=your_github_token
export MURF_API_KEY=your_murf_api_key

# Run the server
uv run main.py
```

## Architecture

- FastAPI backend with WebSocket support
- ChromaDB for vector storage
- SQLite/PostgreSQL for user data
- GitHub token fallback for LLM access
- Streamlit testing interface included
