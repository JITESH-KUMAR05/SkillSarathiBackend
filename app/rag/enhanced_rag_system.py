"""
Enhanced RAG (Retrieval Augmented Generation) System
Using ChromaDB for vector storage and retrieval
Supports multi-agent user profiling and context sharing as per project requirements
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Union
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import uuid
import json
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from app.core.config import settings


class MockEmbeddings:
    """Mock embeddings for development/testing when OpenAI API key is not available"""
    
    def embed_query(self, text: str) -> List[float]:
        """Generate mock embedding for a query"""
        # Simple hash-based mock embedding
        hash_value = hash(text)
        np.random.seed(abs(hash_value) % (2**32))
        return np.random.rand(384).tolist()  # Mock 384-dimensional embedding
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for documents"""
        return [self.embed_query(text) for text in texts]


class EnhancedRAGSystem:
    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Initialize embeddings with graceful fallback
        try:
            if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
                self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
            else:
                # Use a mock embeddings for demo/development
                print("⚠️  Using mock embeddings - set OPENAI_API_KEY for production use")
                self.embeddings = MockEmbeddings()
        except Exception as e:
            print(f"⚠️  Error initializing OpenAI embeddings: {e}")
            print("   Using mock embeddings for development")
            self.embeddings = MockEmbeddings()
            
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Initialize collections for multi-agent system
        self.documents_collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.conversations_collection = self.client.get_or_create_collection(
            name="conversations",
            metadata={"hnsw:space": "cosine"}
        )
        
        # User profiling and context collections
        self.user_profiles_collection = self.client.get_or_create_collection(
            name="user_profiles",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.interactions_collection = self.client.get_or_create_collection(
            name="agent_interactions",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Shared knowledge base for all agents
        self.shared_knowledge_collection = self.client.get_or_create_collection(
            name="shared_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_document(self, user_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a document to the user's knowledge base"""
        doc_id = str(uuid.uuid4())
        chunks = self.text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_{i}"
            
            # Get embeddings
            embedding = self.embeddings.embed_query(chunk)
            
            # Store in ChromaDB
            self.documents_collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "timestamp": datetime.utcnow().isoformat(),
                    **(metadata or {})
                }]
            )
        
        return doc_id
    
    async def search_documents(self, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents for a user"""
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.documents_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"user_id": user_id}
        )
        
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": score
            }
            for doc, meta, score in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]
    
    async def add_conversation_context(self, user_id: str, conversation_id: str, content: str):
        """Add conversation context to RAG system"""
        context_id = f"{conversation_id}_{uuid.uuid4()}"
        
        embedding = self.embeddings.embed_query(content)
        
        self.conversations_collection.add(
            ids=[context_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "user_id": user_id,
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }]
        )
    
    async def search_conversation_history(self, user_id: str, query: str, k: int = 5) -> List[str]:
        """Search conversation history for relevant context"""
        query_embedding = self.embeddings.embed_query(query)
        
        results = self.conversations_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"user_id": user_id}
        )
        
        return results['documents'][0] if results['documents'] else []
    
    # Enhanced methods for multi-agent system
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> str:
        """Create or update user profile for personalized agent interactions"""
        profile_id = f"profile_{user_id}"
        
        # Convert profile to searchable text
        profile_text = self._profile_to_text(profile_data)
        embedding = self.embeddings.embed_query(profile_text)
        
        # Store profile with metadata - ensure all values are compatible with ChromaDB
        metadata = {
            "user_id": user_id,
            "profile_type": "user_profile",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Add profile data to metadata, converting lists to strings
        for key, value in profile_data.items():
            if isinstance(value, list):
                metadata[key] = ", ".join(map(str, value))
            elif value is None:
                continue  # Skip None values
            else:
                metadata[key] = str(value)
        
        try:
            # Try to update existing profile
            self.user_profiles_collection.delete(ids=[profile_id])
        except:
            pass  # Profile doesn't exist yet
        
        self.user_profiles_collection.add(
            ids=[profile_id],
            embeddings=[embedding],
            documents=[profile_text],
            metadatas=[metadata]
        )
        
        return profile_id
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Retrieve comprehensive user profile"""
        profile_id = f"profile_{user_id}"
        
        try:
            results = self.user_profiles_collection.get(ids=[profile_id])
            if results['metadatas']:
                profile_data = results['metadatas'][0].copy()
                # Remove system fields
                for field in ['user_id', 'profile_type', 'created_at', 'last_updated']:
                    profile_data.pop(field, None)
                return profile_data
        except:
            pass
        
        return {}
    
    async def add_user_interaction(
        self, 
        user_id: str, 
        interaction: Dict[str, Any]
    ) -> str:
        """Store user interaction for learning and personalization"""
        interaction_id = str(uuid.uuid4())
        
        # Convert interaction to searchable text
        interaction_text = self._interaction_to_text(interaction)
        embedding = self.embeddings.embed_query(interaction_text)
        
        metadata = {
            "user_id": user_id,
            "interaction_id": interaction_id,
            "agent_type": interaction.get("agent", "unknown"),
            "timestamp": interaction.get("timestamp", datetime.utcnow().isoformat()),
            "interaction_type": "agent_interaction"
        }
        
        self.interactions_collection.add(
            ids=[interaction_id],
            embeddings=[embedding],
            documents=[interaction_text],
            metadatas=[metadata]
        )
        
        # Update user profile based on interaction
        await self._update_profile_from_interaction(user_id, interaction)
        
        return interaction_id
    
    async def search_user_context(
        self, 
        user_id: str, 
        query: str, 
        k: int = 5,
        include_profile: bool = True
    ) -> List[str]:
        """Search for relevant user context across all interactions and profile"""
        contexts = []
        
        # Search interaction history
        query_embedding = self.embeddings.embed_query(query)
        
        interaction_results = self.interactions_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"user_id": user_id}
        )
        
        if interaction_results['documents']:
            contexts.extend(interaction_results['documents'][0])
        
        # Include profile information if requested
        if include_profile:
            profile = await self.get_user_profile(user_id)
            if profile:
                profile_summary = self._summarize_profile(profile)
                contexts.insert(0, profile_summary)
        
        return contexts[:k]
    
    async def add_shared_knowledge(
        self, 
        content: str, 
        category: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add knowledge to shared knowledge base accessible by all agents"""
        knowledge_id = str(uuid.uuid4())
        
        # Split content into chunks for better retrieval
        chunks = self.text_splitter.split_text(content)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{knowledge_id}_{i}"
            embedding = self.embeddings.embed_query(chunk)
            
            chunk_metadata = {
                "knowledge_id": knowledge_id,
                "category": category,
                "chunk_index": i,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            self.shared_knowledge_collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[chunk_metadata]
            )
        
        return knowledge_id
    
    async def search_shared_knowledge(
        self, 
        query: str, 
        category: Optional[str] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search shared knowledge base"""
        query_embedding = self.embeddings.embed_query(query)
        
        where_clause = {}
        if category:
            where_clause["category"] = category
        
        results = self.shared_knowledge_collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where_clause if where_clause else None
        )
        
        return [
            {
                "content": doc,
                "metadata": meta,
                "score": score
            }
            for doc, meta, score in zip(
                results['documents'][0] if results['documents'] else [],
                results['metadatas'][0] if results['metadatas'] else [],
                results['distances'][0] if results['distances'] else []
            )
        ]
    
    async def get_user_interaction_summary(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get summary of user interactions over specified period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        # Get all interactions for user in time period
        all_interactions = self.interactions_collection.get(
            where={
                "user_id": user_id,
                "timestamp": {"$gte": cutoff_str}
            }
        )
        
        if not all_interactions['metadatas']:
            return {"total_interactions": 0, "agent_distribution": {}, "recent_topics": []}
        
        # Analyze interactions
        agent_counts = defaultdict(int)
        topics = []
        
        for metadata, content in zip(all_interactions['metadatas'], all_interactions['documents']):
            agent_counts[metadata.get('agent_type', 'unknown')] += 1
            topics.append(content[:100])  # First 100 chars as topic summary
        
        return {
            "total_interactions": len(all_interactions['metadatas']),
            "agent_distribution": dict(agent_counts),
            "recent_topics": topics[-10:],  # Last 10 topics
            "period_days": days
        }
    
    # Helper methods
    
    def _profile_to_text(self, profile_data: Dict[str, Any]) -> str:
        """Convert profile data to searchable text"""
        text_parts = []
        
        for key, value in profile_data.items():
            if isinstance(value, (str, int, float)):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, list):
                text_parts.append(f"{key}: {', '.join(map(str, value))}")
            elif isinstance(value, dict):
                text_parts.append(f"{key}: {json.dumps(value)}")
        
        return ". ".join(text_parts)
    
    def _interaction_to_text(self, interaction: Dict[str, Any]) -> str:
        """Convert interaction data to searchable text"""
        text_parts = [
            f"Agent: {interaction.get('agent', 'unknown')}",
            f"User message: {interaction.get('user_message', '')}",
            f"Agent response: {interaction.get('agent_response', '')}",
            f"Context: {json.dumps(interaction.get('context', {}))}"
        ]
        
        return ". ".join(text_parts)
    
    async def _update_profile_from_interaction(
        self, 
        user_id: str, 
        interaction: Dict[str, Any]
    ):
        """Update user profile based on interaction patterns"""
        current_profile = await self.get_user_profile(user_id)
        
        # Extract insights from interaction
        agent_type = interaction.get('agent', 'unknown')
        user_message = interaction.get('user_message', '').lower()
        
        # Update interaction counts
        interaction_counts = current_profile.get('interaction_counts', {})
        interaction_counts[agent_type] = interaction_counts.get(agent_type, 0) + 1
        current_profile['interaction_counts'] = interaction_counts
        
        # Extract interests and topics
        interests = current_profile.get('interests', [])
        
        # Simple keyword extraction for interests
        if 'career' in user_message or 'job' in user_message:
            if 'career development' not in interests:
                interests.append('career development')
        
        if 'interview' in user_message:
            if 'interview preparation' not in interests:
                interests.append('interview preparation')
        
        if any(tech in user_message for tech in ['python', 'javascript', 'programming', 'coding']):
            if 'technology' not in interests:
                interests.append('technology')
        
        current_profile['interests'] = interests[:10]  # Keep top 10 interests
        current_profile['last_active'] = datetime.utcnow().isoformat()
        
        # Update profile
        await self.create_user_profile(user_id, current_profile)
    
    def _summarize_profile(self, profile: Dict[str, Any]) -> str:
        """Create a concise profile summary for context"""
        summary_parts = []
        
        if 'name' in profile:
            summary_parts.append(f"Name: {profile['name']}")
        
        if 'interests' in profile and profile['interests']:
            summary_parts.append(f"Interests: {', '.join(profile['interests'][:5])}")
        
        if 'career_goal' in profile:
            summary_parts.append(f"Career goal: {profile['career_goal']}")
        
        if 'interaction_counts' in profile:
            most_used_agent = max(profile['interaction_counts'].items(), key=lambda x: x[1])
            summary_parts.append(f"Most interactions with: {most_used_agent[0]} agent")
        
        if 'preferred_language' in profile:
            summary_parts.append(f"Preferred language: {profile['preferred_language']}")
        
        return ". ".join(summary_parts)


# Global enhanced RAG instance
enhanced_rag_system = EnhancedRAGSystem()
