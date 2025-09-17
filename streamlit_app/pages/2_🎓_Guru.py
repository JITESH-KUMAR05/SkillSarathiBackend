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
from utils.api_client import api_client, init_api_client_with_session
from utils.audio import audio_manager

# Initialize API client with session manager
init_api_client_with_session(session_manager)

# Import voice input functionality
try:
    from streamlit_mic_recorder import mic_recorder
    MIC_RECORDER_AVAILABLE = True
except ImportError:
    MIC_RECORDER_AVAILABLE = False
    st.warning("⚠️ Voice input not available. Install: uv add streamlit-mic-recorder")

def show_guru_header():
    """Show Guru's enhanced header section"""
    
    # Add custom CSS for Guru styling
    st.markdown("""
    <style>
    .guru-header {
        background: linear-gradient(135deg, #4FC3F7 0%, #29B6F6 50%, #03A9F4 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(79, 195, 247, 0.3);
    }
    .guru-subtitle {
        font-size: 1.2rem;
        margin-bottom: 1rem;
        opacity: 0.9;
    }
    .learning-stats {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #ff9800;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="guru-header">
        <h1>🎓 गुरू (Guru)</h1>
        <div class="guru-subtitle">Your AI Learning Mentor & Knowledge Guide</div>
        <p>📚 Dedicated to expanding your knowledge and guiding your learning journey</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">
            🧠 Comprehensive • 📊 Interactive • 🎯 Goal-Oriented • 📈 Progress Tracking
        </p>
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
    """Show document upload, analysis, and concept explanation"""
    
    st.subheader("📄 Document Learning Hub")
    
    uploaded_file = st.file_uploader(
        "Upload a document for learning",
        type=['pdf', 'txt', 'docx', 'md'],
        help="Upload PDFs, text files, Word documents, or Markdown files for analysis and concept explanation"
    )
    
    if uploaded_file:
        st.success(f"📁 Uploaded: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Document processing options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Analyze Document", type="primary"):
                with st.spinner("🎓 Guru is analyzing your document..."):
                    # Read file content
                    try:
                        if uploaded_file.type == "text/plain":
                            content = str(uploaded_file.read(), "utf-8")
                        else:
                            content = f"Document content from {uploaded_file.name}"
                        
                        analysis_prompt = f"""
                        Analyze this document and provide:
                        1. Key concepts and topics covered
                        2. Difficulty level assessment
                        3. Learning objectives
                        4. Important terms and definitions
                        5. Practical applications
                        
                        Document content: {content[:1000]}...
                        """
                        
                        response = api_client.send_chat_message(
                            analysis_prompt,
                            "guru",
                            session_manager.get_user_id()
                        )
                        
                        if response and "response" in response:
                            st.markdown("### 📊 Document Analysis")
                            st.markdown(response["response"])
                            session_manager.add_message("guru", "assistant", response["response"])
                            
                            # Store document content for concept explanation
                            st.session_state.uploaded_document = {
                                "name": uploaded_file.name,
                                "content": content
                            }
                        
                    except Exception as e:
                        st.error(f"Error analyzing document: {e}")
        
        with col2:
            if st.button("🎓 Generate Quiz"):
                st.info("🎯 Go to the Practice tab to generate quiz from this document!")
        
        with col3:
            if st.button("💡 Explain Concepts"):
                with st.spinner("🎓 Extracting key concepts..."):
                    try:
                        if uploaded_file.type == "text/plain":
                            content = str(uploaded_file.read(), "utf-8")
                        else:
                            content = f"Document content from {uploaded_file.name}"
                        
                        concept_prompt = f"""
                        Extract and explain the key concepts from this document in simple terms:
                        
                        Document: {content[:1000]}...
                        
                        For each concept, provide:
                        - Clear definition
                        - Simple explanation
                        - Example if applicable
                        - Why it's important
                        """
                        
                        response = api_client.send_chat_message(
                            concept_prompt,
                            "guru",
                            session_manager.get_user_id()
                        )
                        
                        if response and "response" in response:
                            st.markdown("### 💡 Key Concepts Explained")
                            st.markdown(response["response"])
                            session_manager.add_message("guru", "assistant", response["response"])
                            
                    except Exception as e:
                        st.error(f"Error explaining concepts: {e}")
    
    # Concept explanation from text input
    st.markdown("---")
    st.markdown("### 🤔 Ask for Concept Explanation")
    
    with st.form("concept_explanation"):
        concept_input = st.text_input(
            "Enter a concept or topic you want explained:",
            placeholder="e.g., Machine Learning, Python Classes, Database Normalization..."
        )
        
        explanation_level = st.selectbox(
            "Explanation Level:",
            ["Simple (Beginner)", "Detailed (Intermediate)", "Technical (Advanced)"]
        )
        
        if st.form_submit_button("💡 Explain Concept"):
            if concept_input:
                with st.spinner(f"🎓 Guru is explaining '{concept_input}'..."):
                    level_mapping = {
                        "Simple (Beginner)": "beginner-friendly with simple examples",
                        "Detailed (Intermediate)": "detailed with practical examples",
                        "Technical (Advanced)": "technical with in-depth analysis"
                    }
                    
                    level_desc = level_mapping[explanation_level]
                    
                    explanation_prompt = f"""
                    Explain the concept "{concept_input}" in a {level_desc} manner.
                    
                    Include:
                    - Clear definition
                    - Key components or features
                    - Real-world examples
                    - Common use cases
                    - Related concepts
                    - Learning resources
                    
                    Make it educational and engaging for learning.
                    """
                    
                    response = api_client.send_chat_message(
                        explanation_prompt,
                        "guru",
                        session_manager.get_user_id()
                    )
                    
                    if response and "response" in response:
                        st.markdown(f"### 💡 Understanding: {concept_input}")
                        st.markdown(response["response"])
                        session_manager.add_message("guru", "assistant", response["response"])
                        
                        # Generate voice explanation
                        if session_manager.get_preference("voice_enabled", True):
                            audio_data = api_client.generate_voice(response["response"], "guru")
                            if audio_data:
                                auto_play = session_manager.get_preference("auto_play", True)
                                audio_manager.play_audio(audio_data, auto_play)

def generate_questions_from_content(document_content: str, num_questions: int, difficulty: str):
    """Generate AI-powered questions from document content based on difficulty and number"""
    import json
    
    # Create detailed prompt for AI question generation
    difficulty_guidelines = {
        "Beginner": "Focus on basic facts, simple recall, and straightforward information from the document. Questions should be easy to answer for someone just learning.",
        "Intermediate": "Include analysis, comparison, and application questions. Require understanding of concepts and relationships within the document.", 
        "Advanced": "Create complex questions requiring synthesis, evaluation, and deep analysis. Include scenarios and critical thinking elements."
    }
    
    # Build comprehensive prompt for AI
    ai_prompt = f"""
Based on the following document content, create exactly {num_questions} multiple choice questions at {difficulty} level.

DIFFICULTY GUIDELINES:
{difficulty_guidelines.get(difficulty, difficulty_guidelines["Beginner"])}

DOCUMENT CONTENT:
{document_content[:1500]}  

REQUIREMENTS:
1. Create exactly {num_questions} questions
2. Each question must have 4 options (A, B, C, D)
3. Provide correct answer (A, B, C, or D)
4. Include detailed explanation for each answer
5. Questions should be directly based on the document content
6. Use {difficulty.lower()} level complexity
7. Ensure questions test different aspects of the document

RESPONSE FORMAT (JSON only, no other text):
[
    {{
        "question": "Your question here?",
        "options": [
            "A) First option",
            "B) Second option", 
            "C) Third option",
            "D) Fourth option"
        ],
        "correct_answer": "A",
        "explanation": "Detailed explanation why this answer is correct"
    }}
]
"""
    
    # Try to get AI-generated questions
    try:
        response = api_client.send_chat_message(
            ai_prompt,
            "guru", 
            session_manager.get_user_id()
        )
        
        if response and "response" in response:
            # Try to parse JSON response
            try:
                questions_data = json.loads(response["response"])
                if isinstance(questions_data, list) and len(questions_data) > 0:
                    return questions_data[:num_questions]  # Ensure we don't exceed requested number
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                import re
                json_match = re.search(r'\[.*\]', response["response"], re.DOTALL)
                if json_match:
                    try:
                        questions_data = json.loads(json_match.group())
                        if isinstance(questions_data, list) and len(questions_data) > 0:
                            return questions_data[:num_questions]
                    except:
                        pass
    except Exception as e:
        print(f"AI question generation failed: {e}")
    
    # Fallback: Generate rule-based questions if AI fails
    return generate_fallback_questions_from_content(document_content, num_questions, difficulty)

def generate_fallback_questions_from_content(document_content: str, num_questions: int, difficulty: str):
    """Fallback method to generate questions using rule-based approach"""
    import re
    
    # Extract key information from document
    lines = [line.strip() for line in document_content.split('\n') if line.strip()]
    
    # Find names, skills, experience, education etc.
    questions = []
    
    # Extract email and contact info
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', document_content)
    phone_match = re.search(r'[\+]?[\d\s\-\(\)]{10,}', document_content)
    
    # Extract skills
    skill_keywords = ['python', 'java', 'javascript', 'react', 'node', 'database', 'sql', 'api', 'aws', 'docker']
    found_skills = [skill for skill in skill_keywords if skill.lower() in document_content.lower()]
    
    # Extract education keywords
    education_keywords = ['university', 'college', 'degree', 'bachelor', 'master', 'phd', 'graduation']
    found_education = [edu for edu in education_keywords if edu.lower() in document_content.lower()]
    
    # Extract experience keywords
    experience_keywords = ['experience', 'worked', 'developer', 'engineer', 'internship', 'project']
    found_experience = [exp for exp in experience_keywords if exp.lower() in document_content.lower()]
    
    # Generate questions based on extracted content and difficulty
    question_count = 0
    
    # Question about contact information (adjust difficulty)
    if email_match and question_count < num_questions:
        email = email_match.group()
        if difficulty == "Beginner":
            questions.append({
                "question": "What is the email address mentioned in this document?",
                "options": [
                    f"A) {email}",
                    "B) contact@example.com", 
                    "C) info@company.com",
                    "D) user@domain.com"
                ],
                "correct_answer": "A",
                "explanation": f"The email address {email} is explicitly mentioned in the document."
            })
        elif difficulty == "Intermediate":
            questions.append({
                "question": f"Based on the email format '{email}', what can you infer about the communication method?",
                "options": [
                    "A) Professional communication channel",
                    "B) Only for personal use",
                    "C) Temporary contact method",
                    "D) Social media handle"
                ],
                "correct_answer": "A",
                "explanation": "Email addresses in professional documents typically indicate formal communication channels."
            })
        else:  # Advanced
            questions.append({
                "question": f"Analyzing the domain structure of '{email}', what strategic insight can be drawn?",
                "options": [
                    "A) Indicates personal branding and professional online presence",
                    "B) Shows lack of technical understanding",
                    "C) Suggests only academic background",
                    "D) Implies temporary employment status"
                ],
                "correct_answer": "A",
                "explanation": "Professional email domains often reflect personal branding and digital presence strategy."
            })
        question_count += 1
    
    # Question about skills (adjust for difficulty)
    if found_skills and question_count < num_questions:
        main_skill = found_skills[0].title()
        if difficulty == "Beginner":
            questions.append({
                "question": f"Which of these skills is mentioned in the document?",
                "options": [
                    f"A) {main_skill}",
                    "B) Photography",
                    "C) Dancing", 
                    "D) Cooking"
                ],
                "correct_answer": "A",
                "explanation": f"{main_skill} is clearly mentioned as a skill in the document."
            })
        elif difficulty == "Intermediate":
            questions.append({
                "question": f"Considering the mention of {main_skill}, what type of professional profile does this suggest?",
                "options": [
                    "A) Technical/Technology professional",
                    "B) Creative arts professional",
                    "C) Healthcare professional",
                    "D) Finance professional"
                ],
                "correct_answer": "A",
                "explanation": f"Skills like {main_skill} typically indicate a technical background and expertise."
            })
        else:  # Advanced
            questions.append({
                "question": f"How might the presence of {main_skill} skills impact career trajectory and market value?",
                "options": [
                    "A) Increases adaptability in tech-driven markets and remote work opportunities",
                    "B) Limits career options to traditional industries only",
                    "C) Only relevant for entry-level positions",
                    "D) No significant impact on professional growth"
                ],
                "correct_answer": "A",
                "explanation": f"Technical skills like {main_skill} are increasingly valuable in digital transformation."
            })
        question_count += 1
    
    # Question about education
    if found_education and question_count < num_questions:
        edu_term = found_education[0].title()
        if difficulty == "Beginner":
            questions.append({
                "question": f"What educational background is indicated in the document?",
                "options": [
                    f"A) Contains {edu_term} information",
                    "B) No educational background mentioned",
                    "C) Only professional certifications",
                    "D) Self-taught only"
                ],
                "correct_answer": "A",
                "explanation": f"The document contains information about {edu_term}."
            })
        elif difficulty == "Intermediate":
            questions.append({
                "question": f"How does the {edu_term} background complement the professional profile?",
                "options": [
                    "A) Provides theoretical foundation for practical skills",
                    "B) Is completely unrelated to career path",
                    "C) Only matters for academic positions",
                    "D) Indicates lack of practical experience"
                ],
                "correct_answer": "A",
                "explanation": f"Educational background typically provides foundational knowledge that supports professional development."
            })
        else:  # Advanced
            questions.append({
                "question": f"What strategic advantage does formal {edu_term} provide in competitive markets?",
                "options": [
                    "A) Demonstrates systematic learning approach and credentialing for complex roles",
                    "B) Only useful for government jobs",
                    "C) Prevents innovation and creativity",
                    "D) No relevance in modern workplace"
                ],
                "correct_answer": "A",
                "explanation": f"Formal education demonstrates structured learning and is often required for specialized roles."
            })
        question_count += 1
    
    # Question about experience
    if found_experience and question_count < num_questions:
        exp_term = found_experience[0]
        questions.append({
            "question": f"What type of professional background is mentioned?",
            "options": [
                f"A) Has {exp_term} background",
                "B) No professional experience",
                "C) Only academic background",
                "D) Volunteer work only"
            ],
            "correct_answer": "A", 
            "explanation": f"The document mentions {exp_term} background."
        })
        question_count += 1
    
    # Fill remaining questions with content-based questions
    while question_count < num_questions:
        # Create questions based on document length and content
        word_count = len(document_content.split())
        
        if word_count > 100:
            questions.append({
                "question": "Based on the document content, what can you conclude?",
                "options": [
                    "A) This appears to be a detailed professional document",
                    "B) This is a short note",
                    "C) This is just a title page",
                    "D) This contains no meaningful information"
                ],
                "correct_answer": "A",
                "explanation": f"The document contains {word_count} words, indicating it's a detailed document."
            })
        else:
            questions.append({
                "question": "What type of document is this most likely to be?",
                "options": [
                    "A) A professional document or resume",
                    "B) A shopping list",
                    "C) A recipe",
                    "D) A poem"
                ],
                "correct_answer": "A",
                "explanation": "Based on the content structure and keywords, this appears to be a professional document."
            })
        
        question_count += 1
    
    return questions[:num_questions]

def get_fallback_questions(topic: str, num_questions: int):
    """Generate fallback questions for given topic"""
    fallback_questions = {
        "Python Programming": [
            {
                "question": "What is Python?",
                "options": [
                    "A) A high-level programming language",
                    "B) A snake species",
                    "C) A web browser", 
                    "D) A database"
                ],
                "correct_answer": "A",
                "explanation": "Python is a high-level, interpreted programming language known for its simplicity and readability."
            },
            {
                "question": "Which keyword is used to define a function in Python?",
                "options": [
                    "A) def",
                    "B) function",
                    "C) define",
                    "D) func"
                ],
                "correct_answer": "A",
                "explanation": "The 'def' keyword is used to define functions in Python."
            }
        ],
        "Web Development": [
            {
                "question": "What does HTML stand for?",
                "options": [
                    "A) HyperText Markup Language",
                    "B) High Tech Modern Language",
                    "C) Home Tool Markup Language",
                    "D) Hyperlink and Text Markup Language"
                ],
                "correct_answer": "A",
                "explanation": "HTML stands for HyperText Markup Language, used for creating web pages."
            }
        ],
        "Data Science": [
            {
                "question": "What is data science primarily used for?",
                "options": [
                    "A) Extracting insights from data",
                    "B) Creating websites",
                    "C) Building mobile apps",
                    "D) Writing documents"
                ],
                "correct_answer": "A", 
                "explanation": "Data science is primarily used for extracting insights and knowledge from data."
            }
        ]
    }
    
    # Get questions for the topic or use general questions
    topic_questions = fallback_questions.get(topic, fallback_questions["Python Programming"])
    
    # Repeat questions if needed
    questions = []
    for i in range(num_questions):
        question_idx = i % len(topic_questions)
        question = topic_questions[question_idx].copy()
        if i >= len(topic_questions):
            question["question"] = f"Question {i+1}: {question['question']}"
        questions.append(question)
    
    return questions

def show_quiz_interface():
    """Show interactive MCQ quiz interface"""
    
    st.subheader("🧪 Interactive Knowledge Quiz")
    
    # Initialize quiz state
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = {
            "questions": [],
            "current_question": 0,
            "score": 0,
            "answers": [],
            "quiz_started": False,
            "quiz_completed": False
        }
    
    # Quiz setup section
    if not st.session_state.quiz_state["quiz_started"]:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            topics = [
                "Python Programming",
                "Data Science",
                "Machine Learning", 
                "Web Development",
                "General Knowledge",
                "Current Affairs"
            ]
            selected_topic = st.selectbox("Choose Quiz Topic", topics)
        
        with col2:
            difficulty = st.select_slider("Difficulty Level", ["Beginner", "Intermediate", "Advanced"])
        
        with col3:
            num_questions = st.select_slider("Number of Questions", [3, 5, 7, 10])
        
        st.markdown("---")
        
        # Document upload for quiz generation
        uploaded_file = st.file_uploader(
            "📄 Upload Document (Optional)",
            type=['pdf', 'txt', 'docx'],
            help="Upload a document to generate quiz questions from its content"
        )
        
        if uploaded_file:
            st.success(f"📄 Document uploaded: {uploaded_file.name}")
            st.info("Quiz questions will be generated based on your document content!")
        
        if st.button("🎯 Start Quiz", type="primary", use_container_width=True):
            with st.spinner("🎓 Generating interactive quiz questions..."):
                # Process document content if uploaded
                document_content = ""
                if uploaded_file:
                    try:
                        # Upload document to backend for processing
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        upload_response = api_client.upload_document("guru", files)
                        
                        if upload_response and "extracted_text" in upload_response:
                            document_content = upload_response["extracted_text"]
                            # Truncate if too long (keep first 2000 characters for quiz generation)
                            if len(document_content) > 2000:
                                document_content = document_content[:2000] + "..."
                            st.success(f"✅ Document processed successfully! Extracted {len(document_content)} characters.")
                        elif upload_response and "document_id" in upload_response:
                            st.warning("⚠️ Document uploaded but text extraction not available in response. Using general questions.")
                        else:
                            st.error("❌ Document upload failed. Using general questions.")
                    except Exception as e:
                        st.error(f"❌ Error processing document: {str(e)}")
                        document_content = ""
                
                # Generate MCQ questions
                if document_content:
                    content_context = f"based on this document content:\n\n{document_content}\n\nGenerate questions"
                    st.info("🎯 Generating questions from your document content...")
                    
                    # Generate questions directly from document content
                    questions_data = generate_questions_from_content(document_content, num_questions, difficulty)
                    
                elif uploaded_file:
                    content_context = f"based on the uploaded document '{uploaded_file.name}'"
                    st.warning("⚠️ Using general questions since document processing failed.")
                    questions_data = get_fallback_questions(selected_topic, num_questions)
                else:
                    content_context = f"on {selected_topic}"
                    questions_data = get_fallback_questions(selected_topic, num_questions)
                
                # Store quiz data
                st.session_state.quiz_state.update({
                    "questions": questions_data,
                    "current_question": 0,
                    "score": 0,
                    "answers": [],
                    "quiz_started": True,
                    "quiz_completed": False,
                    "topic": selected_topic,
                    "difficulty": difficulty
                })
                
                st.success(f"✅ Generated {len(questions_data)} questions!")
                st.rerun()
    
    # Quiz in progress
    elif st.session_state.quiz_state["quiz_started"] and not st.session_state.quiz_state["quiz_completed"]:
        quiz_state = st.session_state.quiz_state
        current_q = quiz_state["current_question"]
        total_q = len(quiz_state["questions"])
        
        # Progress bar
        progress = (current_q) / total_q
        st.progress(progress, text=f"Question {current_q + 1} of {total_q}")
        
        # Question display
        if current_q < total_q:
            question_data = quiz_state["questions"][current_q]
            
            st.markdown(f"### 📝 Question {current_q + 1}")
            st.markdown(f"**{question_data['question']}**")
            
            # MCQ options
            selected_option = st.radio(
                "Choose your answer:",
                question_data["options"],
                key=f"question_{current_q}",
                index=None
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                if st.button("✅ Submit Answer", type="primary", disabled=selected_option is None):
                    # Check answer
                    correct_answer = question_data["correct_answer"]
                    user_answer = selected_option[0] if selected_option else None
                    
                    is_correct = user_answer == correct_answer
                    
                    if is_correct:
                        st.success(f"✅ Correct! {question_data['explanation']}")
                        quiz_state["score"] += 1
                    else:
                        st.error(f"❌ Incorrect. The correct answer is {correct_answer}.")
                        st.info(f"💡 {question_data['explanation']}")
                    
                    quiz_state["answers"].append({
                        "question": question_data["question"],
                        "user_answer": user_answer,
                        "correct_answer": correct_answer,
                        "is_correct": is_correct
                    })
                    
                    time.sleep(2)  # Show feedback briefly
                    
                    # Move to next question
                    quiz_state["current_question"] += 1
                    
                    if quiz_state["current_question"] >= total_q:
                        quiz_state["quiz_completed"] = True
                    
                    st.rerun()
    
    # Quiz completed
    else:
        quiz_state = st.session_state.quiz_state
        score = quiz_state["score"]
        total = len(quiz_state["questions"])
        percentage = (score / total) * 100
        
        st.markdown("## 🎉 Quiz Completed!")
        
        # Score display
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Score", f"{score}/{total}")
        with col2:
            st.metric("Percentage", f"{percentage:.1f}%")
        with col3:
            if percentage >= 80:
                st.metric("Grade", "🏆 Excellent")
            elif percentage >= 60:
                st.metric("Grade", "👍 Good")
            else:
                st.metric("Grade", "📚 Needs Improvement")
        
        # Detailed results
        with st.expander("📊 Detailed Results", expanded=True):
            for i, answer in enumerate(quiz_state["answers"]):
                if answer["is_correct"]:
                    st.success(f"Q{i+1}: ✅ Correct")
                else:
                    st.error(f"Q{i+1}: ❌ Wrong (Correct: {answer['correct_answer']})")
        
        # Reset quiz
        if st.button("🔄 Take Another Quiz", type="primary"):
            st.session_state.quiz_state = {
                "questions": [],
                "current_question": 0,
                "score": 0,
                "answers": [],
                "quiz_started": False,
                "quiz_completed": False
            }
            st.rerun()

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
    
    # Voice input section
    if MIC_RECORDER_AVAILABLE:
        st.markdown("### 🎤 Voice Input")
        voice_input = mic_recorder(
            start_prompt="🎤 Ask Guru (Voice)",
            stop_prompt="⏹️ Stop Recording", 
            just_once=False,
            use_container_width=True,
            callback=None,
            args=(),
            kwargs={},
            key=f"guru_voice_input"
        )
        
        # Process voice input
        if voice_input and voice_input.get('bytes'):
            st.success("🎵 Voice recorded! Processing...")
            st.info("🔄 Voice transcription feature coming soon!")
    else:
        st.info("🎤 Install voice packages to enable speech input")
    
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
        # Add user message to conversation history
        session_manager.add_message("guru", "user", user_input)
        
        with st.spinner("🎓 Guru is preparing a comprehensive answer..."):
            # Get current session for conversation continuity
            current_session_id = session_manager.get_session_id("guru")
            
            response = api_client.send_chat_message(
                user_input,  # Send original message, not modified prompt
                "guru",
                session_manager.get_user_id(),
                current_session_id
            )
        
        if response and "response" in response and not response.get("error", False):
            session_manager.add_message("guru", "assistant", response["response"])
            
            # Generate voice with educational tone
            if session_manager.get_preference("voice_enabled", True):
                audio_data = api_client.generate_voice(response["response"], "guru")
                if audio_data:
                    auto_play = session_manager.get_preference("auto_play", True)
                    audio_manager.play_audio(audio_data, auto_play)
        else:
            error_msg = "I'm having some technical difficulties. Please try rephrasing your question."
            session_manager.add_message("guru", "assistant", error_msg)
        
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
    
    # Voice Settings
    with st.expander("🎵 Voice Settings", expanded=False):
        voice_enabled = st.checkbox(
            "🔊 Enable Voice Responses",
            value=session_manager.get_preference("voice_enabled", True),
            key="guru_voice_enabled"
        )
        session_manager.set_preference("voice_enabled", voice_enabled)
        
        if voice_enabled:
            auto_play = st.checkbox(
                "🔄 Auto-play Responses", 
                value=session_manager.get_preference("auto_play", True),
                key="guru_auto_play",
                help="Automatically play voice when Guru responds"
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
