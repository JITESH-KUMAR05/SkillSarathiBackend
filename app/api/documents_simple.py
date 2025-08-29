"""
Simple Documents API for BuddyAgents
===================================
Basic document management without complex RAG dependencies
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Document(BaseModel):
    id: str
    title: str
    content: str
    created_at: str
    file_type: str = "text"

class DocumentResponse(BaseModel):
    documents: List[Document]
    total: int

router = APIRouter()

# In-memory storage for demo (replace with database later)
_documents = {}

@router.get("/", response_model=DocumentResponse)
async def list_documents():
    """List all documents"""
    
    try:
        documents = list(_documents.values())
        return DocumentResponse(
            documents=documents,
            total=len(documents)
        )
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")

@router.post("/", response_model=Document)
async def create_document(title: str, content: str):
    """Create a new document"""
    
    try:
        doc_id = f"doc_{len(_documents) + 1}"
        
        document = Document(
            id=doc_id,
            title=title,
            content=content,
            created_at=datetime.now().isoformat(),
            file_type="text"
        )
        
        _documents[doc_id] = document
        
        return document
        
    except Exception as e:
        logger.error(f"Error creating document: {e}")
        raise HTTPException(status_code=500, detail="Failed to create document")

@router.get("/{document_id}", response_model=Document)
async def get_document(document_id: str):
    """Get a specific document"""
    
    try:
        if document_id not in _documents:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return _documents[document_id]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to get document")

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document"""
    
    try:
        if document_id not in _documents:
            raise HTTPException(status_code=404, detail="Document not found")
        
        del _documents[document_id]
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

@router.post("/search")
async def search_documents(query: str):
    """Search documents"""
    
    try:
        results = []
        query_lower = query.lower()
        
        for doc in _documents.values():
            if (query_lower in doc.title.lower() or 
                query_lower in doc.content.lower()):
                results.append(doc)
        
        return DocumentResponse(
            documents=results,
            total=len(results)
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to search documents")

@router.get("/health")
async def documents_health():
    """Health check for documents system"""
    
    return {
        "status": "healthy",
        "total_documents": len(_documents),
        "timestamp": datetime.now().isoformat()
    }
