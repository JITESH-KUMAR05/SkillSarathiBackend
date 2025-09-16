"""
Voice Performance Monitor
========================

Tracks and reports voice pipeline performance metrics
for latency optimization and monitoring.
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class VoiceMetrics:
    """Voice generation performance metrics"""
    session_id: str
    agent_type: str
    text_length: int
    start_time: float
    first_chunk_time: Optional[float] = None
    completion_time: Optional[float] = None
    total_audio_bytes: int = 0
    chunk_count: int = 0
    success: bool = False
    error_message: Optional[str] = None
    
    @property
    def latency_to_first_chunk(self) -> Optional[float]:
        """Time to receive first audio chunk (critical for perceived latency)"""
        if self.first_chunk_time:
            return self.first_chunk_time - self.start_time
        return None
    
    @property
    def total_generation_time(self) -> Optional[float]:
        """Total time to complete voice generation"""
        if self.completion_time:
            return self.completion_time - self.start_time
        return None
    
    @property
    def audio_throughput_kbps(self) -> Optional[float]:
        """Audio throughput in KB/s"""
        if self.total_generation_time and self.total_generation_time > 0:
            return (self.total_audio_bytes / 1024) / self.total_generation_time
        return None

class VoicePerformanceMonitor:
    """Monitor and track voice generation performance"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.active_sessions: Dict[str, VoiceMetrics] = {}
        
        # Performance targets (industry standards)
        self.target_first_chunk_ms = 500  # Sub-500ms to first audio
        self.target_total_time_ms = 2000  # Complete generation under 2s
        self.target_throughput_kbps = 64  # Minimum audio quality
        
    def start_session(self, session_id: str, agent_type: str, text: str) -> VoiceMetrics:
        """Start tracking a new voice generation session"""
        metrics = VoiceMetrics(
            session_id=session_id,
            agent_type=agent_type,
            text_length=len(text),
            start_time=time.time()
        )
        
        self.active_sessions[session_id] = metrics
        logger.info(f"📊 Started tracking session {session_id} for {agent_type}")
        return metrics
    
    def record_first_chunk(self, session_id: str, chunk_size: int):
        """Record the first audio chunk received"""
        if session_id in self.active_sessions:
            metrics = self.active_sessions[session_id]
            if not metrics.first_chunk_time:  # Only record the first chunk
                metrics.first_chunk_time = time.time()
                metrics.total_audio_bytes += chunk_size
                metrics.chunk_count += 1
                
                latency_sec = metrics.latency_to_first_chunk
                if latency_sec:
                    latency = latency_sec * 1000  # Convert to ms
                    status = "✅" if latency <= self.target_first_chunk_ms else "⚠️"
                    logger.info(f"{status} First chunk latency: {latency:.1f}ms (target: {self.target_first_chunk_ms}ms)")
    
    def record_chunk(self, session_id: str, chunk_size: int):
        """Record an audio chunk"""
        if session_id in self.active_sessions:
            metrics = self.active_sessions[session_id]
            metrics.total_audio_bytes += chunk_size
            metrics.chunk_count += 1
    
    def complete_session(self, session_id: str, success: bool = True, error: Optional[str] = None):
        """Complete a voice generation session"""
        if session_id in self.active_sessions:
            metrics = self.active_sessions[session_id]
            metrics.completion_time = time.time()
            metrics.success = success
            metrics.error_message = error
            
            # Move to history
            self.metrics_history.append(metrics)
            del self.active_sessions[session_id]
            
            # Log performance summary
            self._log_session_summary(metrics)
    
    def _log_session_summary(self, metrics: VoiceMetrics):
        """Log performance summary for a completed session"""
        if not metrics.success:
            logger.error(f"❌ Session {metrics.session_id} failed: {metrics.error_message}")
            return
        
        first_chunk_ms = (metrics.latency_to_first_chunk or 0) * 1000
        total_time_ms = (metrics.total_generation_time or 0) * 1000
        throughput = metrics.audio_throughput_kbps or 0
        
        # Performance assessment
        first_chunk_ok = first_chunk_ms <= self.target_first_chunk_ms
        total_time_ok = total_time_ms <= self.target_total_time_ms
        throughput_ok = throughput >= self.target_throughput_kbps
        
        status = "🚀" if all([first_chunk_ok, total_time_ok, throughput_ok]) else "⚠️"
        
        logger.info(f"{status} Session {metrics.session_id} completed:")
        logger.info(f"  Agent: {metrics.agent_type}")
        logger.info(f"  Text length: {metrics.text_length} chars")
        logger.info(f"  First chunk: {first_chunk_ms:.1f}ms {'✅' if first_chunk_ok else '❌'}")
        logger.info(f"  Total time: {total_time_ms:.1f}ms {'✅' if total_time_ok else '❌'}")
        logger.info(f"  Throughput: {throughput:.1f} KB/s {'✅' if throughput_ok else '❌'}")
        logger.info(f"  Audio size: {metrics.total_audio_bytes} bytes ({metrics.chunk_count} chunks)")
    
    def get_performance_stats(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        # Filter metrics by agent type if specified
        recent_metrics = list(self.metrics_history)
        if agent_type:
            recent_metrics = [m for m in recent_metrics if m.agent_type == agent_type]
        
        if not recent_metrics:
            return {"error": "No metrics available"}
        
        # Calculate statistics
        successful_metrics = [m for m in recent_metrics if m.success]
        
        if not successful_metrics:
            return {"error": "No successful sessions"}
        
        first_chunk_times = [m.latency_to_first_chunk for m in successful_metrics if m.latency_to_first_chunk]
        total_times = [m.total_generation_time for m in successful_metrics if m.total_generation_time]
        throughputs = [m.audio_throughput_kbps for m in successful_metrics if m.audio_throughput_kbps]
        
        def safe_avg(values):
            return sum(values) / len(values) if values else 0
        
        def safe_percentile(values, p):
            if not values:
                return 0
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * p / 100)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]
        
        stats = {
            "total_sessions": len(recent_metrics),
            "successful_sessions": len(successful_metrics),
            "success_rate": len(successful_metrics) / len(recent_metrics) * 100,
            "first_chunk_latency": {
                "avg_ms": safe_avg(first_chunk_times) * 1000,
                "p95_ms": safe_percentile(first_chunk_times, 95) * 1000,
                "target_ms": self.target_first_chunk_ms,
                "meets_target_pct": len([t for t in first_chunk_times if t * 1000 <= self.target_first_chunk_ms]) / len(first_chunk_times) * 100 if first_chunk_times else 0
            },
            "total_generation_time": {
                "avg_ms": safe_avg(total_times) * 1000,
                "p95_ms": safe_percentile(total_times, 95) * 1000,
                "target_ms": self.target_total_time_ms,
                "meets_target_pct": len([t for t in total_times if t * 1000 <= self.target_total_time_ms]) / len(total_times) * 100 if total_times else 0
            },
            "throughput": {
                "avg_kbps": safe_avg(throughputs),
                "min_kbps": min(throughputs) if throughputs else 0,
                "target_kbps": self.target_throughput_kbps
            },
            "agent_breakdown": self._get_agent_breakdown(successful_metrics)
        }
        
        return stats
    
    def _get_agent_breakdown(self, metrics: List[VoiceMetrics]) -> Dict[str, Dict[str, float]]:
        """Get performance breakdown by agent type"""
        agent_stats = defaultdict(list)
        
        for metric in metrics:
            if metric.latency_to_first_chunk:
                agent_stats[metric.agent_type].append(metric.latency_to_first_chunk * 1000)
        
        breakdown = {}
        for agent, latencies in agent_stats.items():
            breakdown[agent] = {
                "avg_first_chunk_ms": sum(latencies) / len(latencies),
                "sessions": len(latencies),
                "meets_target_pct": len([l for l in latencies if l <= self.target_first_chunk_ms]) / len(latencies) * 100
            }
        
        return breakdown

# Global performance monitor instance
performance_monitor = VoicePerformanceMonitor()