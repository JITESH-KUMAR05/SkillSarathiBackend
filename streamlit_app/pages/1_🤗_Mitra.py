"""
Mitra (Friend) Agent Page
========================

Dedicated page for emotional support and friendly conversations.
"""

import streamlit as st
from datetime import datetime
import time

# Page config
st.set_page_config(
    page_title="🤗 Mitra - Your Friend",
    page_icon="🤗",
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

def show_mitra_header():
    """Show Mitra's enhanced header section"""
    
    # Add custom CSS for better styling
    st.markdown("""
    <style>
    .mitra-header {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 50%, #FFA8A8 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
    }
    .mitra-subtitle {
        font-size: 1.2rem;
        margin-bottom: 1rem;
        opacity: 0.9;
    }
    .feature-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="mitra-header">
        <h1>🤗 मित्र (Mitra)</h1>
        <div class="mitra-subtitle">Your Caring AI Friend & Emotional Support Companion</div>
        <p>💝 I'm here to listen, understand, and support you through life's journey</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">
            🌟 Empathetic • 🗣️ Bilingual • 💬 Always Available • 🤗 Non-judgmental
        </p>
    </div>
    """, unsafe_allow_html=True)

def show_mood_selector():
    """Show enhanced mood selection interface"""
    
    st.markdown("### 🌈 How are you feeling today?")
    
    # Add mood selector styling
    st.markdown("""
    <style>
    .mood-button {
        text-align: center;
        padding: 1rem;
        margin: 0.25rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #dee2e6;
        transition: all 0.3s ease;
    }
    .mood-button:hover {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-color: #2196f3;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    moods = {
        "😊": "Happy",
        "😢": "Sad", 
        "😰": "Anxious",
        "😴": "Tired",
        "🤔": "Thoughtful"
    }
    
    selected_mood = None
    
    for i, (emoji, mood) in enumerate(moods.items()):
        col = [col1, col2, col3, col4, col5][i]
        with col:
            if st.button(f"{emoji}\n{mood}", key=f"mood_{mood}", use_container_width=True):
                selected_mood = mood
                session_manager.update_preference("current_mood", mood)
                st.success(f"Noted! You're feeling {mood.lower()} today.")
                st.balloons()  # Add celebration effect
    
    # Show current mood with better styling
    current_mood = session_manager.get_preference("current_mood")
    if current_mood:
        mood_emoji = [k for k, v in moods.items() if v == current_mood][0]
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%); 
                   padding: 1rem; border-radius: 10px; text-align: center; margin: 1rem 0;">
            <h4 style="margin: 0; color: #2e7d32;">Current Mood: {mood_emoji} {current_mood}</h4>
        </div>
        """, unsafe_allow_html=True)

def show_conversation_starters():
    """Show conversation starter suggestions"""
    
    st.subheader("💭 Need help starting a conversation?")
    
    starters = [
        "I had a really tough day today...",
        "I'm feeling grateful for...",
        "I've been thinking about...",
        "I need advice about...",
        "I want to share some good news!",
        "I'm worried about..."
    ]
    
    col1, col2 = st.columns(2)
    
    for i, starter in enumerate(starters):
        col = col1 if i % 2 == 0 else col2
        with col:
            if st.button(starter, key=f"starter_{i}", use_container_width=True):
                # Pre-fill the message input
                st.session_state.message_input = starter
                st.rerun()

def show_mitra_chat():
    """Show Mitra's chat interface with empathy features"""
    
    agent = "mitra"
    agent_config = get_agent_config(agent)
    
    st.subheader("💬 Chat with Mitra")
    
    # Conversation history
    conversation = session_manager.get_conversation_history(agent)
    
    # Create chat container with custom styling
    chat_container = st.container()
    
    with chat_container:
        if conversation:
            for message in conversation[-15:]:  # Show more messages for emotional context
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                        st.caption(f"📅 {message['timestamp'][:19]}")
                else:
                    with st.chat_message("assistant", avatar="🤗"):
                        st.write(message["content"])
                        st.caption(f"💖 Mitra • {message['timestamp'][:19]}")
                        
                        # Show empathy indicators
                        if any(word in message["content"].lower() for word in ["understand", "sorry", "feel", "support"]):
                            st.markdown("*🤗 Showing empathy*")
        else:
            st.info("👋 नमस्ते! I'm Mitra, your caring friend. How are you feeling today?")
    
    # Enhanced message input with mood context
    current_mood = session_manager.get_preference("current_mood")
    mood_context = f" (Feeling {current_mood})" if current_mood else ""
    
    # Voice input section
    if MIC_RECORDER_AVAILABLE:
        st.markdown("### 🎤 Voice Input")
        voice_input = mic_recorder(
            start_prompt="🎤 Start Speaking",
            stop_prompt="⏹️ Stop Recording", 
            just_once=False,
            use_container_width=True,
            callback=None,
            args=(),
            kwargs={},
            key=f"mitra_voice_input"
        )
        
        # Process voice input
        if voice_input and voice_input.get('bytes'):
            st.success("🎵 Voice recorded! Processing...")
            # Here you would typically transcribe the audio
            # For now, we'll show a placeholder
            st.info("🔄 Voice transcription feature coming soon!")
    else:
        st.info("🎤 Install voice packages to enable speech input")
    
    # Voice Conversation Interface
    audio_manager.create_voice_conversation_interface(agent)
    
    # Get pre-filled message if any
    default_message = st.session_state.get("message_input", "")
    
    with st.form("mitra_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_area(
                f"Share with Mitra{mood_context}",
                value=default_message,
                placeholder="Type your message... (or use voice input above)",
                height=100,
                label_visibility="collapsed",
                key="mitra_text_input",
                help="💡 You can type here or use the voice input button above to speak directly!"
            )
        
        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            send_button = st.form_submit_button("💝 Share", use_container_width=True)
    
    # Voice input placeholder (outside form)
    if st.button("🎤 Voice", help="Click to hear AI response in voice"):
        # Get the last AI message and play it as voice
        conversation_history = session_manager.get_conversation_history(agent)
        if conversation_history:
            # Find the last assistant message
            last_ai_message = None
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    last_ai_message = msg.get("content", "")
                    break
            
            if last_ai_message:
                with st.spinner("🔊 Generating voice..."):
                    audio_data = api_client.generate_voice(last_ai_message, agent)
                    if audio_data and audio_data != b"placeholder_audio":
                        audio_manager.play_audio(audio_data, auto_play=True)
                        st.success("🎵 Playing voice response!")
                    else:
                        st.info("🎵 Voice generation completed!")
            else:
                st.info("🤗 Send a message first, then I'll speak it for you!")
        else:
            st.info("🤗 Send a message first, then I'll speak it for you!")
    
    # Clear pre-filled message after display
    if "message_input" in st.session_state:
        del st.session_state.message_input
    
    # Process message with enhanced empathy
    if send_button and user_input:
        # Add user message with mood context
        session_manager.add_message(agent, "user", user_input)
        
        # Enhanced prompt for empathy
        empathy_prompt = f"""
        User mood: {current_mood if current_mood else 'Unknown'}
        User message: {user_input}
        
        Please respond as Mitra, a caring Hindi-English speaking friend. Show empathy, use appropriate Hindi phrases naturally, and provide emotional support. Be warm, understanding, and helpful.
        """
        
        # Get response with empathy context
        with st.spinner("🤗 Mitra is listening with care..."):
            response = api_client.send_chat_message(
                empathy_prompt,
                agent,
                session_manager.get_user_id(),
                session_manager.get_session_id(agent)  # Add session_id
            )
        
        # Add response with empathy processing
        if response and "response" in response:
            response_text = response["response"]
            session_manager.add_message(agent, "assistant", response_text)
            
            # Generate voice with caring tone
            if session_manager.get_preference("voice_enabled", True):
                audio_data = api_client.generate_voice(response_text, agent)
                if audio_data:
                    auto_play = session_manager.get_preference("auto_play", True)
                    audio_manager.play_audio(audio_data, auto_play)
        
        st.rerun()

def show_mitra_features():
    """Show Mitra's special features"""
    
    st.subheader("🌟 Special Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **🎭 Emotion Recognition**
        - Mood tracking
        - Empathy responses
        - Emotional support
        """)
    
    with col2:
        st.markdown("""
        **🗣️ Bilingual Support**
        - Hindi & English
        - Natural code-switching
        - Cultural understanding
        """)
    
    with col3:
        st.markdown("""
        **💝 Caring Features**
        - Active listening
        - Personalized responses
        - Memory of your feelings
        """)

def show_wellness_tips():
    """Show wellness and self-care tips"""
    
    with st.expander("🌱 Daily Wellness Tips", expanded=False):
        tips = [
            "🌅 Start your day with gratitude - think of 3 things you're thankful for",
            "🧘‍♀️ Take 5 deep breaths when feeling stressed",
            "🚶‍♀️ A short walk can boost your mood significantly", 
            "💧 Stay hydrated - your brain needs water to function well",
            "📱 Take breaks from social media to reduce anxiety",
            "😴 Prioritize 7-8 hours of sleep for emotional balance",
            "🎵 Listen to music that makes you feel good",
            "📝 Journal your thoughts to process emotions"
        ]
        
        import random
        daily_tip = random.choice(tips)
        st.info(f"**Today's Tip:** {daily_tip}")
        
        if st.button("🔄 Get Another Tip"):
            st.rerun()

def main():
    """Main Mitra page function"""
    
    # Initialize session for Mitra
    session_manager.set_current_agent("mitra")
    
    # Show header
    show_mitra_header()
    
    st.divider()
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Chat interface
        show_mitra_chat()
    
    with col2:
        # Voice Settings
        with st.expander("🎵 Voice Settings", expanded=False):
            voice_enabled = st.checkbox(
                "🔊 Enable Voice Responses",
                value=session_manager.get_preference("voice_enabled", True),
                key="mitra_voice_enabled"
            )
            session_manager.set_preference("voice_enabled", voice_enabled)
            
            if voice_enabled:
                auto_play = st.checkbox(
                    "🔄 Auto-play Responses",
                    value=session_manager.get_preference("auto_play", True),
                    key="mitra_auto_play",
                    help="Automatically play voice when Mitra responds"
                )
                session_manager.set_preference("auto_play", auto_play)
                
                if auto_play:
                    st.success("✅ Voice will play automatically")
                else:
                    st.info("ℹ️ Click voice button to hear responses")
            else:
                st.warning("⚠️ Voice responses disabled")
        
        # Mood selector
        show_mood_selector()
        
        st.divider()
        
        # Conversation starters
        show_conversation_starters()
        
        st.divider()
        
        # Wellness tips
        show_wellness_tips()
    
    st.divider()
    
    # Features section
    show_mitra_features()
    
    # Footer
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🤗 Mitra is here to support you with care and empathy</p>
        <p>Remember: It's okay to not be okay. You're not alone. 💝</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
