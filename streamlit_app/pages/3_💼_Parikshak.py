"""
Parikshak (Interviewer) Agent Page
=================================

Dedicated page for interview preparation with video calls and assessment features.
"""

import streamlit as st
from datetime import datetime
import time
import json

# Page config
st.set_page_config(
    page_title="💼 Parikshak - Your Interview Coach",
    page_icon="💼",
    layout="wide"
)

# Import utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config import config, get_agent_config
from utils.session import session_manager
from utils.api_client import api_client
from utils.audio import audio_manager

# Import voice input functionality
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_AVAILABLE = True
except ImportError:
    MIC_RECORDER_AVAILABLE = False
    st.warning("⚠️ Voice input not available. Install: uv add streamlit-mic-recorder")

def show_parikshak_header():
    """Show Parikshak's enhanced header section"""
    
    # Add custom CSS for Parikshak styling
    st.markdown("""
    <style>
    .parikshak-header {
        background: linear-gradient(135deg, #7E57C2 0%, #673AB7 50%, #5E35B1 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(126, 87, 194, 0.3);
    }
    .parikshak-subtitle {
        font-size: 1.2rem;
        margin-bottom: 1rem;
        opacity: 0.9;
    }
    .interview-metric {
        background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        text-align: center;
        border: 1px solid #ce93d8;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="parikshak-header">
        <h1>💼 परीक्षक (Parikshak)</h1>
        <div class="parikshak-subtitle">Your AI Interview Coach & Career Mentor</div>
        <p>🎯 Master interviews, build confidence, and advance your career</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">
            💪 Confidence Building • 📊 Performance Analytics • 🎤 Mock Interviews • 📈 Skill Assessment
        </p>
    </div>
    """, unsafe_allow_html=True)

def show_interview_dashboard():
    """Show interview preparation dashboard"""
    
    st.subheader("📊 Interview Preparation Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Mock interview stats
    with col1:
        st.metric("🎯 Practice Sessions", "15", "+3")
    
    with col2:
        st.metric("📈 Avg Score", "82%", "+5%")
    
    with col3:
        st.metric("⏱️ Interview Time", "2h 30m", "+45m")
    
    with col4:
        st.metric("🏆 Skills Improved", "12", "+2")

def show_interview_types():
    """Show different interview preparation modes"""
    
    st.subheader("🎯 Choose Interview Type")
    
    interview_types = {
        "💼 HR Interview": "Behavioral questions and company culture fit",
        "💻 Technical Interview": "Programming, algorithms, and technical skills",
        "🎯 Case Study": "Problem-solving and analytical thinking",
        "🗣️ Presentation": "Communication and presentation skills",
        "📞 Phone/Video Interview": "Remote interview simulation"
    }
    
    selected_type = st.selectbox("Interview Type", list(interview_types.keys()))
    st.info(f"**Focus:** {interview_types[selected_type]}")
    
    return selected_type

def show_video_interview_section():
    """Show video interview capabilities"""
    
    st.subheader("📹 Video Interview Simulation")
    
    # Video call status
    video_active = st.session_state.get("video_call_active", False)
    
    if not video_active:
        st.markdown("""
        ### 🎥 Start Your Video Interview
        
        **Features:**
        - ✅ Real-time video interaction
        - ✅ AI-powered feedback
        - ✅ Body language analysis
        - ✅ Eye contact tracking
        - ✅ Speech pattern analysis
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📹 Start Video Interview", type="primary", use_container_width=True):
                # Initialize video session
                st.session_state.video_call_active = True
                session_manager.start_interview_session()
                st.rerun()
        
        with col2:
            if st.button("🎤 Audio Only Interview", use_container_width=True):
                st.info("Starting audio-only interview...")
                session_manager.start_interview_session()
    
    else:
        # Video interface with WebRTC integration
        st.success("🟢 Video Interview Active")
        
        # Import and use video components
        try:
            from components.video import (
                create_video_interview_component,
                show_video_analysis_summary,
                show_cheating_detection_alerts
            )
            
            # Main video interview interface
            webrtc_ctx = create_video_interview_component("parikshak_main_video")
            
            # Show real-time analysis below video
            if webrtc_ctx.video_receiver:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 Real-time Analysis")
                    show_video_analysis_summary()
                
                with col2:
                    st.subheader("🛡️ Interview Integrity")
                    show_cheating_detection_alerts()
                    
        except ImportError:
            # Fallback to placeholder if video components not available
            st.markdown("""
            <div style='background: #f0f0f0; padding: 40px; text-align: center; border-radius: 10px; margin: 20px 0;'>
                <h3>📹 Video Stream Placeholder</h3>
                <p>Install video dependencies to enable WebRTC</p>
                <p><code>uv add streamlit-webrtc opencv-python aiortc</code></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Interview controls
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("⏸️ Pause"):
                st.info("Interview paused")
        
        with col2:
            if st.button("📊 Feedback"):
                show_live_feedback()
        
        with col3:
            if st.button("🔄 Next Question"):
                generate_interview_question()
        
        with col4:
            if st.button("⏹️ End Interview", type="secondary"):
                st.session_state.video_call_active = False
                session_manager.end_interview_session()
                st.rerun()

def show_live_feedback():
    """Show real-time interview feedback"""
    
    feedback_data = {
        "confidence": 75,
        "eye_contact": 80,
        "speech_clarity": 85,
        "body_language": 70,
        "response_quality": 78
    }
    
    st.subheader("📊 Live Performance Feedback")
    
    for metric, score in feedback_data.items():
        # Create progress bar with color coding
        if score >= 80:
            color = "green"
        elif score >= 60:
            color = "orange"  
        else:
            color = "red"
        
        st.metric(
            metric.replace("_", " ").title(),
            f"{score}%",
            delta=f"+{score-70}%" if score > 70 else f"{score-70}%"
        )

def generate_interview_question():
    """Generate interview questions based on type"""
    
    interview_type = st.session_state.get("current_interview_type", "HR Interview")
    
    questions_db = {
        "💼 HR Interview": [
            "Tell me about yourself and your career journey.",
            "Why do you want to work for our company?",
            "Describe a challenging situation you faced and how you handled it.",
            "What are your greatest strengths and weaknesses?",
            "Where do you see yourself in 5 years?"
        ],
        "💻 Technical Interview": [
            "Explain the difference between Python lists and tuples.",
            "How would you optimize a slow database query?",
            "Design a system to handle 1 million concurrent users.",
            "What is your approach to debugging complex issues?",
            "Explain object-oriented programming concepts."
        ],
        "🎯 Case Study": [
            "How would you increase user engagement for a mobile app?",
            "Design a solution for reducing customer wait times.",
            "Analyze the pros and cons of remote work policies.",
            "How would you handle a data breach incident?",
            "Create a strategy for entering a new market."
        ]
    }
    
    questions = questions_db.get(interview_type, questions_db["💼 HR Interview"])
    import random
    question = random.choice(questions)
    
    st.info(f"**Interview Question:** {question}")
    
    # Add to conversation
    session_manager.add_message("parikshak", "assistant", f"Interview Question: {question}")
    
    return question

def show_mock_interview():
    """Show text-based mock interview"""
    
    st.subheader("📝 Text Interview Practice")
    
    # Interview setup
    with st.form("interview_setup"):
        col1, col2 = st.columns(2)
        
        with col1:
            position = st.text_input("Position Applied For", placeholder="e.g., Software Engineer")
            company = st.text_input("Company Name", placeholder="e.g., Google")
        
        with col2:
            experience = st.selectbox("Experience Level", ["Fresher", "1-3 years", "3-5 years", "5+ years"])
            difficulty = st.selectbox("Question Difficulty", ["Easy", "Medium", "Hard"])
        
        if st.form_submit_button("🎯 Start Mock Interview"):
            if position:
                st.session_state.interview_context = {
                    "position": position,
                    "company": company,
                    "experience": experience,
                    "difficulty": difficulty
                }
                
                # Generate first question
                context_prompt = f"""
                I'm interviewing for a {position} position at {company}. 
                I have {experience} of experience. 
                Please ask me a {difficulty} level interview question appropriate for this role.
                """
                
                with st.spinner("🎯 Parikshak is preparing your interview..."):
                    response = api_client.send_chat_message(
                        context_prompt,
                        "parikshak",
                        session_manager.get_user_id()
                    )
                    
                    if response and "response" in response:
                        st.markdown("### 🎯 Your Interview Begins")
                        st.markdown(response["response"])
                        session_manager.add_message("parikshak", "assistant", response["response"])
                        st.rerun()

def show_parikshak_chat():
    """Show Parikshak's chat interface with interview focus"""
    
    agent = "parikshak"
    
    st.subheader("💬 Interview Practice Chat")
    
    # Show interview context if available
    if "interview_context" in st.session_state:
        context = st.session_state.interview_context
        st.info(f"🎯 **Interview Context:** {context['position']} at {context['company']} ({context['experience']} experience)")
    
    # Conversation history
    conversation = session_manager.get_conversation_history(agent)
    
    if conversation:
        for message in conversation[-8:]:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
                    st.caption(f"📅 {message['timestamp'][:19]}")
            else:
                with st.chat_message("assistant", avatar="💼"):
                    st.write(message["content"])
                    st.caption(f"💼 Parikshak • {message['timestamp'][:19]}")
    else:
        st.info("🙏 Namaste! I'm Parikshak, your interview coach. Ready to practice?")
    
    # Voice input section
    if MIC_RECORDER_AVAILABLE:
        st.markdown("### 🎤 Voice Interview Practice")
        voice_input = mic_recorder(
            start_prompt="🎤 Practice Interview (Voice)",
            stop_prompt="⏹️ Stop Recording", 
            just_once=False,
            use_container_width=True,
            callback=None,
            args=(),
            kwargs={},
            key=f"parikshak_voice_input"
        )
        
        # Process voice input
        if voice_input and voice_input.get('bytes'):
            st.success("🎵 Voice recorded! Processing...")
            st.info("🔄 Voice transcription feature coming soon!")
    else:
        st.info("🎤 Install voice packages to enable speech input")
    
    # Interview-focused input
    with st.form("parikshak_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_area(
                "Your Answer",
                placeholder="Provide your interview response here...",
                height=120,
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")
            st.write("")
            send_button = st.form_submit_button("💼 Submit", use_container_width=True)
    
    # Interview action buttons (outside form)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🎯 New Question"):
            generate_interview_question()
            st.rerun()
    with col4:
        if st.button("🎤 Voice", help="Click to hear AI response in voice"):
            st.info("🎵 Voice will work after submitting a response!")
    
    # Process interview response
    if send_button and user_input:
        # Add user message to conversation history
        session_manager.add_message("parikshak", "user", user_input)
        
        with st.spinner("💼 Parikshak is evaluating your response..."):
            # Get current session for conversation continuity
            current_session_id = session_manager.get_session_id("parikshak")
            
            response = api_client.send_chat_message(
                user_input,  # Send original message, not modified prompt
                "parikshak",
                session_manager.get_user_id(),
                current_session_id
            )
        
        if response and "response" in response and not response.get("error", False):
            session_manager.add_message("parikshak", "assistant", response["response"])
            
            # Generate voice feedback
            if session_manager.get_preference("voice_enabled", True):
                audio_data = api_client.generate_voice(response["response"], "parikshak")
                if audio_data:
                    auto_play = session_manager.get_preference("auto_play", True)
                    audio_manager.play_audio(audio_data, auto_play)
        else:
            error_msg = "There seems to be a technical issue on my end. Let's continue with your preparation - please rephrase your question and I'll do my best to help."
            session_manager.add_message("parikshak", "assistant", error_msg)
        
        st.rerun()

def show_interview_resources():
    """Show interview preparation resources"""
    
    with st.expander("📚 Interview Preparation Resources", expanded=False):
        resources = {
            "📝 Common Questions": [
                "Behavioral questions (STAR method)",
                "Technical skill assessments", 
                "Company-specific questions",
                "Salary negotiation tips"
            ],
            "💻 Technical Prep": [
                "Data structures and algorithms",
                "System design concepts",
                "Coding practice platforms",
                "Mock coding interviews"
            ],
            "🎯 Best Practices": [
                "Research the company thoroughly",
                "Prepare thoughtful questions",
                "Practice active listening",
                "Follow up professionally"
            ]
        }
        
        for category, items in resources.items():
            st.markdown(f"**{category}:**")
            for item in items:
                st.markdown(f"• {item}")
            st.write("")

def main():
    """Main Parikshak page function"""
    
    # Initialize session for Parikshak
    session_manager.set_current_agent("parikshak")
    
    # Show header
    show_parikshak_header()
    
    st.divider()
    
    # Interview dashboard
    show_interview_dashboard()
    
    st.divider()
    
    # Voice Settings
    with st.expander("🎵 Voice Settings", expanded=False):
        voice_enabled = st.checkbox(
            "🔊 Enable Voice Responses",
            value=session_manager.get_preference("voice_enabled", True),
            key="parikshak_voice_enabled"
        )
        session_manager.set_preference("voice_enabled", voice_enabled)
        
        if voice_enabled:
            auto_play = st.checkbox(
                "🔄 Auto-play Responses",
                value=session_manager.get_preference("auto_play", True),
                key="parikshak_auto_play",
                help="Automatically play voice when Parikshak responds"
            )
            session_manager.set_preference("auto_play", auto_play)
            
            if auto_play:
                st.success("✅ Voice will play automatically")
            else:
                st.info("ℹ️ Click voice button to hear responses")
        else:
            st.warning("⚠️ Voice responses disabled")
    
    st.divider()
    
    # Main interface with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Practice", "📹 Video Interview", "📝 Mock Interview", "📊 Assessment"])
    
    with tab1:
        show_parikshak_chat()
    
    with tab2:
        show_video_interview_section()
    
    with tab3:
        interview_type = show_interview_types()
        st.session_state.current_interview_type = interview_type
        show_mock_interview()
        show_interview_resources()
    
    with tab4:
        st.subheader("📊 Performance Analytics")
        
        # Mock performance data
        performance = {
            "Communication": 85,
            "Technical Skills": 78,
            "Problem Solving": 82,
            "Confidence": 75,
            "Overall": 80
        }
        
        for skill, score in performance.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.progress(score/100)
            with col2:
                st.write(f"{skill}: {score}%")
        
        if st.button("📈 Detailed Report"):
            st.info("Detailed performance report will be available in the full version.")
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>💼 Parikshak is here to help you succeed in interviews</p>
        <p>तैयारी सफलता की चाबी है - Preparation is the key to success 🗝️</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
