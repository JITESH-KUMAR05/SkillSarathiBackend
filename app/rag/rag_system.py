from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.schema import Document
from sentence_transformers import SentenceTransformer
import os
from app.core.config import settings


class RAGSystem:
    """Retrieval-Augmented Generation system for document processing"""
    
    def __init__(self):
        self.chroma_client = self._initialize_chroma()
        self.embeddings = self._initialize_embeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def _initialize_chroma(self) -> chromadb.Client:
        """Initialize ChromaDB client"""
        try:
            # Use in-memory client to avoid persistence issues during development
            return chromadb.EphemeralClient()
        except Exception as e:
            print(f"ChromaDB initialization warning: {e}")
            # Fallback to a simple client
            return chromadb.EphemeralClient()
    
    def _initialize_embeddings(self):
        """Initialize embedding model"""
        if settings.OPENAI_API_KEY:
            return OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
        else:
            # Fallback to local sentence transformer
            return SentenceTransformer('all-MiniLM-L6-v2')
    
    async def add_document(self, document_content: str, document_id: str, 
                          metadata: Optional[Dict[str, Any]] = None) -> List[str]:
        """Add a document to the vector database"""
        # Split document into chunks
        chunks = self.text_splitter.split_text(document_content)
        
        # Get or create collection
        collection_name = f"user_documents"
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception:
            collection = self.chroma_client.create_collection(collection_name)
        
        # Generate embeddings and add to collection
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            chunk_ids.append(chunk_id)
            
            # Create metadata for chunk
            chunk_metadata = {
                "document_id": document_id,
                "chunk_index": i,
                "chunk_text": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                **(metadata or {})
            }
            
            # Generate embedding
            if hasattr(self.embeddings, 'embed_documents'):
                embedding = self.embeddings.embed_documents([chunk])[0]
            else:
                embedding = self.embeddings.encode([chunk])[0].tolist()
            
            # Add to collection
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[chunk_metadata],
                ids=[chunk_id]
            )
        
        return chunk_ids
    
    async def search_documents(self, query: str, user_id: int, 
                             top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        collection_name = f"user_documents"
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
        except Exception:
            return []
        
        # Generate query embedding
        if hasattr(self.embeddings, 'embed_query'):
            query_embedding = self.embeddings.embed_query(query)
        else:
            query_embedding = self.embeddings.encode([query])[0].tolist()
        
        # Search collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id} if user_id else None
        )
        
        # Format results
        formatted_results = []
        if results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if results['distances'] else None,
                    "id": results['ids'][0][i]
                })
        
        return formatted_results
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks"""
        collection_name = f"user_documents"
        
        try:
            collection = self.chroma_client.get_collection(collection_name)
            
            # Get all chunks for this document
            results = collection.get(where={"document_id": document_id})
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                return True
            
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
        
        return False
    
    async def get_context_for_query(self, query: str, user_id: int, 
                                   max_context_length: int = 2000) -> str:
        """Get relevant context for a query"""
        results = await self.search_documents(query, user_id, top_k=5)
        
        context_parts = []
        current_length = 0
        
        for result in results:
            content = result['content']
            if current_length + len(content) <= max_context_length:
                context_parts.append(content)
                current_length += len(content)
            else:
                # Add partial content if it fits
                remaining_space = max_context_length - current_length
                if remaining_space > 100:  # Only add if meaningful amount of space
                    context_parts.append(content[:remaining_space] + "...")
                break
        
        return "\n\n".join(context_parts)


# Global RAG instance
rag_system = RAGSystem()
