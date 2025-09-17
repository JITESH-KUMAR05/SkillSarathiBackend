# 🤖 BuddyAgents Streamlit Frontend

A next-generation multi-agent companion system with voice integration, video interviews, and AI-powered assistance for emotional support, learning, and career development.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv package manager](https://github.com/astral-sh/uv)
- Backend server running on `localhost:8000`

### Installation

1. **Install Frontend Dependencies**
   ```bash
   cd streamlit_app
   ./install.sh
   ```

2. **Configure Environment**
   ```bash
   # Edit .env file with your API keys
   nano .env
   ```

3. **Start the Application**
   ```bash
   # Start backend (from parent directory)
   cd .. && uv run main.py
   
   # Start frontend (in new terminal)
   cd streamlit_app && uv run streamlit run app.py
   ```

4. **Access the Application**
   - Frontend: [http://localhost:8501](http://localhost:8501)
   - Backend API: [http://localhost:8000](http://localhost:8000)

## 🤗 Meet Your AI Agents

### 🤗 Mitra - Emotional Support Agent
- **Purpose**: Mental wellness and emotional support
- **Features**: 
  - Mood tracking and analysis
  - Empathetic conversations
  - Wellness recommendations
  - Crisis support resources
  - Voice-enabled emotional check-ins


### 🎓 Guru - Learning Mentor Agent  
- **Purpose**: Educational guidance and skill development
- **Features**:
  - Personalized learning paths
  - Document analysis and Q&A
  - Interactive quizzes and assessments
  - Goal setting and progress tracking
  - Multi-language learning support

### 💼 Parikshak - Interview Coach Agent
- **Purpose**: Career development and interview preparation
- **Features**:
  - Live video interview simulation
  - Real-time performance analysis
  - Mock interview generation
  - Body language and eye contact tracking
  - Industry-specific question banks
  - Screen sharing for technical interviews

## 🎥 Video Interview Features

The Parikshak agent includes advanced video capabilities:

- **Real-time Face Detection**: Tracks candidate presence
- **Eye Contact Analysis**: Measures engagement levels
- **Integrity Monitoring**: Detects multiple faces or suspicious behavior
- **Performance Metrics**: Comprehensive scoring system
- **Screen Sharing**: For technical coding interviews (coming soon)

## 🔊 Voice Integration

All agents support Murf AI voice synthesis with 21 Indian voices:

### Hindi Voices (6)
- Aditi (Female, Young Adult)
- Kabir (Male, Young Adult)  
- Neerja (Female, Middle Aged)
- Radhika (Female, Young Adult)
- Saanvi (Female, Young Adult)
- Tarun (Male, Young Adult)

### English-India Voices (7)
- Alisha (Female, Young Adult)
- Arnav (Male, Young Adult)
- Kavya (Female, Young Adult)
- Priya (Female, Young Adult)
- Rahul (Male, Young Adult)
- Ravi (Male, Middle Aged)
- Sneha (Female, Young Adult)

### Bengali & Tamil Voices (8)
- Bengali: Aarohi, Agni, Anwesha, Binita
- Tamil: Dharini, Rajan, Shruthi, Valluvar

## 📁 Project Structure

```
streamlit_app/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Dependencies
├── install.sh               # Installation script
├── .env                     # Environment configuration
├── utils/
│   ├── config.py            # App configuration
│   ├── api_client.py        # Backend communication
│   ├── session.py           # Session management
│   └── audio.py             # Audio processing
├── pages/
│   ├── 1_🤗_Mitra.py       # Emotional support agent
│   ├── 2_🎓_Guru.py        # Learning mentor agent
│   └── 3_💼_Parikshak.py   # Interview coach agent
└── components/
    └── video.py             # Video processing components
```

## 🛠️ Technical Features

### Frontend Architecture
- **Streamlit**: Modern web interface
- **WebRTC**: Real-time video communication
- **OpenCV**: Computer vision processing
- **Session Management**: Persistent user state
- **Modular Design**: Scalable component system

### Backend Integration
- **FastAPI**: High-performance API server
- **WebSocket**: Real-time communication
- **SQLite**: Local database storage
- **Murf AI**: Voice synthesis
- **Multi-agent System**: Specialized AI assistants

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Backend Connection
BACKEND_URL=http://localhost:8000
WEBSOCKET_URL=ws://localhost:8000

# Murf AI Voice
MURF_API_KEY=your_murf_api_key
MURF_API_URL=https://api.murf.ai/v1

# Application Settings
DEBUG=true
API_TIMEOUT=30
STUN_SERVER=stun:stun.l.google.com:19302
```

## 🚀 Deployment

### Local Development
```bash
# Backend
cd backend && uv run main.py

# Frontend  
cd streamlit_app && uv run streamlit run app.py
```

### Production Deployment
```bash
# Backend with Gunicorn
cd backend && uv run gunicorn -w 4 -k uvicorn.workers.UnicornWorker app.main:app

# Frontend with custom port
cd streamlit_app && uv run streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## 🎯 Usage Examples

### 1. Emotional Support Session
1. Select **🤗 Mitra** from sidebar
2. Choose your current mood
3. Start voice or text conversation
4. Receive personalized wellness advice

### 2. Learning Session
1. Select **🎓 Guru** from sidebar
2. Upload documents or set learning goals
3. Take interactive quizzes
4. Track your progress

### 3. Interview Preparation
1. Select **💼 Parikshak** from sidebar
2. Choose interview type (behavioral/technical)
3. Start video interview simulation
4. Receive real-time feedback and scoring

## 🔍 Troubleshooting

### Common Issues

**Video not working**:
```bash
# Install video dependencies
uv add streamlit-webrtc opencv-python aiortc
```

**Backend connection failed**:
- Ensure backend is running on `localhost:8000`
- Check `.env` file configuration
- Verify firewall settings

**Audio issues**:
- Check microphone permissions
- Verify Murf API key in `.env`
- Test browser audio settings

## 📚 API Documentation

Backend API documentation available at: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes following code style
4. Test thoroughly with all agents
5. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review API documentation
- Open an issue on GitHub
