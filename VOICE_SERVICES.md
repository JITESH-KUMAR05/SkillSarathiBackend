# Voice Services Documentation

## Overview

The BuddyAgents Voice Services provide comprehensive text-to-speech (TTS), speech-to-text (STT), and real-time voice streaming capabilities with support for Hindi and English languages. The system is designed for production use with advanced caching, optimization, and multi-provider support.

## Architecture

### Core Components

1. **MurfVoiceService** - Murf AI integration for high-quality TTS
2. **SpeechRecognitionService** - Azure/Google Cloud STT with streaming support
3. **VoiceCommandProcessor** - Natural language processing for voice commands
4. **AudioOptimizer** - Audio format conversion and quality optimization
5. **VoiceCache** - Redis-based intelligent caching system
6. **VoiceStreamingService** - Real-time WebSocket voice communication

### Agent Voice Mapping

- **Mitra** (Emotional Support): Aditi (Primary), Priya (Backup)
- **Guru** (Learning Assistant): Arnav (Primary), Kabir (Backup)  
- **Parikshak** (Interview Coach): Alisha (Primary), Radhika (Backup)

## Installation

### 1. Install Dependencies

```bash
pip install -r voice_requirements.txt
```

### 2. System Dependencies (Ubuntu/Debian)

```bash
# FFmpeg for audio processing
sudo apt update
sudo apt install ffmpeg

# For audio development (optional)
sudo apt install portaudio19-dev python3-pyaudio
```

### 3. Environment Configuration

Copy the environment variables from `voice_env_example.txt` to your `.env` file:

```bash
cp voice_env_example.txt .env
# Edit .env with your API keys and configuration
```

### 4. Required API Keys

- **Murf AI**: Sign up at https://murf.ai/ for TTS services
- **Azure Speech**: Get from Azure Cognitive Services
- **Google Cloud Speech**: Optional, for backup STT provider

## API Endpoints

### Text-to-Speech

#### Generate Speech
```http
POST /api/v1/voice/tts
Content-Type: application/json

{
  "text": "नमस्ते! आज आप कैसे हैं?",
  "agent": "mitra",
  "language": "hi-IN",
  "quality": "good",
  "format": "mp3"
}
```

#### Streaming Speech
```http
POST /api/v1/voice/tts/stream
Content-Type: application/json

{
  "text": "Long text for streaming...",
  "agent": "guru",
  "streaming": true
}
```

### Speech-to-Text

#### Upload Audio File
```http
POST /api/v1/voice/stt
Content-Type: multipart/form-data

audio_file: [audio file]
language: hi-IN
enable_commands: true
```

### Voice Commands

#### Process Voice Command
```http
POST /api/v1/voice/commands
Content-Type: application/json

{
  "text": "मित्र से बात करना चाहता हूं",
  "language": "hi-IN",
  "confidence": 0.95,
  "agent_context": "guru"
}
```

### Real-time Voice Streaming

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/voice/stream/session123?agent=mitra');

// Send audio chunk
ws.send(JSON.stringify({
  type: 'audio_chunk',
  data: {
    audio: base64AudioData
  }
}));

// Send text for TTS
ws.send(JSON.stringify({
  type: 'text_input',
  data: {
    text: 'Hello, how are you today?'
  }
}));
```

### Health and Status

#### Service Health
```http
GET /api/v1/voice/health
```

#### Available Voices
```http
GET /api/v1/voice/voices
```

#### Cache Statistics
```http
GET /api/v1/voice/cache/stats
```

## Voice Command Processing

### Supported Command Types

1. **Agent Switch Commands**
   - Hindi: "मित्र से बात करो", "गुरु से मदद चाहिए"
   - English: "Talk to Mitra", "Switch to Guru"

2. **Action Commands**
   - Learning: "मुझे कुछ सीखना है", "Explain this concept"
   - Interview: "Interview practice शुरू करो", "Check my resume"
   - Emotional: "मुझे दुख हो रहा है", "I'm feeling happy"

3. **Questions**
   - "क्या है...", "What is...", "कैसे करते हैं...", "How to..."

4. **Greetings**
   - "नमस्ते", "Hello", "Good morning"

### Command Processing Pipeline

1. **Speech Recognition** - Convert audio to text
2. **Language Detection** - Identify Hindi/English
3. **Intent Classification** - Determine command type
4. **Entity Extraction** - Extract parameters
5. **Validation** - Verify command validity
6. **Response Generation** - Create appropriate response

## Audio Optimization

### Quality Presets

- **Low** (64kbps): Mobile networks, bandwidth-constrained
- **Good** (128kbps): Standard quality, balanced performance
- **High** (192kbps): High quality for important content
- **Premium** (320kbps/WAV): Maximum quality, lossless

### Format Support

- **MP3**: Standard web audio, good compression
- **WAV**: Lossless quality, larger files
- **OGG**: Open source, efficient compression
- **M4A**: Apple ecosystem, good quality

### Speech Optimization Features

- Noise reduction and filtering
- Volume normalization
- Dynamic range compression
- Speech-specific frequency enhancement
- Silence trimming

## Caching Strategy

### Redis Caching

- **Key Structure**: `voice:tts:{agent}:{text_hash}:{language}`
- **TTL**: 24 hours (configurable)
- **Compression**: GZIP for large audio files
- **Invalidation**: LRU with manual cleanup

### Cache Performance

- **Hit Rate**: Typically 60-80% for common phrases
- **Latency Reduction**: 90%+ for cached content
- **Storage Efficiency**: ~70% compression ratio

### Preloading

Common phrases and greetings are preloaded for each agent:
- Welcome messages
- Common responses
- Error messages
- Help text

## Performance Optimization

### Concurrent Processing

- Maximum 10 concurrent TTS requests
- Request queuing with priority
- Automatic retry with exponential backoff

### Streaming Optimization

- 500ms audio chunks for smooth playback
- Buffer management for continuous streaming
- Adaptive quality based on bandwidth

### Latency Targets

- **TTS Generation**: <2 seconds
- **STT Processing**: <1 second  
- **Voice Commands**: <500ms
- **Cache Retrieval**: <100ms

## Security Considerations

### Authentication

All endpoints require valid JWT tokens except health checks.

### Rate Limiting

- TTS: 100 requests/hour per user
- STT: 200 requests/hour per user
- Streaming: 5 concurrent sessions per user

### Data Privacy

- Audio data is not permanently stored
- Transcriptions are processed in memory only
- Cache data is encrypted and expires automatically

### API Key Security

- Environment variables only
- Rotation support
- Service-specific keys with minimal permissions

## Monitoring and Logging

### Health Metrics

- Service availability
- Response times
- Error rates
- Cache hit ratios
- Active WebSocket connections

### Logging Levels

- **DEBUG**: Detailed processing information
- **INFO**: Normal operations and statistics
- **WARNING**: Recoverable errors and degraded performance
- **ERROR**: Service failures and critical issues

### Alerting

Configure alerts for:
- Service downtime > 1 minute
- Error rate > 5%
- Cache hit rate < 30%
- Response time > 5 seconds

## Troubleshooting

### Common Issues

1. **Murf API Failures**
   - Check API key validity
   - Verify account quota
   - Review request formatting

2. **Audio Quality Issues**
   - Adjust quality presets
   - Check format compatibility
   - Verify optimization settings

3. **STT Accuracy Problems**
   - Ensure clean audio input
   - Check language settings
   - Verify microphone quality

4. **Streaming Interruptions**
   - Check network stability
   - Monitor WebSocket connections
   - Review buffer settings

### Debug Commands

```bash
# Test voice service health
curl http://localhost:8000/api/v1/voice/health

# Check cache statistics
curl -H "Authorization: Bearer $JWT_TOKEN" \
     http://localhost:8000/api/v1/voice/cache/stats

# Test TTS generation
curl -X POST http://localhost:8000/api/v1/voice/tts \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -d '{"text": "Test message", "agent": "mitra"}'
```

## Development Setup

### Local Development

1. Install Redis locally or use Docker:
```bash
docker run -d -p 6379:6379 redis:alpine
```

2. Set development environment variables:
```bash
export VOICE_CACHE_ENABLED=true
export DEFAULT_AUDIO_QUALITY=good
export VOICE_LOG_LEVEL=DEBUG
```

3. Run with hot reload:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Unit tests
pytest tests/test_voice_services.py -v

# Integration tests
pytest tests/test_voice_integration.py -v

# Load testing
python tests/load_test_voice.py
```

## Production Deployment

### Environment Checklist

- [ ] All API keys configured
- [ ] Redis instance running
- [ ] SSL certificates installed
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Log aggregation setup

### Scaling Considerations

- **Horizontal Scaling**: Multiple FastAPI instances behind load balancer
- **Redis Clustering**: For high-availability caching
- **CDN Integration**: For static audio content delivery
- **Queue System**: For background audio processing

### Performance Tuning

```python
# Production settings
VOICE_CACHE_TTL_HOURS=48
MAX_VOICE_REQUESTS=50
VOICE_REQUEST_TIMEOUT=15
REDIS_CONNECTION_POOL_SIZE=20
```

## API Reference

Complete API documentation is available at `/docs` when running in development mode.

### WebSocket Message Types

#### Client to Server
- `audio_chunk`: Raw audio data for STT
- `text_input`: Text for TTS generation
- `voice_command`: Direct command processing
- `session_config`: Update session settings
- `start_listening`: Begin voice recognition
- `stop_listening`: End voice recognition

#### Server to Client
- `audio_chunk`: Generated speech audio
- `transcription`: STT results with commands
- `status`: Session status updates
- `error`: Error messages
- `agent_switch`: Agent change notifications

## Changelog

### Version 2.0.0
- Initial comprehensive voice services implementation
- Murf AI integration with Indian voices
- Multi-provider speech recognition
- Real-time WebSocket streaming
- Advanced caching and optimization
- Production-ready error handling

For technical support or feature requests, please create an issue in the project repository.