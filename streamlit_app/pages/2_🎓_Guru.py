"""
Guru (Mentor) Agent Page
=======================

Dedicated page for learning, skill development, and educational guidance.
"""

import streamlit as st
from datetime import datetime
import time

# Page config
st.set_page_config(
    page_title="🎓 Guru - Your Mentor",
    page_icon="🎓",
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

def show_guru_header():
    """Show Guru's header section"""
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🎓 गुरु (Guru)")
        st.subheader("Your Learning Mentor")
        
        st.markdown("""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #4ECDC4 0%, #5FDED8 100%); border-radius: 10px; color: white;'>
            <h3>📚 Knowledge is the greatest wealth</h3>
            <p>I'm here to guide your learning journey, answer questions, and help you grow professionally and personally.</p>
        </div>
        """, unsafe_allow_html=True)

def show_learning_dashboard():
    """Show learning progress dashboard"""
    
    st.subheader("📊 Your Learning Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Mock learning stats - in production, this would come from user data
    with col1:
        st.metric("📚 Topics Explored", "12", "+3")
    
    with col2:
        st.metric("🎯 Goals Set", "5", "+1")
    
    with col3:
        st.metric("⏱️ Study Time", "45m", "+15m")
    
    with col4:
        st.metric("🏆 Achievements", "8", "+2")

def show_learning_modes():
    """Show different learning modes"""
    
    st.subheader("🎯 Choose Your Learning Mode")
    
    modes = {
        "📝 Q&A Session": "Ask me questions about any topic",
        "📄 Document Analysis": "Upload and analyze documents",
        "🧪 Quiz & Practice": "Test your knowledge",
        "🎯 Goal Setting": "Set and track learning goals",
        "🚀 Skill Assessment": "Evaluate your current skills"
    }
    
    selected_mode = st.selectbox("Learning Mode", list(modes.keys()))
    st.info(f"**Selected:** {modes[selected_mode]}")
    
    return selected_mode

def show_document_upload():
    """Show document upload and analysis"""
    
    st.subheader("📄 Document Analysis")
    
    uploaded_file = st.file_uploader(
        "Upload a document for analysis",
        type=['pdf', 'txt', 'docx', 'md'],
        help="Upload PDFs, text files, Word documents, or Markdown files"
    )
    
    if uploaded_file:
        st.success(f"📁 Uploaded: {uploaded_file.name}")
        
        if st.button("🔍 Analyze Document"):
            with st.spinner("🎓 Guru is analyzing your document..."):
                # Simulate document analysis
                time.sleep(2)
                
                analysis = f"""
                **Document Analysis: {uploaded_file.name}**
                
                📊 **Key Insights:**
                - Document contains educational content
                - Complexity level: Intermediate
                - Estimated reading time: 15 minutes
                
                🎯 **Learning Recommendations:**
                - Focus on main concepts first
                - Practice with examples provided
                - Review summary points
                
                💡 **Questions to Consider:**
                - How does this relate to your goals?
                - What practical applications exist?
                - Which areas need deeper study?
                """
                
                st.markdown(analysis)
                
                # Add to conversation
                session_manager.add_message("guru", "assistant", analysis)

def show_quiz_interface():
    """Show interactive quiz interface"""
    
    st.subheader("🧪 Knowledge Quiz")
    
    # Quiz topic selection
    topics = [
        "Python Programming",
        "Data Science",
        "Machine Learning", 
        "Web Development",
        "General Knowledge",
        "Current Affairs"
    ]
    
    selected_topic = st.selectbox("Choose Quiz Topic", topics)
    difficulty = st.select_slider("Difficulty Level", ["Beginner", "Intermediate", "Advanced"])
    
    if st.button("🎯 Start Quiz"):
        with st.spinner("🎓 Preparing your quiz..."):
            # Generate quiz questions
            quiz_prompt = f"""
            Create a 5-question quiz on {selected_topic} at {difficulty} level.
            Format as multiple choice with explanations.
            """
            
            response = api_client.send_chat_message(
                quiz_prompt,
                "guru",
                session_manager.get_user_id()
            )
            
            if response and "response" in response:
                st.markdown("### 📝 Your Quiz")
                st.markdown(response["response"])
                
                # Add to conversation
                session_manager.add_message("guru", "assistant", response["response"])

def show_goal_setting():
    """Show goal setting interface"""
    
    st.subheader("🎯 Learning Goals")
    
    with st.form("goal_setting"):
        goal_title = st.text_input("Goal Title", placeholder="e.g., Learn Python in 3 months")
        goal_description = st.text_area("Description", placeholder="Describe your learning goal...")
        target_date = st.date_input("Target Date")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        
        if st.form_submit_button("🎯 Set Goal"):
            if goal_title:
                goal_data = {
                    "title": goal_title,
                    "description": goal_description,
                    "target_date": target_date.isoformat(),
                    "priority": priority,
                    "created_date": datetime.now().isoformat()
                }
                
                # Store goal (in production, this would go to backend)
                if "learning_goals" not in st.session_state:
                    st.session_state.learning_goals = []
                
                st.session_state.learning_goals.append(goal_data)
                st.success(f"🎯 Goal '{goal_title}' has been set!")
                
                # Ask Guru for advice
                advice_prompt = f"I've set a learning goal: {goal_title}. {goal_description}. Please provide guidance and a learning plan."
                
                with st.spinner("🎓 Guru is creating your learning plan..."):
                    response = api_client.send_chat_message(
                        advice_prompt,
                        "guru", 
                        session_manager.get_user_id()
                    )
                    
                    if response and "response" in response:
                        st.markdown("### 📋 Your Learning Plan")
                        st.markdown(response["response"])
                        session_manager.add_message("guru", "assistant", response["response"])
    
    # Display existing goals
    if "learning_goals" in st.session_state and st.session_state.learning_goals:
        st.markdown("### 📋 Your Current Goals")
        for i, goal in enumerate(st.session_state.learning_goals):
            with st.expander(f"🎯 {goal['title']}", expanded=False):
                st.write(f"**Description:** {goal['description']}")
                st.write(f"**Target Date:** {goal['target_date']}")
                st.write(f"**Priority:** {goal['priority']}")

def show_guru_chat():
    """Show Guru's chat interface with learning focus"""
    
    agent = "guru"
    agent_config = get_agent_config(agent)
    
    st.subheader("💬 Ask Guru Anything")
    
    # Conversation history
    conversation = session_manager.get_conversation_history(agent)
    
    if conversation:
        for message in conversation[-10:]:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
                    st.caption(f"📅 {message['timestamp'][:19]}")
            else:
                with st.chat_message("assistant", avatar="🎓"):
                    st.write(message["content"])
                    st.caption(f"🎓 Guru • {message['timestamp'][:19]}")
    else:
        st.info("🙏 Namaste! I'm Guru, your learning mentor. What would you like to learn today?")
    
    # Learning-focused message input
    with st.form("guru_chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_area(
                "Ask Guru",
                placeholder="Ask about any topic, request explanations, or seek learning guidance...",
                height=100,
                label_visibility="collapsed"
            )
        
        with col2:
            st.write("")
            st.write("")
            send_button = st.form_submit_button("🎓 Ask", use_container_width=True)
    
    # Quick learning prompts (outside form)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("💡 Explain", help="Ask for detailed explanation"):
            st.session_state.quick_prompt = "Please explain this in detail: "
    with col4:
        if st.button("🎤 Voice", help="Click to hear AI response in voice"):
            st.info("🎵 Voice will work after sending a message!")
    
    # Process message with learning context
    if send_button and user_input:
        # Add context for educational responses
        learning_prompt = f"""
        As Guru, an educational mentor, please provide a comprehensive and educational response to: {user_input}
        
        Include:
        - Clear explanations
        - Practical examples
        - Learning tips
        - Next steps for deeper learning
        """
        
        session_manager.add_message(agent, "user", user_input)
        
        with st.spinner("🎓 Guru is preparing a comprehensive answer..."):
            response = api_client.send_chat_message(
                learning_prompt,
                agent,
                session_manager.get_user_id()
            )
        
        if response and "response" in response:
            session_manager.add_message(agent, "assistant", response["response"])
            
            # Generate voice with educational tone
            if session_manager.get_preference("voice_enabled", True):
                audio_data = api_client.generate_voice(response["response"], agent)
                if audio_data:
                    auto_play = session_manager.get_preference("auto_play", True)
                    audio_manager.play_audio(audio_data, auto_play)
        
        st.rerun()

def show_learning_resources():
    """Show curated learning resources"""
    
    with st.expander("📚 Curated Learning Resources", expanded=False):
        resources = {
            "Programming": [
                "🐍 Python.org - Official Python documentation",
                "📚 FreeCodeCamp - Interactive coding lessons",
                "🎯 LeetCode - Coding practice problems"
            ],
            "Data Science": [
                "📊 Kaggle Learn - Free data science courses",
                "🔬 Towards Data Science - Medium publication",
                "📈 Google Colab - Free Jupyter notebooks"
            ],
            "General Learning": [
                "🎓 Coursera - University courses online",
                "📹 Khan Academy - Free educational videos",
                "📚 edX - University-level courses"
            ]
        }
        
        for category, links in resources.items():
            st.markdown(f"**{category}:**")
            for link in links:
                st.markdown(f"• {link}")
            st.write("")

def main():
    """Main Guru page function"""
    
    # Initialize session for Guru
    session_manager.set_current_agent("guru")
    
    # Show header
    show_guru_header()
    
    st.divider()
    
    # Learning dashboard
    show_learning_dashboard()
    
    st.divider()
    
    # Main interface with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "📚 Learn", "🎯 Goals", "📊 Practice"])
    
    with tab1:
        show_guru_chat()
    
    with tab2:
        # Learning modes
        mode = show_learning_modes()
        
        if "Document Analysis" in mode:
            show_document_upload()
        elif "Quiz" in mode:
            show_quiz_interface()
        else:
            st.info(f"Selected mode: {mode}")
        
        # Learning resources
        show_learning_resources()
    
    with tab3:
        show_goal_setting()
    
    with tab4:
        show_quiz_interface()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🎓 Guru is here to guide your learning journey</p>
        <p>विद्या ददाति विनयं - Knowledge gives humility 📚</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
