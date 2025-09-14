"""
Voice Command Processor

Natural language processing for voice commands in Hindi and English
with support for agent switching, actions, and contextual understanding.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class VoiceCommand(BaseModel):
    """Parsed voice command structure"""
    command_type: str  # 'agent_switch', 'action', 'question', 'greeting'
    action: str
    parameters: Dict[str, Any] = {}
    target_agent: Optional[str] = None
    confidence: float = 0.0
    original_text: str = ""
    language: str = "hi-IN"

class VoiceCommandProcessor:
    """
    Natural Language Processing for voice commands
    """
    
    def __init__(self):
        self.command_patterns = self._initialize_command_patterns()
        self.agent_keywords = self._initialize_agent_keywords()
        self.action_keywords = self._initialize_action_keywords()
        
    def _initialize_command_patterns(self) -> Dict[str, List[str]]:
        """Initialize command patterns for different languages"""
        return {
            # Agent switching commands
            "agent_switch": [
                # Hindi patterns
                r"(?:मित्र|mitra)\s*(?:से|ko|se)\s*(?:बात|बोल|speak|talk)",
                r"(?:गुरु|guru)\s*(?:से|ko|se)\s*(?:बात|help|मदद|सीख)",
                r"(?:परीक्षक|parikshak)\s*(?:से|ko|se)\s*(?:interview|साक्षात्कार)",
                
                # English patterns  
                r"(?:talk to|switch to|connect (?:me )?with|speak with)\s*(mitra|guru|parikshak)",
                r"(?:i want to|let me)\s*(?:talk to|speak with|chat with)\s*(mitra|guru|parikshak)",
                r"(?:open|start|begin)\s*(mitra|guru|parikshak)(?:\s*(?:agent|chat|session))?",
                
                # Mixed language patterns
                r"(?:mitra|guru|parikshak)\s*(?:खोल|start|begin|चालू)",
                r"(?:से|with|के साथ)\s*(?:mitra|guru|parikshak)"
            ],
            
            # Action commands
            "action": [
                # Learning actions (Guru)
                r"(?:सीखना|learn|teach|explain|समझा)\s*(?:है|चाहता|want|about)\s*(.+)",
                r"(?:क्या है|what is|tell me about|बता)\s*(.+)",
                r"(?:कैसे|how)\s*(?:करते|करना|to|do)\s*(.+)",
                
                # Interview actions (Parikshak)
                r"(?:interview|साक्षात्कार)\s*(?:practice|अभ्यास|start|शुरू)",
                r"(?:mock|प्रैक्टिस)\s*(?:interview|टेस्ट)",
                r"(?:resume|बायोडाटा)\s*(?:check|देख|review)",
                
                # Emotional support (Mitra)
                r"(?:मुझे|i am|i feel|मैं)\s*(?:sad|खुश|दुखी|happy|परेशान|worried)",
                r"(?:help|मदद)\s*(?:चाहिए|need|required)",
                r"(?:बात|talk|chat)\s*(?:करना|want to|चाहता)"
            ],
            
            # Questions
            "question": [
                r"(?:क्या|what|कैसे|how|कब|when|कहाँ|where|क्यों|why)\s*(.+)",
                r"(?:बता|tell)\s*(?:मुझे|me)\s*(.+)",
                r"(?:explain|समझा)\s*(.+)"
            ],
            
            # Greetings
            "greeting": [
                r"(?:नमस्ते|नमस्कार|hello|hi|hey)\s*(?:mitra|guru|parikshak)?",
                r"(?:good|शुभ)\s*(?:morning|afternoon|evening|सुबह|दोपहर|शाम)",
                r"(?:कैसे|how)\s*(?:हो|are you|हैं)"
            ]
        }
    
    def _initialize_agent_keywords(self) -> Dict[str, List[str]]:
        """Initialize keywords for agent identification"""
        return {
            "mitra": [
                # Hindi
                "मित्र", "दोस्त", "साथी", "friend",
                # English
                "mitra", "friend", "companion", "buddy",
                # Context words
                "emotional", "support", "feeling", "mood", "दुख", "खुशी"
            ],
            "guru": [
                # Hindi  
                "गुरु", "शिक्षक", "अध्यापक", "teacher",
                # English
                "guru", "teacher", "mentor", "tutor",
                # Context words
                "learn", "study", "education", "knowledge", "सीख", "पढ़", "ज्ञान"
            ],
            "parikshak": [
                # Hindi
                "परीक्षक", "interviewer", "नियोक्ता",
                # English  
                "parikshak", "interviewer", "examiner", "assessor",
                # Context words
                "interview", "job", "career", "resume", "साक्षात्कार", "नौकरी"
            ]
        }
    
    def _initialize_action_keywords(self) -> Dict[str, List[str]]:
        """Initialize action keywords"""
        return {
            "learn": ["सीख", "learn", "study", "पढ़", "समझ", "understand"],
            "practice": ["अभ्यास", "practice", "exercise", "प्रैक्टिस"],
            "interview": ["interview", "साक्षात्कार", "mock", "प्रैक्टिस"],
            "help": ["help", "मदद", "assistance", "सहायता"],
            "explain": ["explain", "समझा", "clarify", "स्पष्ट"],
            "chat": ["बात", "chat", "talk", "conversation", "बातचीत"]
        }
    
    async def process_voice_command(
        self,
        transcribed_text: str,
        language: str = "hi-IN",
        confidence: float = 0.0
    ) -> List[VoiceCommand]:
        """
        Process voice command and extract actionable information
        
        Args:
            transcribed_text: Transcribed text from speech
            language: Language of the text
            confidence: Transcription confidence
            
        Returns:
            List of parsed voice commands
        """
        text = transcribed_text.strip().lower()
        commands = []
        
        try:
            # Detect agent switching commands
            agent_command = await self._detect_agent_switch(text, language, confidence)
            if agent_command:
                commands.append(agent_command)
            
            # Detect action commands
            action_command = await self._detect_action_command(text, language, confidence)
            if action_command:
                commands.append(action_command)
            
            # Detect questions
            question_command = await self._detect_question(text, language, confidence)
            if question_command:
                commands.append(question_command)
            
            # Detect greetings
            greeting_command = await self._detect_greeting(text, language, confidence)
            if greeting_command:
                commands.append(greeting_command)
            
            # If no specific commands detected, treat as general chat
            if not commands:
                commands.append(VoiceCommand(
                    command_type="chat",
                    action="general_chat",
                    parameters={"text": transcribed_text},
                    confidence=confidence * 0.7,  # Lower confidence for general chat
                    original_text=transcribed_text,
                    language=language
                ))
            
            logger.debug(f"Processed {len(commands)} commands from: '{transcribed_text}'")
            return commands
            
        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            # Return fallback command
            return [VoiceCommand(
                command_type="error",
                action="processing_error",
                parameters={"error": str(e), "text": transcribed_text},
                confidence=0.0,
                original_text=transcribed_text,
                language=language
            )]
    
    async def _detect_agent_switch(
        self,
        text: str,
        language: str,
        confidence: float
    ) -> Optional[VoiceCommand]:
        """Detect agent switching commands"""
        
        for pattern in self.command_patterns["agent_switch"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract target agent from match
                target_agent = None
                
                # Check for agent names in the match
                for agent, keywords in self.agent_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in text.lower():
                            target_agent = agent
                            break
                    if target_agent:
                        break
                
                if target_agent:
                    return VoiceCommand(
                        command_type="agent_switch",
                        action="switch_agent",
                        target_agent=target_agent,
                        parameters={"requested_agent": target_agent},
                        confidence=confidence * 0.9,
                        original_text=text,
                        language=language
                    )
        
        return None
    
    async def _detect_action_command(
        self,
        text: str,
        language: str,
        confidence: float
    ) -> Optional[VoiceCommand]:
        """Detect action commands"""
        
        for pattern in self.command_patterns["action"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Determine action type based on keywords
                action_type = "general_action"
                parameters = {}
                
                # Extract parameters from match groups
                if match.groups():
                    parameters["subject"] = match.group(1).strip()
                
                # Classify action based on keywords
                for action, keywords in self.action_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in text.lower():
                            action_type = action
                            break
                    if action_type != "general_action":
                        break
                
                return VoiceCommand(
                    command_type="action",
                    action=action_type,
                    parameters=parameters,
                    confidence=confidence * 0.8,
                    original_text=text,
                    language=language
                )
        
        return None
    
    async def _detect_question(
        self,
        text: str,
        language: str,
        confidence: float
    ) -> Optional[VoiceCommand]:
        """Detect question patterns"""
        
        for pattern in self.command_patterns["question"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                question_type = "general_question"
                parameters = {"question": text}
                
                # Extract question subject if available
                if match.groups():
                    parameters["subject"] = match.group(1).strip()
                
                # Classify question type
                if any(word in text.lower() for word in ["क्या है", "what is", "define"]):
                    question_type = "definition"
                elif any(word in text.lower() for word in ["कैसे", "how to", "how do"]):
                    question_type = "procedure"
                elif any(word in text.lower() for word in ["क्यों", "why", "reason"]):
                    question_type = "explanation"
                
                return VoiceCommand(
                    command_type="question",
                    action=question_type,
                    parameters=parameters,
                    confidence=confidence * 0.85,
                    original_text=text,
                    language=language
                )
        
        return None
    
    async def _detect_greeting(
        self,
        text: str,
        language: str,
        confidence: float
    ) -> Optional[VoiceCommand]:
        """Detect greeting patterns"""
        
        for pattern in self.command_patterns["greeting"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                greeting_type = "general_greeting"
                
                # Classify greeting type
                if any(word in text.lower() for word in ["नमस्ते", "hello", "hi"]):
                    greeting_type = "hello"
                elif any(word in text.lower() for word in ["good morning", "शुभ सुबह"]):
                    greeting_type = "good_morning"
                elif any(word in text.lower() for word in ["good evening", "शुभ शाम"]):
                    greeting_type = "good_evening"
                elif any(word in text.lower() for word in ["कैसे हो", "how are you"]):
                    greeting_type = "how_are_you"
                
                return VoiceCommand(
                    command_type="greeting",
                    action=greeting_type,
                    parameters={"greeting_text": text},
                    confidence=confidence * 0.9,
                    original_text=text,
                    language=language
                )
        
        return None
    
    async def get_command_suggestions(
        self,
        current_agent: str = "mitra",
        language: str = "hi-IN"
    ) -> List[Dict[str, str]]:
        """
        Get suggested voice commands for current context
        
        Args:
            current_agent: Currently active agent
            language: Preferred language
            
        Returns:
            List of command suggestions
        """
        suggestions = []
        
        if language.startswith("hi"):
            # Hindi suggestions
            base_suggestions = [
                {"text": "मित्र से बात करो", "description": "Switch to Mitra for emotional support"},
                {"text": "गुरु से मदद चाहिए", "description": "Switch to Guru for learning help"},
                {"text": "परीक्षक से interview practice", "description": "Switch to Parikshak for interview practice"},
                {"text": "नमस्ते", "description": "General greeting"},
                {"text": "मुझे खुशी हो रही है", "description": "Express emotions (for Mitra)"},
                {"text": "मुझे कुछ सीखना है", "description": "Request learning (for Guru)"},
                {"text": "interview practice शुरू करो", "description": "Start interview practice (for Parikshak)"}
            ]
        else:
            # English suggestions
            base_suggestions = [
                {"text": "Talk to Mitra", "description": "Switch to Mitra for emotional support"},
                {"text": "Help me learn something", "description": "Switch to Guru for learning"},
                {"text": "Start interview practice", "description": "Switch to Parikshak for interviews"},
                {"text": "Hello there", "description": "General greeting"},
                {"text": "I'm feeling happy today", "description": "Express emotions (for Mitra)"},
                {"text": "Explain this concept", "description": "Request explanation (for Guru)"},
                {"text": "Practice mock interview", "description": "Interview practice (for Parikshak)"}
            ]
        
        # Add agent-specific suggestions
        agent_specific = {
            "mitra": [
                {"text": "मुझे दुख हो रहा है" if language.startswith("hi") else "I'm feeling sad", 
                 "description": "Express sadness for emotional support"},
                {"text": "आज मेरा दिन अच्छा नहीं रहा" if language.startswith("hi") else "I had a bad day",
                 "description": "Share daily feelings"}
            ],
            "guru": [
                {"text": "यह कैसे काम करता है" if language.startswith("hi") else "How does this work",
                 "description": "Ask for explanations"},
                {"text": "मुझे प्रोग्रामिंग सीखनी है" if language.startswith("hi") else "I want to learn programming",
                 "description": "Request learning sessions"}
            ],
            "parikshak": [
                {"text": "मेरे resume को check करो" if language.startswith("hi") else "Check my resume",
                 "description": "Resume review request"},
                {"text": "behavioral interview practice" if language.startswith("hi") else "Practice behavioral interview",
                 "description": "Specific interview type practice"}
            ]
        }
        
        suggestions.extend(base_suggestions)
        if current_agent in agent_specific:
            suggestions.extend(agent_specific[current_agent])
        
        return suggestions
    
    async def validate_command(self, command: VoiceCommand) -> bool:
        """
        Validate if a voice command is properly formed and actionable
        
        Args:
            command: Voice command to validate
            
        Returns:
            True if command is valid
        """
        try:
            # Basic validation
            if not command.command_type or not command.action:
                return False
            
            # Check confidence threshold
            if command.confidence < 0.3:  # Very low confidence
                return False
            
            # Command-specific validation
            if command.command_type == "agent_switch":
                return command.target_agent in ["mitra", "guru", "parikshak"]
            
            elif command.command_type == "action":
                return command.action in self.action_keywords.keys()
            
            elif command.command_type in ["question", "greeting", "chat"]:
                return len(command.original_text.strip()) > 0
            
            return True
            
        except Exception as e:
            logger.error(f"Command validation error: {e}")
            return False
    
    async def get_command_response_template(
        self,
        command: VoiceCommand,
        current_agent: str
    ) -> Dict[str, Any]:
        """
        Get response template for a voice command
        
        Args:
            command: Processed voice command
            current_agent: Currently active agent
            
        Returns:
            Response template with suggested actions
        """
        template = {
            "action_required": False,
            "response_type": "text",
            "suggested_response": "",
            "follow_up_actions": []
        }
        
        try:
            if command.command_type == "agent_switch" and command.target_agent:
                template.update({
                    "action_required": True,
                    "response_type": "agent_switch",
                    "target_agent": command.target_agent,
                    "suggested_response": f"Switching to {command.target_agent.title()}...",
                    "follow_up_actions": ["switch_agent", "send_greeting"]
                })
            
            elif command.command_type == "greeting":
                greetings = {
                    "mitra": "नमस्ते! मैं मित्र हूं। आज आप कैसा महसूस कर रहे हैं?",
                    "guru": "नमस्ते! मैं गुरु हूं। आज आप क्या सीखना चाहते हैं?",
                    "parikshak": "नमस्ते! मैं परीक्षक हूं। interview practice के लिए तैयार हैं?"
                }
                
                template.update({
                    "response_type": "greeting",
                    "suggested_response": greetings.get(current_agent, "नमस्ते! कैसे हैं आप?"),
                    "follow_up_actions": ["wait_for_response"]
                })
            
            elif command.command_type == "action":
                template.update({
                    "action_required": True,
                    "response_type": "action_response",
                    "suggested_response": f"I'll help you with {command.action}",
                    "follow_up_actions": ["process_action", "provide_assistance"]
                })
            
            elif command.command_type == "question":
                template.update({
                    "response_type": "question_response", 
                    "suggested_response": "Let me help you with that question.",
                    "follow_up_actions": ["research_answer", "provide_explanation"]
                })
            
        except Exception as e:
            logger.error(f"Error generating response template: {e}")
        
        return template