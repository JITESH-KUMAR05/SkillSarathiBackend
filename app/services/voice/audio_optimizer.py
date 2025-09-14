"""
Audio Optimization Service

Handles audio format conversion, compression, quality optimization,
and streaming audio processing for voice services.
"""

import io
import logging
import asyncio
import hashlib
from typing import Optional, Dict, Any, Union, BinaryIO
from pydantic import BaseModel
from datetime import datetime
import json

# Audio processing libraries
try:
    import pydub
    from pydub import AudioSegment
    from pydub.utils import make_chunks
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logging.warning("pydub not available - audio optimization will be limited")
    
    # Create dummy classes for type hints when pydub is not available
    class AudioSegment:
        def __init__(self, *args, **kwargs):
            pass
        
        def __len__(self):
            return 0
        
        def __getitem__(self, key):
            return self
        
        @property
        def frame_rate(self):
            return 22050
        
        @property
        def channels(self):
            return 1
        
        @property
        def dBFS(self):
            return -20.0
        
        def set_frame_rate(self, rate):
            return self
        
        def set_channels(self, channels):
            return self
        
        def apply_gain(self, gain):
            return self
        
        def compress_dynamic_range(self, **kwargs):
            return self
        
        def export(self, *args, **kwargs):
            pass
            
        @classmethod
        def from_file(cls, *args, **kwargs):
            return cls()
    
    def make_chunks(audio, chunk_size):
        return [audio]

try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logging.warning("librosa not available - advanced audio processing disabled")

logger = logging.getLogger(__name__)

class AudioConfig(BaseModel):
    """Audio configuration parameters"""
    format: str = "mp3"  # mp3, wav, ogg, m4a
    bitrate: str = "128k"  # Audio bitrate
    sample_rate: int = 22050  # Sample rate in Hz
    channels: int = 1  # Mono/Stereo
    quality: str = "good"  # low, good, high, premium
    normalize: bool = True  # Normalize audio levels
    compress: bool = True  # Apply compression
    optimize_for_speech: bool = True  # Speech-specific optimizations

class AudioMetrics(BaseModel):
    """Audio quality metrics"""
    duration_ms: int = 0
    file_size_bytes: int = 0
    sample_rate: int = 0
    channels: int = 0
    bitrate: int = 0
    format: str = ""
    quality_score: float = 0.0  # 0-1 quality score
    speech_clarity: float = 0.0  # Speech clarity score
    noise_level: float = 0.0  # Background noise level

class AudioOptimizer:
    """
    Audio processing and optimization service
    """
    
    def __init__(self):
        self.quality_presets = self._initialize_quality_presets()
        self.format_configs = self._initialize_format_configs()
        
    def _initialize_quality_presets(self) -> Dict[str, AudioConfig]:
        """Initialize quality preset configurations"""
        return {
            "low": AudioConfig(
                format="mp3",
                bitrate="64k",
                sample_rate=16000,
                channels=1,
                quality="low",
                normalize=True,
                compress=True
            ),
            "good": AudioConfig(
                format="mp3", 
                bitrate="128k",
                sample_rate=22050,
                channels=1,
                quality="good",
                normalize=True,
                compress=True
            ),
            "high": AudioConfig(
                format="mp3",
                bitrate="192k", 
                sample_rate=44100,
                channels=1,
                quality="high",
                normalize=True,
                compress=False
            ),
            "premium": AudioConfig(
                format="wav",
                bitrate="320k",
                sample_rate=48000,
                channels=2,
                quality="premium",
                normalize=False,
                compress=False
            )
        }
    
    def _initialize_format_configs(self) -> Dict[str, Dict[str, Any]]:
        """Initialize format-specific configurations"""
        return {
            "mp3": {
                "mime_type": "audio/mpeg",
                "extension": ".mp3",
                "streaming_friendly": True,
                "compression_ratio": 0.1,
                "quality_loss": "lossy"
            },
            "wav": {
                "mime_type": "audio/wav",
                "extension": ".wav", 
                "streaming_friendly": False,
                "compression_ratio": 1.0,
                "quality_loss": "lossless"
            },
            "ogg": {
                "mime_type": "audio/ogg",
                "extension": ".ogg",
                "streaming_friendly": True,
                "compression_ratio": 0.08,
                "quality_loss": "lossy"
            },
            "m4a": {
                "mime_type": "audio/mp4",
                "extension": ".m4a",
                "streaming_friendly": True,
                "compression_ratio": 0.12,
                "quality_loss": "lossy"
            }
        }
    
    async def optimize_audio(
        self,
        audio_data: bytes,
        source_format: str = "mp3",
        target_config: Optional[AudioConfig] = None,
        quality_preset: str = "good"
    ) -> tuple[bytes, AudioMetrics]:
        """
        Optimize audio data for voice applications
        
        Args:
            audio_data: Raw audio data
            source_format: Source audio format
            target_config: Target configuration
            quality_preset: Quality preset to use
            
        Returns:
            Tuple of optimized audio data and metrics
        """
        if not PYDUB_AVAILABLE:
            logger.warning("Audio optimization disabled - returning original data")
            return audio_data, AudioMetrics()
        
        try:
            # Use preset if no specific config provided
            if target_config is None:
                target_config = self.quality_presets.get(quality_preset, self.quality_presets["good"])
            
            # Load audio data
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=source_format
            )
            
            # Apply optimizations
            optimized_audio = await self._apply_optimizations(audio_segment, target_config)
            
            # Export optimized audio
            output_buffer = io.BytesIO()
            optimized_audio.export(
                output_buffer,
                format=target_config.format,
                bitrate=target_config.bitrate,
                parameters=["-ar", str(target_config.sample_rate)]
            )
            
            optimized_data = output_buffer.getvalue()
            
            # Calculate metrics
            metrics = await self._calculate_audio_metrics(
                optimized_audio,
                optimized_data,
                target_config
            )
            
            logger.debug(f"Audio optimized: {len(audio_data)} -> {len(optimized_data)} bytes")
            return optimized_data, metrics
            
        except Exception as e:
            logger.error(f"Audio optimization failed: {e}")
            return audio_data, AudioMetrics()
    
    async def _apply_optimizations(
        self,
        audio: AudioSegment,
        config: AudioConfig
    ) -> AudioSegment:
        """Apply audio optimizations based on configuration"""
        
        optimized = audio
        
        try:
            # Resample if needed
            if optimized.frame_rate != config.sample_rate:
                optimized = optimized.set_frame_rate(config.sample_rate)
            
            # Set channels (mono/stereo)
            if optimized.channels != config.channels:
                if config.channels == 1:
                    optimized = optimized.set_channels(1)
                else:
                    optimized = optimized.set_channels(2)
            
            # Speech optimization
            if config.optimize_for_speech:
                optimized = await self._optimize_for_speech(optimized)
            
            # Normalize audio levels
            if config.normalize:
                optimized = await self._normalize_audio(optimized)
            
            # Apply compression
            if config.compress:
                optimized = await self._apply_compression(optimized)
            
            # Quality-specific processing
            if config.quality == "premium":
                optimized = await self._apply_premium_processing(optimized)
            
            return optimized
            
        except Exception as e:
            logger.error(f"Optimization processing failed: {e}")
            return audio
    
    async def _optimize_for_speech(self, audio: AudioSegment) -> AudioSegment:
        """Apply speech-specific optimizations"""
        try:
            # High-pass filter to remove low-frequency noise
            # This is a simple implementation - in production, use more sophisticated filtering
            
            # Enhance vocal frequencies (300-3400 Hz)
            # For now, we'll just ensure good sample rate
            if audio.frame_rate < 16000:
                audio = audio.set_frame_rate(16000)
            
            # Remove silence at start/end
            audio = self._trim_silence(audio)
            
            return audio
            
        except Exception as e:
            logger.error(f"Speech optimization failed: {e}")
            return audio
    
    def _trim_silence(self, audio: AudioSegment, silence_thresh: int = -40) -> AudioSegment:
        """Trim silence from start and end of audio"""
        try:
            # Find non-silent parts
            non_silent_ranges = pydub.silence.detect_nonsilent(
                audio,
                min_silence_len=100,  # 100ms minimum silence
                silence_thresh=silence_thresh
            )
            
            if non_silent_ranges:
                start = non_silent_ranges[0][0]
                end = non_silent_ranges[-1][1]
                return audio[start:end]
            
            return audio
            
        except Exception as e:
            logger.error(f"Silence trimming failed: {e}")
            return audio
    
    async def _normalize_audio(self, audio: AudioSegment) -> AudioSegment:
        """Normalize audio levels"""
        try:
            # Simple normalization - bring to target dBFS
            target_dBFS = -20.0  # Target level
            change_in_dBFS = target_dBFS - audio.dBFS
            return audio.apply_gain(change_in_dBFS)
            
        except Exception as e:
            logger.error(f"Audio normalization failed: {e}")
            return audio
    
    async def _apply_compression(self, audio: AudioSegment) -> AudioSegment:
        """Apply dynamic range compression"""
        try:
            # Simple compression using gain adjustment
            # In production, use more sophisticated compression algorithms
            
            # Compress loud parts
            compressed = audio.compress_dynamic_range(
                threshold=-25.0,  # dBFS threshold
                ratio=4.0,        # 4:1 compression ratio
                attack=5.0,       # 5ms attack
                release=50.0      # 50ms release
            )
            
            return compressed
            
        except Exception as e:
            logger.error(f"Audio compression failed: {e}")
            return audio
    
    async def _apply_premium_processing(self, audio: AudioSegment) -> AudioSegment:
        """Apply premium quality processing"""
        try:
            # Premium processing for highest quality
            # This could include advanced filtering, noise reduction, etc.
            
            # For now, ensure no additional processing that might degrade quality
            return audio
            
        except Exception as e:
            logger.error(f"Premium processing failed: {e}")
            return audio
    
    async def _calculate_audio_metrics(
        self,
        audio: AudioSegment,
        audio_data: bytes,
        config: AudioConfig
    ) -> AudioMetrics:
        """Calculate audio quality metrics"""
        try:
            metrics = AudioMetrics(
                duration_ms=len(audio),
                file_size_bytes=len(audio_data),
                sample_rate=audio.frame_rate,
                channels=audio.channels,
                bitrate=int(config.bitrate.replace('k', '')) * 1000,
                format=config.format,
                quality_score=self._calculate_quality_score(audio, config),
                speech_clarity=self._calculate_speech_clarity(audio),
                noise_level=self._calculate_noise_level(audio)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Metrics calculation failed: {e}")
            return AudioMetrics()
    
    def _calculate_quality_score(self, audio: AudioSegment, config: AudioConfig) -> float:
        """Calculate overall quality score (0-1)"""
        try:
            score = 0.5  # Base score
            
            # Sample rate contribution
            if audio.frame_rate >= 22050:
                score += 0.2
            elif audio.frame_rate >= 16000:
                score += 0.1
            
            # Bitrate contribution  
            bitrate = int(config.bitrate.replace('k', ''))
            if bitrate >= 192:
                score += 0.2
            elif bitrate >= 128:
                score += 0.15
            elif bitrate >= 64:
                score += 0.1
            
            # Format contribution
            if config.format == "wav":
                score += 0.1
            elif config.format in ["mp3", "m4a"]:
                score += 0.05
            
            return min(1.0, score)
            
        except Exception:
            return 0.5
    
    def _calculate_speech_clarity(self, audio: AudioSegment) -> float:
        """Calculate speech clarity score"""
        try:
            # Simple clarity metric based on frequency content
            # In production, use more sophisticated speech analysis
            
            # Check if sample rate is good for speech
            if audio.frame_rate >= 16000:
                clarity = 0.8
            else:
                clarity = 0.5
            
            # Check dynamic range
            if audio.dBFS > -30:  # Good level
                clarity += 0.2
            
            return min(1.0, clarity)
            
        except Exception:
            return 0.5
    
    def _calculate_noise_level(self, audio: AudioSegment) -> float:
        """Calculate background noise level"""
        try:
            # Simple noise level estimation
            # Find quietest part of audio as noise floor estimation
            
            # Split into chunks and find minimum RMS
            chunk_length = 1000  # 1 second chunks
            chunks = make_chunks(audio, chunk_length)
            
            if chunks:
                min_rms = min(chunk.rms for chunk in chunks if len(chunk) > 0)
                # Convert to 0-1 scale (lower is better)
                noise_level = max(0, min(1, (min_rms + 60) / 60))  # Normalize around -60dB
                return noise_level
            
            return 0.5
            
        except Exception:
            return 0.5
    
    async def convert_format(
        self,
        audio_data: bytes,
        source_format: str,
        target_format: str,
        quality: str = "good"
    ) -> bytes:
        """
        Convert audio between formats
        
        Args:
            audio_data: Source audio data
            source_format: Source format
            target_format: Target format
            quality: Quality preset
            
        Returns:
            Converted audio data
        """
        if not PYDUB_AVAILABLE:
            logger.warning("Format conversion disabled - returning original data")
            return audio_data
        
        try:
            # Load source audio
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=source_format
            )
            
            # Get target configuration
            config = self.quality_presets.get(quality, self.quality_presets["good"])
            config.format = target_format
            
            # Apply basic optimizations for target format
            if target_format in self.format_configs:
                format_config = self.format_configs[target_format]
                
                # Optimize for streaming if format supports it
                if format_config["streaming_friendly"] and config.compress:
                    audio = await self._apply_compression(audio)
            
            # Export in target format
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format=target_format)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Format conversion failed: {e}")
            return audio_data
    
    async def create_audio_chunks(
        self,
        audio_data: bytes,
        chunk_duration_ms: int = 1000,
        source_format: str = "mp3"
    ) -> list[bytes]:
        """
        Split audio into chunks for streaming
        
        Args:
            audio_data: Audio data to chunk
            chunk_duration_ms: Chunk duration in milliseconds
            source_format: Source audio format
            
        Returns:
            List of audio chunks
        """
        if not PYDUB_AVAILABLE:
            logger.warning("Audio chunking disabled")
            return [audio_data]
        
        try:
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=source_format
            )
            
            chunks = make_chunks(audio, chunk_duration_ms)
            
            chunk_data = []
            for chunk in chunks:
                output_buffer = io.BytesIO()
                chunk.export(output_buffer, format=source_format)
                chunk_data.append(output_buffer.getvalue())
            
            logger.debug(f"Created {len(chunk_data)} audio chunks")
            return chunk_data
            
        except Exception as e:
            logger.error(f"Audio chunking failed: {e}")
            return [audio_data]
    
    def get_optimal_config_for_bandwidth(self, bandwidth_kbps: int) -> AudioConfig:
        """
        Get optimal audio configuration for given bandwidth
        
        Args:
            bandwidth_kbps: Available bandwidth in kbps
            
        Returns:
            Optimal audio configuration
        """
        if bandwidth_kbps >= 256:
            return self.quality_presets["high"]
        elif bandwidth_kbps >= 128:
            return self.quality_presets["good"]
        else:
            return self.quality_presets["low"]
    
    def estimate_file_size(
        self,
        duration_seconds: float,
        config: AudioConfig
    ) -> int:
        """
        Estimate file size for given duration and configuration
        
        Args:
            duration_seconds: Audio duration in seconds
            config: Audio configuration
            
        Returns:
            Estimated file size in bytes
        """
        try:
            bitrate_bps = int(config.bitrate.replace('k', '')) * 1000
            estimated_size = int((bitrate_bps * duration_seconds) / 8)
            
            # Apply format compression ratio
            if config.format in self.format_configs:
                compression_ratio = self.format_configs[config.format]["compression_ratio"]
                estimated_size = int(estimated_size * compression_ratio)
            
            return estimated_size
            
        except Exception:
            return int(duration_seconds * 16000)  # Fallback estimate
    
    async def validate_audio_data(self, audio_data: bytes, format: str = "mp3") -> bool:
        """
        Validate audio data integrity
        
        Args:
            audio_data: Audio data to validate
            format: Expected audio format
            
        Returns:
            True if audio data is valid
        """
        if not audio_data:
            return False
        
        if not PYDUB_AVAILABLE:
            # Basic validation without pydub
            return len(audio_data) > 1024  # Minimum reasonable size
        
        try:
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=format
            )
            
            # Basic validation checks
            if len(audio) < 100:  # Minimum 100ms
                return False
            
            if audio.frame_rate < 8000:  # Minimum reasonable sample rate
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Audio validation failed: {e}")
            return False