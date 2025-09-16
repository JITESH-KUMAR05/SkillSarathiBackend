"""
Advanced RAG System with Personalized Memory
===========================================

Features:
- User-specific knowledge bases with conversation history
- Vector embeddings for semantic search  
- Context evolution tracking
- Document upload and processing
- Memory consolidation and retrieval
"""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import numpy as np
from pathlib import Path

# Vector store and embeddings
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Document processing
import PyPDF2
import docx
from io import BytesIO

# Database
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.database.models import User, Document, Conversation

logger = logging.getLogger(__name__)

class AdvancedRAGSystem:
    """Production-grade RAG system with personalized memory and context evolution"""
    
    def __init__(self):
        # Initialize ChromaDB for vector storage
        self.chroma_client = chromadb.PersistentClient(
            path="./data/chromadb",
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize sentence transformer for embeddings
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Collections for different types of memory
        self.user_collections = {}  # user_id -> collection
        self.global_collection = self._get_or_create_collection("global_knowledge")
        
        # Memory consolidation settings
        self.max_memory_items = 1000
        self.consolidation_threshold = 100
        
    def _get_or_create_collection(self, collection_name: str):
        """Get or create a ChromaDB collection"""
        try:
            return self.chroma_client.get_collection(collection_name)
        except Exception:
            return self.chroma_client.create_collection(
                name=collection_name,
                metadata={"description": f"Collection for {collection_name}"}
            )
    
    def _get_user_collection(self, user_id: str):
        """Get or create user-specific collection"""
        if user_id not in self.user_collections:
            collection_name = f"user_{user_id}"
            self.user_collections[user_id] = self._get_or_create_collection(collection_name)
        return self.user_collections[user_id]
    
    async def add_conversation_memory(
        self, 
        user_id: str, 
        user_message: str, 
        agent_response: str,
        agent_type: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Add conversation to user's personalized memory"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Create conversation memory entry
            conversation_text = f"User: {user_message}\n{agent_type.title()}: {agent_response}"
            
            # Generate embedding
            embedding = self.embedding_model.encode(conversation_text).tolist()
            
            # Create unique ID
            memory_id = f"conv_{user_id}_{uuid.uuid4()}"
            
            # Metadata
            metadata = {
                "type": "conversation",
                "user_id": user_id,
                "agent_type": agent_type,
                "timestamp": datetime.now().isoformat(),
                "user_message": user_message,
                "agent_response": agent_response,
                "context": json.dumps(context or {})
            }
            
            # Add to collection
            collection.add(
                embeddings=[embedding],
                documents=[conversation_text],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            logger.info(f"Added conversation memory for user {user_id}")
            
            # Check if consolidation is needed
            await self._check_memory_consolidation(user_id)
            
        except Exception as e:
            logger.error(f"Error adding conversation memory: {e}")
    
    async def add_document_knowledge(
        self,
        user_id: str,
        document_content: str,
        document_name: str,
        document_type: str = "upload"
    ):
        """Add document knowledge to user's memory"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Split document into chunks for better retrieval
            chunks = self._split_document(document_content)
            
            embeddings = []
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.embedding_model.encode(chunk).tolist()
                embeddings.append(embedding)
                documents.append(chunk)
                
                # Metadata
                metadata = {
                    "type": "document",
                    "user_id": user_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "chunk_index": i,
                    "timestamp": datetime.now().isoformat()
                }
                metadatas.append(metadata)
                
                # ID
                chunk_id = f"doc_{user_id}_{uuid.uuid4()}"
                ids.append(chunk_id)
            
            # Add all chunks to collection
            collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added document '{document_name}' to user {user_id} memory ({len(chunks)} chunks)")
            
        except Exception as e:
            logger.error(f"Error adding document knowledge: {e}")
    
    def _split_document(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split document into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
    
    async def search_user_memory(
        self,
        user_id: str,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search user's personalized memory"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Build where clause for filtering
            where_clause = {"user_id": user_id}
            if memory_types:
                where_clause["type"] = {"$in": memory_types}
            
            # Search collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    result = {
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "relevance_score": 1 - results["distances"][0][i],  # Convert distance to similarity
                        "type": results["metadatas"][0][i].get("type"),
                        "timestamp": results["metadatas"][0][i].get("timestamp")
                    }
                    formatted_results.append(result)
            
            logger.info(f"Found {len(formatted_results)} relevant memories for user {user_id}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching user memory: {e}")
            return []
    
    async def get_context_for_agent(
        self,
        user_id: str,
        current_message: str,
        agent_type: str,
        context_limit: int = 3
    ) -> Dict[str, Any]:
        """Get relevant context for agent response"""
        try:
            # Search recent conversations with this agent
            recent_conversations = await self.search_user_memory(
                user_id=user_id,
                query=current_message,
                memory_types=["conversation"],
                limit=context_limit
            )
            
            # Filter for specific agent if needed
            agent_conversations = [
                conv for conv in recent_conversations
                if conv["metadata"].get("agent_type") == agent_type
            ]
            
            # Search relevant documents
            document_context = await self.search_user_memory(
                user_id=user_id,
                query=current_message,
                memory_types=["document"],
                limit=2
            )
            
            # Build context summary
            context = {
                "recent_conversations": agent_conversations[:2],
                "relevant_documents": document_context,
                "user_id": user_id,
                "agent_type": agent_type,
                "context_generated_at": datetime.now().isoformat()
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for agent: {e}")
            return {"recent_conversations": [], "relevant_documents": []}
    
    async def _check_memory_consolidation(self, user_id: str):
        """Check if memory consolidation is needed"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Get collection count
            count = collection.count()
            
            if count > self.consolidation_threshold:
                await self._consolidate_user_memory(user_id)
                
        except Exception as e:
            logger.error(f"Error checking memory consolidation: {e}")
    
    async def _consolidate_user_memory(self, user_id: str):
        """Consolidate user memory by removing old, less relevant items"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Get all items older than 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # This is a simplified consolidation - in production, you'd want more sophisticated logic
            logger.info(f"Memory consolidation needed for user {user_id}")
            
            # For now, just log the need for consolidation
            # Full implementation would involve:
            # 1. Analyzing conversation patterns
            # 2. Identifying frequently accessed memories
            # 3. Summarizing old conversations
            # 4. Removing redundant information
            
        except Exception as e:
            logger.error(f"Error consolidating memory: {e}")
    
    async def process_uploaded_file(
        self,
        user_id: str,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> bool:
        """Process uploaded file and add to user's knowledge base"""
        try:
            text_content = ""
            
            # Extract text based on file type
            if content_type == "application/pdf":
                text_content = self._extract_pdf_text(file_content)
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                text_content = self._extract_docx_text(file_content)
            elif content_type == "text/plain":
                text_content = file_content.decode('utf-8')
            else:
                logger.warning(f"Unsupported file type: {content_type}")
                return False
            
            if text_content.strip():
                await self.add_document_knowledge(
                    user_id=user_id,
                    document_content=text_content,
                    document_name=filename,
                    document_type="upload"
                )
                return True
            else:
                logger.warning(f"No text content extracted from {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}")
            return False
    
    def _extract_pdf_text(self, file_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_docx_text(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            doc_file = BytesIO(file_content)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            return ""
    
    async def get_user_knowledge_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's knowledge base"""
        try:
            collection = self._get_user_collection(user_id)
            
            # Get all metadata to analyze
            all_items = collection.get(
                include=["metadatas"]
            )
            
            if not all_items["metadatas"]:
                return {
                    "total_items": 0,
                    "conversations": 0,
                    "documents": 0,
                    "document_names": [],
                    "agents_interacted": []
                }
            
            # Analyze metadata
            conversations = 0
            documents = 0
            document_names = set()
            agents_interacted = set()
            
            for metadata in all_items["metadatas"]:
                if metadata.get("type") == "conversation":
                    conversations += 1
                    agent_type = metadata.get("agent_type")
                    if agent_type:
                        agents_interacted.add(agent_type)
                elif metadata.get("type") == "document":
                    documents += 1
                    doc_name = metadata.get("document_name")
                    if doc_name:
                        document_names.add(doc_name)
            
            return {
                "total_items": len(all_items["metadatas"]),
                "conversations": conversations,
                "documents": documents,
                "document_names": list(document_names),
                "agents_interacted": list(agents_interacted),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user knowledge summary: {e}")
            return {"total_items": 0, "error": str(e)}

# Global RAG system instance - lazy initialization
_rag_system = None

def get_rag_system() -> AdvancedRAGSystem:
    """Get or create the global RAG system instance"""
    global _rag_system
    if _rag_system is None:
        _rag_system = AdvancedRAGSystem()
    return _rag_system

# For backward compatibility, create rag_system as a callable that returns the instance
rag_system = get_rag_system

# Alias for enhanced_rag_system compatibility
advanced_rag_system = get_rag_system()
