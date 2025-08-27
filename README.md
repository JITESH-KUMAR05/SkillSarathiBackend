# Skillsarathi AI - Backend

Advanced Multi-Agent AI Platform for India with real-time streaming, document understanding, and video interview capabilities.

## 🔒 SECURITY FIRST

**IMPORTANT**: Before running the application, set up your environment variables:

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual API keys (see `SECURITY.md` for details)

3. Never commit `.env` to version control!

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
# 1. Set up environment (REQUIRED)
cp .env.example .env
# Edit .env with your API keys

# 2. Install dependencies
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
