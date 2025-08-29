"""
BuddyAgents Streamlit Frontend
=============================

Main application entry point for the BuddyAgents multi-agent platform.
"""

import streamlit as st
import time
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="🙏 BuddyAgents - Your AI Companions",
    page_icon="🙏",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/buddyagents',
        'Report a bug': "https://github.com/your-repo/buddyagents/issues",
        'About': "BuddyAgents - Your AI Companions for India"
    }
)

# Import utilities
from utils.config import config, get_agent_config, get_all_agents
from utils.session import session_manager
from utils.api_client import api_client, get_backend_status, get_available_agents
from utils.audio import audio_manager, show_audio_controls

def show_sidebar():
    """Render the main sidebar with navigation and settings"""
    
    with st.sidebar:
        st.title("🙏 BuddyAgents")
        st.markdown("*Your AI Companions*")
        
        # Backend status
        status = get_backend_status()
        if status.get("status") == "healthy":
            st.success("🟢 Backend Connected")
        else:
            st.error("🔴 Backend Disconnected")
            st.warning("Please start the backend server")
        
        st.divider()
        
        # User profile section
        if not session_manager.get_preference("authenticated", False):
            with st.expander("👤 User Profile", expanded=False):
                with st.form("profile_form"):
                    name = st.text_input("Name", placeholder="Enter your name")
                    email = st.text_input("Email", placeholder="Enter your email")
                    
                    if st.form_submit_button("Save Profile"):
                        if name and email:
                            session_manager.set_user_profile(name, email)
                            st.success("Profile saved!")
                            st.rerun()
                        else:
                            st.error("Please fill in all fields")
        else:
            profile = session_manager.get_user_profile()
            if profile:
                st.info(f"👋 Welcome, {profile['name']}!")
                if st.button("Logout"):
                    session_manager.logout()
                    st.rerun()
        
        st.divider()
        
        # Agent selection
        st.subheader("🤖 Select Your Companion")
        
        agents = get_all_agents()
        current_agent = session_manager.get_current_agent()
        
        # Create agent selection buttons
        for agent in agents:
            agent_config = get_agent_config(agent)
            if agent_config:
                is_selected = agent == current_agent
                button_type = "primary" if is_selected else "secondary"
                
                if st.button(
                    f"{agent_config['emoji']} {agent_config['name']}",
                    key=f"agent_{agent}",
                    type=button_type,
                    use_container_width=True,
                    help=agent_config['description']
                ):
                    session_manager.set_current_agent(agent)
                    st.rerun()
        
        st.divider()
        
        # Audio settings
        st.subheader("🔊 Voice Settings")
        audio_controls = show_audio_controls(
            voice_enabled=session_manager.get_preference("voice_enabled", True)
        )
        
        # Update preferences
        for key, value in audio_controls.items():
            session_manager.set_preference(key, value)
        
        st.divider()
        
        # Theme settings
        st.subheader("🎨 Appearance")
        
        theme = st.selectbox(
            "Theme",
            ["light", "dark"],
            index=0 if session_manager.get_preference("theme") == "light" else 1
        )
        session_manager.set_preference("theme", theme)
        
        language = st.selectbox(
            "Language",
            ["en-IN", "hi-IN", "bn-IN", "ta-IN"],
            index=0,
            help="Select your preferred language"
        )
        session_manager.set_preference("language", language)
        
        st.divider()
        
        # Session info
        with st.expander("📊 Session Info", expanded=False):
            stats = session_manager.get_session_stats()
            st.json(stats)

def show_welcome_section():
    """Show welcome message and quick stats"""
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🙏 Welcome to BuddyAgents")
        st.markdown("""
        Your AI companions are here to help you with:
        - **Emotional support** with Mitra (मित्र)
        - **Learning & growth** with Guru (गुरु)  
        - **Interview preparation** with Parikshak (परीक्षक)
        """)
    
    with col2:
        # Quick stats
        stats = session_manager.get_session_stats()
        st.metric("Messages Today", stats["total_messages"])
        st.metric("Active Agent", stats["current_agent"].title())
    
    with col3:
        # Current time
        st.info(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        
        # Backend status
        status = get_backend_status()
        if status.get("status") == "healthy":
            st.success("✅ All Systems Ready")
        else:
            st.error("❌ Backend Issue")

def show_agent_interface():
    """Show the main agent interface"""
    
    current_agent = session_manager.get_current_agent()
    agent_config = get_agent_config(current_agent)
    
    if not agent_config:
        st.error("Agent configuration not found")
        return
    
    # Agent header
    st.header(f"{agent_config['emoji']} {agent_config['name']}")
    st.markdown(f"*{agent_config['description']}*")
    
    # Chat interface
    st.subheader("💬 Chat")
    
    # Display conversation history
    conversation = session_manager.get_conversation_history(current_agent)
    
    if conversation:
        # Create a container for messages
        chat_container = st.container()
        
        with chat_container:
            for message in conversation[-10:]:  # Show last 10 messages
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                        st.caption(f"📅 {message['timestamp'][:19]}")
                else:
                    with st.chat_message("assistant", avatar=agent_config['emoji']):
                        st.write(message["content"])
                        st.caption(f"📅 {message['timestamp'][:19]}")
    else:
        st.info(f"👋 Start a conversation with {agent_config['name']}!")
    
    # Message input
    with st.form(f"chat_form_{current_agent}", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        
        with col1:
            user_input = st.text_input(
                "Message",
                placeholder=f"Type your message to {agent_config['name']}...",
                label_visibility="collapsed"
            )
        
        with col2:
            send_button = st.form_submit_button("Send 📤", use_container_width=True)
    
    # Process message
    if send_button and user_input:
        # Add user message to history
        session_manager.add_message(current_agent, "user", user_input)
        
        # Get response from backend
        with st.spinner(f"🤔 {agent_config['name']} is thinking..."):
            response = api_client.send_chat_message(
                user_input, 
                current_agent, 
                session_manager.get_user_id()
            )
        
        # Add assistant response to history
        if response and "response" in response:
            session_manager.add_message(current_agent, "assistant", response["response"])
            
            # Generate voice if enabled
            if session_manager.get_preference("voice_enabled", True):
                audio_data = api_client.generate_voice(response["response"], current_agent)
                if audio_data:
                    auto_play = session_manager.get_preference("auto_play", True)
                    audio_manager.play_audio(audio_data, auto_play)
        
        # Refresh to show new messages
        st.rerun()
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear Chat", help="Clear conversation history"):
            session_manager.clear_conversation(current_agent)
            st.rerun()
    
    with col2:
        if st.button("📊 View Stats", help="View conversation statistics"):
            stats = session_manager.get_session_stats()
            st.json(stats)
    
    with col3:
        if st.button("💾 Export Chat", help="Export conversation"):
            export_data = session_manager.export_conversation(current_agent)
            st.download_button(
                "Download JSON",
                data=export_data,
                file_name=f"buddyagents_{current_agent}_conversation.json",
                mime="application/json"
            )

def main():
    """Main application function"""
    
    # Initialize session
    session_manager.init_session_state()
    
    # Show sidebar
    show_sidebar()
    
    # Main content area
    show_welcome_section()
    
    st.divider()
    
    # Agent interface
    show_agent_interface()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🙏 BuddyAgents - Your AI Companions for India</p>
        <p>Made with ❤️ using Streamlit & FastAPI</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
