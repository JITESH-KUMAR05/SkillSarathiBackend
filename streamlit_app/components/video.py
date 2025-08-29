"""
Video Processing Components
==========================

WebRTC video call capabilities and video analysis for interview features.
"""

import streamlit as st
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime

# RTC Configuration for WebRTC
RTC_CONFIGURATION = RTCConfiguration(
    iceServers=[
        {"urls": ["stun:stun.l.google.com:19302"]},
    ]
)

class VideoAnalyzer:
    """Analyze video stream for interview features"""
    
    def __init__(self):
        self.face_cascade = None
        self.eye_cascade = None
        self.init_opencv_classifiers()
        
        # Analysis metrics
        self.metrics = {
            "face_detected": False,
            "eye_contact_score": 0.0,
            "face_count": 0,
            "looking_away_count": 0,
            "total_frames": 0,
            "start_time": time.time()
        }
    
    def init_opencv_classifiers(self):
        """Initialize OpenCV face and eye classifiers"""
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        except Exception as e:
            st.warning(f"Could not load OpenCV classifiers: {e}")
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """Analyze a single video frame"""
        self.metrics["total_frames"] += 1
        
        if self.face_cascade is None or self.eye_cascade is None:
            return self.metrics
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        self.metrics["face_count"] = len(faces)
        self.metrics["face_detected"] = len(faces) > 0
        
        # Analyze each face
        for (x, y, w, h) in faces:
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # Region of interest for eyes
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            
            # Detect eyes
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            
            # Calculate eye contact (simplified)
            if len(eyes) >= 2:
                self.metrics["eye_contact_score"] += 1
                cv2.putText(frame, "Good Eye Contact", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            else:
                self.metrics["looking_away_count"] += 1
                cv2.putText(frame, "Look at Camera", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
            
            # Draw rectangles around eyes
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (0, 255, 0), 2)
        
        # Multiple face detection (potential cheating)
        if len(faces) > 1:
            cv2.putText(frame, "ALERT: Multiple Faces", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        return self.metrics

    def get_session_summary(self) -> Dict:
        """Get summary of video analysis session"""
        total_frames = self.metrics["total_frames"]
        if total_frames == 0:
            return {"error": "No frames analyzed"}
        
        duration = time.time() - self.metrics["start_time"]
        
        return {
            "session_duration": f"{duration:.1f} seconds",
            "total_frames": total_frames,
            "face_detection_rate": f"{(self.metrics['face_count'] / total_frames * 100):.1f}%",
            "eye_contact_score": f"{(self.metrics['eye_contact_score'] / total_frames * 100):.1f}%",
            "looking_away_incidents": self.metrics["looking_away_count"],
            "overall_score": self.calculate_overall_score()
        }
    
    def calculate_overall_score(self) -> int:
        """Calculate overall interview performance score"""
        if self.metrics["total_frames"] == 0:
            return 0
        
        face_score = min(100, (self.metrics["face_count"] / self.metrics["total_frames"]) * 100)
        eye_score = min(100, (self.metrics["eye_contact_score"] / self.metrics["total_frames"]) * 100)
        
        # Penalize for looking away too much
        penalty = min(20, self.metrics["looking_away_count"] / 10)
        
        overall = (face_score * 0.3 + eye_score * 0.7) - penalty
        return max(0, min(100, int(overall)))

# Global video analyzer instance
video_analyzer = VideoAnalyzer()

def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    """Process video frames for analysis"""
    img = frame.to_ndarray(format="bgr24")
    
    # Analyze frame
    metrics = video_analyzer.analyze_frame(img)
    
    # Add analysis overlay
    cv2.putText(img, f"Frames: {metrics['total_frames']}", (10, img.shape[0] - 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.putText(img, f"Faces: {metrics['face_count']}", (10, img.shape[0] - 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    return av.VideoFrame.from_ndarray(img, format="bgr24")

def create_video_interview_component(key: str = "video_interview"):
    """Create WebRTC video interview component"""
    
    st.subheader("📹 Live Video Interview")
    
    # Video stream component
    webrtc_ctx = webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTC_CONFIGURATION,
        video_frame_callback=video_frame_callback,
        media_stream_constraints={
            "video": True,
            "audio": True
        },
        async_processing=True,
    )
    
    # Show analysis metrics in real-time
    if webrtc_ctx.video_receiver:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            face_detected = video_analyzer.metrics.get("face_detected", False)
            st.metric("Face Detection", "✅ Yes" if face_detected else "❌ No")
        
        with col2:
            face_count = video_analyzer.metrics.get("face_count", 0)
            if face_count > 1:
                st.metric("Face Count", face_count, delta="⚠️ Multiple")
            else:
                st.metric("Face Count", face_count)
        
        with col3:
            total_frames = video_analyzer.metrics.get("total_frames", 0)
            st.metric("Frames Analyzed", total_frames)
        
        # Real-time feedback
        if video_analyzer.metrics.get("looking_away_count", 0) > 10:
            st.warning("⚠️ Try to maintain better eye contact with the camera")
        
        if face_count > 1:
            st.error("🚨 Multiple faces detected - ensure you're alone during the interview")
    
    return webrtc_ctx

def show_video_analysis_summary():
    """Show summary of video analysis"""
    
    summary = video_analyzer.get_session_summary()
    
    if "error" not in summary:
        st.subheader("📊 Interview Performance Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Session Duration", summary["session_duration"])
            st.metric("Face Detection Rate", summary["face_detection_rate"])
            st.metric("Eye Contact Score", summary["eye_contact_score"])
        
        with col2:
            st.metric("Looking Away Incidents", summary["looking_away_incidents"])
            st.metric("Overall Performance", f"{summary['overall_score']}%")
        
        # Performance interpretation
        score = summary["overall_score"]
        if score >= 80:
            st.success("🎉 Excellent performance! You maintained good presence throughout.")
        elif score >= 60:
            st.info("👍 Good performance with room for improvement in eye contact.")
        else:
            st.warning("⚠️ Consider practicing better camera presence and eye contact.")

def create_screen_share_component():
    """Create screen sharing component (placeholder)"""
    
    st.subheader("🖥️ Screen Sharing")
    
    st.info("""
    **Screen Sharing Features (Coming Soon):**
    - 📺 Share your screen for coding interviews
    - 🔍 AI-powered code analysis
    - 📊 Real-time feedback on coding patterns
    - 🎯 LeetCode problem integration
    """)
    
    if st.button("🖥️ Start Screen Share"):
        st.warning("Screen sharing feature will be implemented in the next version")
    
    # Placeholder for screen capture
    st.markdown("""
    ```javascript
    // Screen Capture API Integration
    navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true
    }).then(stream => {
        // Handle screen sharing stream
        console.log('Screen sharing started');
    });
    ```
    """)

def show_cheating_detection_alerts():
    """Show cheating detection alerts and warnings"""
    
    st.subheader("🛡️ Interview Integrity Monitoring")
    
    # Mock cheating detection alerts
    alerts = []
    
    if video_analyzer.metrics.get("face_count", 0) > 1:
        alerts.append("🚨 Multiple faces detected")
    
    if video_analyzer.metrics.get("looking_away_count", 0) > 20:
        alerts.append("⚠️ Excessive looking away from camera")
    
    if video_analyzer.metrics.get("total_frames", 0) > 100 and not video_analyzer.metrics.get("face_detected", False):
        alerts.append("❌ No face detected for extended period")
    
    if alerts:
        st.error("**Potential Issues Detected:**")
        for alert in alerts:
            st.write(f"• {alert}")
    else:
        st.success("✅ No integrity issues detected")

# Export functions for easy import
__all__ = [
    'VideoAnalyzer',
    'create_video_interview_component', 
    'show_video_analysis_summary',
    'create_screen_share_component',
    'show_cheating_detection_alerts',
    'video_analyzer'
]
