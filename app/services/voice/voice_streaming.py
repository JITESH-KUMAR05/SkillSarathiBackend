"""
Voice Streaming Service

Real-time voice communication using WebSocket connections
for low-latency audio streaming and real-time speech processing.
"""

import json
import logging
import asyncio
import base64
import time
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from datetime import datetime
import weakref

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .murf_service import MurfVoiceService
from .speech_recognition import SpeechRecognitionService
from .voice_processor import VoiceCommandProcessor, VoiceCommand
from .audio_optimizer import AudioOptimizer, AudioConfig

logger = logging.getLogger(__name__)

class StreamMessage(BaseModel):
    """WebSocket message structure"""
    type: str  # 'audio_chunk', 'text', 'command', 'status', 'error'
    data: Any
    timestamp: Optional[float] = None
    session_id: str = ""
    agent: str = "mitra"
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = time.time()
        super().__init__(**data)

class VoiceSession(BaseModel):
    """Voice streaming session"""
    session_id: str
    user_id: str
    agent: str = "mitra"
    language: str = "hi-IN"
    quality: str = "good"
    created_at: datetime
    last_activity: datetime
    is_active: bool = True
    
    # Audio settings
    audio_config: Optional[AudioConfig] = None
    
    # Session statistics
    total_audio_received: int = 0
    total_audio_sent: int = 0
    messages_processed: int = 0
    average_latency_ms: float = 0.0

class ConnectionManager:
    """Manage WebSocket connections for voice streaming"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, VoiceSession] = {}
        self.connection_handlers: Dict[str, 'VoiceStreamHandler'] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        agent: str = "mitra"
    ):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[session_id] = websocket
        
        # Create voice session
        session = VoiceSession(
            session_id=session_id,
            user_id=user_id,
            agent=agent,
            created_at=datetime.now(),
            last_activity=datetime.now()
        )
        self.sessions[session_id] = session
        
        logger.info(f"Voice session connected: {session_id} for user {user_id}")
    
    def disconnect(self, session_id: str):
        """Remove connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
        
        if session_id in self.connection_handlers:
            del self.connection_handlers[session_id]
        
        logger.info(f"Voice session disconnected: {session_id}")
    
    async def send_message(self, session_id: str, message: StreamMessage):
        """Send message to specific session"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                await websocket.send_text(message.model_dump_json())
                
                # Update session activity
                if session_id in self.sessions:
                    self.sessions[session_id].last_activity = datetime.now()
                    
            except Exception as e:
                logger.error(f"Failed to send message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_to_user(self, user_id: str, message: StreamMessage):
        """Send message to all sessions for a user"""
        user_sessions = [
            sid for sid, session in self.sessions.items()
            if session.user_id == user_id and session.is_active
        ]
        
        for session_id in user_sessions:
            await self.send_message(session_id, message)
    
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def get_active_sessions(self) -> List[VoiceSession]:
        """Get all active sessions"""
        return [session for session in self.sessions.values() if session.is_active]

class VoiceStreamHandler:
    """Handle voice streaming for a specific session"""
    
    def __init__(
        self,
        session_id: str,
        connection_manager: ConnectionManager,
        murf_service: MurfVoiceService,
        speech_service: SpeechRecognitionService,
        voice_processor: VoiceCommandProcessor,
        audio_optimizer: AudioOptimizer
    ):
        self.session_id = session_id
        self.connection_manager = connection_manager
        self.murf_service = murf_service
        self.speech_service = speech_service
        self.voice_processor = voice_processor
        self.audio_optimizer = audio_optimizer
        
        # Streaming state
        self.is_streaming = False
        self.audio_buffer = bytearray()
        self.processing_lock = asyncio.Lock()
        
        # Performance tracking
        self.start_time = time.time()
        self.last_chunk_time = time.time()
    
    async def handle_incoming_message(self, message_data: dict):
        """Process incoming WebSocket message"""
        try:
            message = StreamMessage(**message_data)
            session = self.connection_manager.get_session(self.session_id)
            
            if not session:
                logger.error(f"Session not found: {self.session_id}")
                return
            
            # Update session activity
            session.last_activity = datetime.now()
            session.messages_processed += 1
            
            # Route message based on type
            if message.type == "audio_chunk":
                await self._handle_audio_chunk(message, session)
            elif message.type == "text_input":
                await self._handle_text_input(message, session)
            elif message.type == "voice_command":
                await self._handle_voice_command(message, session)
            elif message.type == "session_config":
                await self._handle_session_config(message, session)
            elif message.type == "start_listening":
                await self._start_voice_recognition(session)
            elif message.type == "stop_listening":
                await self._stop_voice_recognition(session)
            else:
                logger.warning(f"Unknown message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(f"Message processing failed: {str(e)}")
    
    async def _handle_audio_chunk(self, message: StreamMessage, session: VoiceSession):
        """Process incoming audio chunk"""
        try:
            # Decode base64 audio data
            audio_data = base64.b64decode(message.data.get("audio", ""))
            
            if not audio_data:
                return
            
            session.total_audio_received += len(audio_data)
            
            # Add to buffer
            async with self.processing_lock:
                self.audio_buffer.extend(audio_data)
                
                # Process buffer when enough data is accumulated
                if len(self.audio_buffer) >= 8192:  # 8KB chunks
                    await self._process_audio_buffer(session)
                    
        except Exception as e:
            logger.error(f"Audio chunk processing failed: {e}")
            await self._send_error("Audio processing failed")
    
    async def _process_audio_buffer(self, session: VoiceSession):
        """Process accumulated audio buffer"""
        try:
            if not self.audio_buffer:
                return
            
            audio_data = bytes(self.audio_buffer)
            self.audio_buffer.clear()
            
            # Optimize audio for processing
            optimized_audio, _ = await self.audio_optimizer.optimize_audio(
                audio_data,
                source_format="webm",  # Common WebRTC format
                quality_preset=session.quality
            )
            
            # Transcribe audio to text
            transcription_result = None
            async for result in self.speech_service.transcribe_audio_stream(
                optimized_audio,
                language=session.language
            ):
                if result.text:
                    transcription_result = result
                    break
            
            if transcription_result and transcription_result.text:
                transcribed_text = transcription_result.text
                confidence = transcription_result.confidence
                
                # Process voice commands
                commands = await self.voice_processor.process_voice_command(
                    transcribed_text,
                    language=session.language,
                    confidence=confidence
                )
                
                # Send transcription result
                await self._send_transcription(transcribed_text, confidence, commands)
                
                # Execute commands if any
                for command in commands:
                    await self._execute_voice_command(command, session)
                    
        except Exception as e:
            logger.error(f"Audio buffer processing failed: {e}")
    
    async def _handle_text_input(self, message: StreamMessage, session: VoiceSession):
        """Process text input for TTS generation"""
        try:
            text = message.data.get("text", "")
            if not text:
                return
            
            # Generate speech from text
            audio_response = await self.murf_service.generate_speech(
                text=text,
                agent=session.agent
            )
            
            if audio_response:
                # Optimize audio for streaming
                optimized_audio, metrics = await self.audio_optimizer.optimize_audio(
                    audio_response,
                    quality_preset=session.quality
                )
                
                session.total_audio_sent += len(optimized_audio)
                
                # Send audio chunks for streaming
                await self._send_audio_stream(optimized_audio, session)
                
        except Exception as e:
            logger.error(f"Text input processing failed: {e}")
            await self._send_error("Text-to-speech generation failed")
    
    async def _handle_voice_command(self, message: StreamMessage, session: VoiceSession):
        """Process voice command directly"""
        try:
            command_data = message.data
            command = VoiceCommand(**command_data)
            
            await self._execute_voice_command(command, session)
            
        except Exception as e:
            logger.error(f"Voice command processing failed: {e}")
            await self._send_error("Voice command execution failed")
    
    async def _handle_session_config(self, message: StreamMessage, session: VoiceSession):
        """Update session configuration"""
        try:
            config = message.data
            
            # Update session settings
            if "agent" in config:
                session.agent = config["agent"]
            if "language" in config:
                session.language = config["language"]
            if "quality" in config:
                session.quality = config["quality"]
            
            # Update audio configuration
            if "audio_config" in config:
                session.audio_config = AudioConfig(**config["audio_config"])
            
            # Send confirmation
            await self._send_status("Session configuration updated")
            
        except Exception as e:
            logger.error(f"Session config update failed: {e}")
            await self._send_error("Configuration update failed")
    
    async def _execute_voice_command(self, command: VoiceCommand, session: VoiceSession):
        """Execute a voice command"""
        try:
            if command.command_type == "agent_switch" and command.target_agent:
                # Switch agent
                old_agent = session.agent
                session.agent = command.target_agent
                
                # Generate confirmation message
                confirmation_text = f"Switching from {old_agent} to {command.target_agent}"
                
                # Generate welcome message from new agent
                welcome_messages = {
                    "mitra": "नमस्ते! मैं मित्र हूं। आज आप कैसा महसूस कर रहे हैं?",
                    "guru": "नमस्ते! मैं गुरु हूं। आज आप क्या सीखना चाहते हैं?",
                    "parikshak": "नमस्ते! मैं परीक्षक हूं। Interview practice के लिए तैयार हैं?"
                }
                
                welcome_text = welcome_messages.get(command.target_agent, "Hello!")
                
                # Generate speech for welcome message
                audio_response = await self.murf_service.generate_speech(
                    text=welcome_text,
                    agent=session.agent
                )
                
                if audio_response:
                    await self._send_audio_stream(audio_response, session)
                
                # Send agent switch notification
                await self._send_status(f"Switched to {command.target_agent}")
                
            elif command.command_type == "action":
                # Handle action commands
                await self._send_status(f"Executing action: {command.action}")
                
            elif command.command_type == "question":
                # Handle questions
                await self._send_status("Processing your question...")
                
            elif command.command_type == "greeting":
                # Handle greetings
                greetings = {
                    "mitra": "नमस्ते! मैं आपकी सहायता करने के लिए यहाँ हूँ।",
                    "guru": "नमस्ते! आज हम क्या सीखेंगे?", 
                    "parikshak": "नमस्ते! Interview की तैयारी करते हैं।"
                }
                
                response_text = greetings.get(session.agent, "नमस्ते!")
                
                # Generate speech response
                audio_response = await self.murf_service.generate_speech(
                    text=response_text,
                    agent=session.agent
                )
                
                if audio_response:
                    await self._send_audio_stream(audio_response, session)
                    
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            await self._send_error("Command execution failed")
    
    async def _send_audio_stream(self, audio_data: bytes, session: VoiceSession):
        """Send audio data as streaming chunks"""
        try:
            # Create audio chunks for streaming
            chunks = await self.audio_optimizer.create_audio_chunks(
                audio_data,
                chunk_duration_ms=500  # 500ms chunks for smooth streaming
            )
            
            for i, chunk in enumerate(chunks):
                # Encode chunk as base64
                encoded_chunk = base64.b64encode(chunk).decode('utf-8')
                
                # Send chunk
                message = StreamMessage(
                    type="audio_chunk",
                    data={
                        "audio": encoded_chunk,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "format": session.audio_config.format if session.audio_config else "mp3"
                    },
                    session_id=self.session_id,
                    agent=session.agent
                )
                
                await self.connection_manager.send_message(self.session_id, message)
                
                # Small delay between chunks for smooth streaming
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Audio streaming failed: {e}")
    
    async def _start_voice_recognition(self, session: VoiceSession):
        """Start continuous voice recognition"""
        try:
            self.is_streaming = True
            
            await self._send_status("Voice recognition started")
            
        except Exception as e:
            logger.error(f"Failed to start voice recognition: {e}")
            await self._send_error("Could not start voice recognition")
    
    async def _stop_voice_recognition(self, session: VoiceSession):
        """Stop voice recognition"""
        try:
            self.is_streaming = False
            
            # Process any remaining audio in buffer
            if self.audio_buffer:
                await self._process_audio_buffer(session)
            
            await self._send_status("Voice recognition stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop voice recognition: {e}")
    
    async def _send_transcription(
        self,
        text: str,
        confidence: float,
        commands: List[VoiceCommand]
    ):
        """Send transcription result"""
        message = StreamMessage(
            type="transcription",
            data={
                "text": text,
                "confidence": confidence,
                "commands": [cmd.model_dump() for cmd in commands]
            },
            session_id=self.session_id
        )
        
        await self.connection_manager.send_message(self.session_id, message)
    
    async def _send_status(self, status: str):
        """Send status message"""
        message = StreamMessage(
            type="status",
            data={"message": status},
            session_id=self.session_id
        )
        
        await self.connection_manager.send_message(self.session_id, message)
    
    async def _send_error(self, error: str):
        """Send error message"""
        message = StreamMessage(
            type="error",
            data={"error": error},
            session_id=self.session_id
        )
        
        await self.connection_manager.send_message(self.session_id, message)

class VoiceStreamingService:
    """
    Main voice streaming service
    """
    
    def __init__(
        self,
        murf_service: MurfVoiceService,
        speech_service: SpeechRecognitionService,
        voice_processor: VoiceCommandProcessor,
        audio_optimizer: AudioOptimizer
    ):
        self.murf_service = murf_service
        self.speech_service = speech_service
        self.voice_processor = voice_processor
        self.audio_optimizer = audio_optimizer
        
        self.connection_manager = ConnectionManager()
        
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_inactive_sessions():
            while True:
                try:
                    current_time = datetime.now()
                    inactive_sessions = []
                    
                    for session_id, session in self.connection_manager.sessions.items():
                        # Clean up sessions inactive for more than 30 minutes
                        if (current_time - session.last_activity).total_seconds() > 1800:
                            inactive_sessions.append(session_id)
                    
                    for session_id in inactive_sessions:
                        self.connection_manager.disconnect(session_id)
                        logger.info(f"Cleaned up inactive session: {session_id}")
                    
                    await asyncio.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
                    await asyncio.sleep(60)
        
        self._cleanup_task = asyncio.create_task(cleanup_inactive_sessions())
    
    async def handle_websocket_connection(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        agent: str = "mitra"
    ):
        """Handle WebSocket connection for voice streaming"""
        
        # Connect to session
        await self.connection_manager.connect(websocket, session_id, user_id, agent)
        
        # Create handler for this session
        handler = VoiceStreamHandler(
            session_id=session_id,
            connection_manager=self.connection_manager,
            murf_service=self.murf_service,
            speech_service=self.speech_service,
            voice_processor=self.voice_processor,
            audio_optimizer=self.audio_optimizer
        )
        
        self.connection_manager.connection_handlers[session_id] = handler
        
        try:
            # Send welcome message
            welcome_message = StreamMessage(
                type="status",
                data={"message": f"Connected to {agent} voice session"},
                session_id=session_id,
                agent=agent
            )
            await self.connection_manager.send_message(session_id, welcome_message)
            
            # Handle messages
            while True:
                try:
                    # Receive message from WebSocket
                    raw_message = await websocket.receive_text()
                    message_data = json.loads(raw_message)
                    
                    # Process message
                    await handler.handle_incoming_message(message_data)
                    
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {session_id}")
                    break
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.connection_manager.disconnect(session_id)
    
    async def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session statistics"""
        session = self.connection_manager.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "agent": session.agent,
            "language": session.language,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "is_active": session.is_active,
            "total_audio_received": session.total_audio_received,
            "total_audio_sent": session.total_audio_sent,
            "messages_processed": session.messages_processed,
            "average_latency_ms": session.average_latency_ms
        }
    
    async def shutdown(self):
        """Shutdown the streaming service"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        # Disconnect all active sessions
        for session_id in list(self.connection_manager.active_connections.keys()):
            self.connection_manager.disconnect(session_id)