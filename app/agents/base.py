from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.chat_models.base import BaseChatModel
from app.core.config import settings
from app.llm.llm_factory import LLMFactory


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(self, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self.llm = self._initialize_llm()
        self.system_prompt = self._get_system_prompt()
    
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize the language model using the LLM Factory"""
        model_name = self.config.get("model", "gpt-4o")
        temperature = self.config.get("temperature", 0.7)
        
        # Use LLM Factory to get the appropriate LLM based on available credentials
        return LLMFactory.create_llm(
            model_name=model_name,
            temperature=temperature,
            config=self.config
        )
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user message and return response"""
        pass
    
    def _build_messages(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> List[BaseMessage]:
        """Build message list for the LLM"""
        messages = [SystemMessage(content=self.system_prompt)]
        
        # Add context if provided
        if context and context.get("conversation_history"):
            for msg in context["conversation_history"]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        return messages


class ResearchAgent(BaseAgent):
    """Agent specialized in research and information gathering"""
    
    def _get_system_prompt(self) -> str:
        return """You are a research specialist AI agent. Your role is to:
        1. Analyze research questions and break them down into components
        2. Provide comprehensive, well-structured research findings
        3. Cite sources and provide evidence-based information
        4. Suggest additional areas for investigation
        5. Present information in a clear, academic format
        
        Always be thorough, accurate, and cite your sources when possible."""
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process research-related queries"""
        messages = self._build_messages(message, context)
        
        # Add research-specific context
        research_context = """
        Focus on providing:
        - Factual, evidence-based information
        - Multiple perspectives on the topic
        - Recent developments and trends
        - Reliable sources and references
        """
        
        messages.insert(1, SystemMessage(content=research_context))
        
        response = await self.llm.ainvoke(messages)
        return response.content


class CreativeAgent(BaseAgent):
    """Agent specialized in creative tasks and content generation"""
    
    def _get_system_prompt(self) -> str:
        return """You are a creative AI agent specialized in:
        1. Creative writing and storytelling
        2. Content creation and marketing copy
        3. Brainstorming and ideation
        4. Creative problem-solving
        5. Artistic and design suggestions
        
        Be imaginative, engaging, and help users explore creative possibilities."""
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process creative tasks"""
        messages = self._build_messages(message, context)
        
        creative_context = """
        Approach this creatively:
        - Think outside the box
        - Provide multiple creative options
        - Be engaging and inspiring
        - Consider emotional impact
        """
        
        messages.insert(1, SystemMessage(content=creative_context))
        
        response = await self.llm.ainvoke(messages)
        return response.content


class CodingAgent(BaseAgent):
    """Agent specialized in programming and technical tasks"""
    
    def _get_system_prompt(self) -> str:
        return """You are a senior software engineer AI agent. Your expertise includes:
        1. Writing clean, efficient code in multiple languages
        2. Code review and optimization
        3. Architecture and design patterns
        4. Debugging and troubleshooting
        5. Best practices and modern development techniques
        
        Always provide working, well-documented code with explanations."""
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process coding-related tasks"""
        messages = self._build_messages(message, context)
        
        coding_context = """
        For coding tasks:
        - Write production-ready code
        - Include proper error handling
        - Add helpful comments
        - Suggest best practices
        - Consider security and performance
        """
        
        messages.insert(1, SystemMessage(content=coding_context))
        
        response = await self.llm.ainvoke(messages)
        return response.content


class GeneralAgent(BaseAgent):
    """General-purpose conversational agent"""
    
    def _get_system_prompt(self) -> str:
        return """You are a helpful, knowledgeable AI assistant. You can:
        1. Answer questions on a wide range of topics
        2. Provide explanations and tutorials
        3. Help with analysis and decision-making
        4. Offer suggestions and recommendations
        5. Engage in friendly, informative conversations
        
        Be helpful, accurate, and personable in your responses."""
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process general conversational messages"""
        messages = self._build_messages(message, context)
        response = await self.llm.ainvoke(messages)
        return response.content


# Agent factory
AGENT_TYPES = {
    "research": ResearchAgent,
    "creative": CreativeAgent,
    "coding": CodingAgent,
    "general": GeneralAgent,
}


def create_agent(agent_type: str, name: str, description: str, config: Optional[Dict[str, Any]] = None) -> BaseAgent:
    """Factory function to create agents"""
    agent_class = AGENT_TYPES.get(agent_type)
    if not agent_class:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return agent_class(name=name, description=description, config=config)
