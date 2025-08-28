# 🇮🇳 BuddyAgents Backend

Advanced Multi-Agent AI Platform for India with real-time voice streaming, intelligent RAG, and personalized AI agents.

## 🚀 Features

- **🤖 3 Specialized AI Agents**: Mitra (Friend), Guru (Mentor), Parikshak (Interviewer)
- **🎵 Real-time Voice Synthesis**: Murf AI integration with Indian voices
- **📚 Intelligent RAG System**: Document understanding with personalized memory
- **💬 Advanced Chat API**: WebSocket and REST endpoints
- **🔐 Secure Authentication**: JWT-based user management
- **📊 Analytics Dashboard**: User insights and system metrics

## 🔧 Tech Stack

- **Backend**: FastAPI + SQLAlchemy + ChromaDB
- **LLM**: GitHub Copilot (GPT-4o) integration
- **Voice**: Murf AI TTS with Indian voices (Hindi & English)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Package Management**: UV (modern Python package manager)

## ⚡ Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys:
# GITHUB_TOKEN=your_github_personal_access_token
# MURF_API_KEY=your_murf_ai_api_key
# OPENAI_API_KEY=your_openai_key (optional)
```

### 2. Install Dependencies

```bash
# Install all dependencies using UV
uv sync
```

### 3. Run the Backend

```bash
# Start the FastAPI server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **WebSocket**: ws://localhost:8000/ws/{user_id}

## 📁 Project Structure

```
backend/
├── app/                    # Main application directory
│   ├── main.py            # FastAPI application entry point
│   ├── api/               # API routes and endpoints
│   │   ├── chat.py       # Chat and messaging endpoints
│   │   ├── profiles.py   # User profile management
│   │   └── auth.py       # Authentication endpoints
│   ├── agents/           # AI agent implementations
│   │   ├── base.py       # Base agent class
│   │   └── multi_agent_system.py # Agent orchestrator
│   ├── core/             # Core configurations
│   │   └── config.py     # Settings and environment
│   ├── database/         # Database models and setup
│   │   ├── base.py       # Database configuration
│   │   ├── models.py     # SQLAlchemy models
│   │   └── schemas.py    # Pydantic schemas
│   ├── rag/              # RAG system implementation
│   │   └── advanced_rag_system.py # Document processing
│   ├── llm/              # LLM integrations
│   │   └── github_llm.py # GitHub Copilot integration
│   ├── murf_streaming.py # Murf AI voice integration
│   └── websocket_handler.py # WebSocket management
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
├── pyproject.toml       # UV project configuration
└── README.md            # This file
```

## 🎵 Voice Agents

The platform uses Murf AI for realistic Indian voice synthesis:

- **Mitra** (Friend): `hi-IN-shweta` - Warm Hindi female voice
- **Guru** (Mentor): `en-IN-eashwar` - Professional English-Indian male voice  
- **Parikshak** (Interviewer): `en-IN-isha` - Clear English-Indian female voice

## 🔥 API Endpoints

### Core Endpoints
- `GET /health` - System health check
- `GET /docs` - Interactive API documentation
- `GET /` - Welcome page with system status

### Chat & Messaging
- `POST /api/chat/` - Send message to AI agents
- `WS /ws/{user_id}` - WebSocket real-time communication

### User Management
- `GET /api/users/{user_id}/stats` - User statistics
- `POST /api/auth/login` - User authentication
- `GET /api/profiles/{user_id}` - User profile

### Document Processing
- `POST /api/documents/upload` - Upload documents for RAG
- `GET /api/documents/` - List user documents

## 🧪 Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test chat endpoint
curl -X POST "http://localhost:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "agent": "mitra", "user_id": "test_user"}'

# Open API documentation
open http://localhost:8000/docs
```

## 🚀 Production Deployment

```bash
# 1. Set production environment variables
export DATABASE_URL="postgresql://user:pass@localhost/buddyagents"
export ENVIRONMENT="production"

# 2. Run with Gunicorn for production
uv run gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🎯 Frontend Integration

This backend is designed to work with:
- **Streamlit Frontend**: For development and testing
- **React/Next.js**: For production web applications
- **Mobile Apps**: Via REST API and WebSocket connections

## 📊 Monitoring & Health

- **Health Checks**: Available at `/health`
- **System Metrics**: Database analytics and user insights
- **Logging**: Structured logging for production monitoring
- **Error Handling**: Proper HTTP status codes and error responses

## 🔐 Security

- **Environment Variables**: All sensitive data in `.env`
- **JWT Authentication**: Secure user sessions
- **CORS Configuration**: Proper cross-origin handling
- **Input Validation**: Pydantic schema validation

## 🤝 Development

```bash
# Install development dependencies
uv sync --dev

# Run with auto-reload for development
uv run uvicorn app.main:app --reload

# Check code formatting
uv run black app/
uv run isort app/
```

---

**🎉 Ready to run**: Follow the Quick Start guide above to get your BuddyAgents backend running in under 2 minutes!
