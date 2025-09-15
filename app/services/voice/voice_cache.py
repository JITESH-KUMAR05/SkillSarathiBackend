"""
Redis-based intelligent caching system for voice-related operations.
Implements caching strategies for TTS audio, STT results, and conversation context.
"""

import json
import hashlib
import asyncio
import logging
from typing import Optional, Any, Dict, List, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class VoiceCache:
    """
    Intelligent caching system for voice operations using Redis.
    Features smart TTL management, fallback mechanisms, and performance optimization.
    """
    
    def __init__(self, redis_url: Optional[str] = None, ttl_hours: int = 1):
        self.redis_url = redis_url or "redis://localhost:6379"
        self.default_ttl = ttl_hours * 3600  # Convert to seconds
        self.redis_client: Optional[redis.Redis] = None
        self.fallback_cache: Dict[str, Any] = {}  # In-memory fallback
        self._connection_lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established with proper error handling."""
        if self.redis_client is None:
            async with self._connection_lock:
                if self.redis_client is None:
                    try:
                        self.redis_client = redis.from_url(
                            self.redis_url, 
                            decode_responses=False,
                            socket_timeout=5,
                            socket_connect_timeout=5,
                            retry_on_timeout=True
                        )
                        # Test connection
                        await self.redis_client.ping()
                        logger.info(f"Connected to Redis at {self.redis_url}")
                    except Exception as e:
                        logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
                        self.redis_client = None
    
    def _generate_cache_key(self, text: str, voice_id: str, **kwargs) -> str:
        """
        Generate unique cache key based on text, voice configuration, and parameters.
        
        Args:
            text: Input text for TTS
            voice_id: Voice identifier
            **kwargs: Additional parameters that affect output
        
        Returns:
            Unique cache key string
        """
        # Include relevant parameters in key generation
        key_components = {
            'text': text.strip().lower(),
            'voice_id': voice_id,
            'params': sorted(kwargs.items())
        }
        key_string = json.dumps(key_components, sort_keys=True)
        return f"voice_cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def cache_generated_speech(
        self, 
        text: str, 
        voice_id: str, 
        audio_data: bytes,
        metadata: Optional[Dict[str, Any]] = None,
        custom_ttl: Optional[int] = None
    ) -> bool:
        """
        Cache generated speech audio with metadata.
        
        Args:
            text: Original text input
            voice_id: Voice identifier used
            audio_data: Generated audio bytes
            metadata: Additional metadata (format, quality, etc.)
            custom_ttl: Custom TTL in seconds (optional)
        
        Returns:
            True if cached successfully, False otherwise
        """
        try:
            await self._ensure_connection()
            
            cache_key = self._generate_cache_key(text, voice_id)
            ttl = custom_ttl or self.default_ttl
            
            cache_data = {
                'audio_data': audio_data,
                'text': text,
                'voice_id': voice_id,
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat(),
                'size_bytes': len(audio_data)
            }
            
            if self.redis_client:
                # Store as JSON for metadata and binary for audio
                try:
                    serialized_data = json.dumps({
                        'text': cache_data['text'],
                        'voice_id': cache_data['voice_id'],
                        'metadata': cache_data['metadata'],
                        'created_at': cache_data['created_at'],
                        'size_bytes': cache_data['size_bytes']
                    }).encode()
                    
                    # Use pipeline for atomic operation
                    async with self.redis_client.pipeline() as pipe:
                        await pipe.hset(cache_key, mapping={
                            'metadata': serialized_data,
                            'audio_data': audio_data
                        })
                        await pipe.expire(cache_key, ttl)
                        await pipe.execute()
                    
                    logger.debug(f"Cached speech: {len(audio_data)} bytes for key {cache_key}")
                    return True
                except Exception as e:
                    logger.error(f"Redis cache write failed: {e}")
                    # Fall back to in-memory cache
                    self.fallback_cache[cache_key] = {
                        'data': cache_data,
                        'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
                    }
                    return True
            else:
                # In-memory fallback
                self.fallback_cache[cache_key] = {
                    'data': cache_data,
                    'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
                }
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache speech: {e}")
            return False
    
    async def get_cached_speech(
        self, 
        text: str, 
        voice_id: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached speech audio if available.
        
        Args:
            text: Original text input
            voice_id: Voice identifier
            **kwargs: Additional parameters
        
        Returns:
            Dict with audio_data and metadata, or None if not cached
        """
        try:
            await self._ensure_connection()
            
            cache_key = self._generate_cache_key(text, voice_id, **kwargs)
            
            # Try Redis first
            if self.redis_client:
                try:
                    cached_data = await self.redis_client.hgetall(cache_key)
                    if cached_data:
                        metadata_json = cached_data.get(b'metadata')
                        audio_data = cached_data.get(b'audio_data')
                        
                        if metadata_json and audio_data:
                            metadata = json.loads(metadata_json.decode())
                            
                            logger.debug(f"Cache hit for key {cache_key}")
                            return {
                                'audio_data': audio_data,
                                'text': metadata['text'],
                                'voice_id': metadata['voice_id'],
                                'metadata': metadata['metadata'],
                                'created_at': metadata['created_at'],
                                'size_bytes': metadata['size_bytes']
                            }
                except Exception as e:
                    logger.error(f"Redis cache read failed: {e}")
            
            # Try in-memory fallback
            if cache_key in self.fallback_cache:
                cached_item = self.fallback_cache[cache_key]
                if datetime.utcnow() < cached_item['expires_at']:
                    logger.debug(f"Fallback cache hit for key {cache_key}")
                    return cached_item['data']
                else:
                    # Remove expired item
                    del self.fallback_cache[cache_key]
            
            logger.debug(f"Cache miss for key {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached speech: {e}")
            return None
    
    async def invalidate_cache(self, pattern: str = "voice_cache:*") -> int:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern to match
        
        Returns:
            Number of keys deleted
        """
        deleted_count = 0
        try:
            await self._ensure_connection()
            
            if self.redis_client:
                try:
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        deleted_count = await self.redis_client.delete(*keys)
                        logger.info(f"Invalidated {deleted_count} cache entries")
                except Exception as e:
                    logger.error(f"Redis cache invalidation failed: {e}")
            
            # Also clear in-memory fallback
            keys_to_remove = [k for k in self.fallback_cache.keys() if k.startswith("voice_cache:")]
            for key in keys_to_remove:
                del self.fallback_cache[key]
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = {
            'redis_connected': False,
            'redis_keys': 0,
            'redis_memory_usage': 0,
            'fallback_keys': len(self.fallback_cache),
            'fallback_memory_estimate': 0
        }
        
        try:
            await self._ensure_connection()
            
            if self.redis_client:
                try:
                    # Get Redis stats
                    info = await self.redis_client.info('memory')
                    stats['redis_connected'] = True
                    stats['redis_memory_usage'] = info.get('used_memory', 0)
                    
                    keys = await self.redis_client.keys("voice_cache:*")
                    stats['redis_keys'] = len(keys)
                    
                except Exception as e:
                    logger.error(f"Failed to get Redis stats: {e}")
            
            # Estimate fallback cache memory usage
            fallback_memory = 0
            for key, value in self.fallback_cache.items():
                try:
                    if 'data' in value and 'audio_data' in value['data']:
                        fallback_memory += len(value['data']['audio_data'])
                except:
                    pass
            
            stats['fallback_memory_estimate'] = fallback_memory
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
        
        return stats
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Redis connection closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Context manager for Redis operations."""
        await self._ensure_connection()
        try:
            yield self.redis_client
        finally:
            pass  # Connection is reused