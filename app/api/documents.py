"""
Document Management API with enhanced file processing
Supports multiple file formats and intelligent content extraction
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import aiofiles
import os
from pathlib import Path
import uuid
from datetime import datetime

from app.database.base import get_db
from app.database.models import Document as DocumentModel, User
from app.database.schemas import Document, DocumentCreate, DocumentUpdate
from app.auth.dependencies import get_current_active_user
from app.rag.enhanced_rag_system import get_rag_system
from app.rag.enhanced_rag_system import enhanced_rag_system

router = APIRouter()

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.get("/", response_model=List[Document])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user's documents"""
    result = await db.execute(
        select(DocumentModel)
        .where(DocumentModel.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    documents = result.scalars().all()
    return documents


@router.post("/", response_model=Document)
async def create_document(
    document: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new document"""
    # Create document in database
    db_document = DocumentModel(
        title=document.title,
        content=document.content,
        file_type=document.file_type,
        user_id=current_user.id,
        metadata=document.metadata
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Add to vector database
    try:
        chunk_ids = await rag_system.add_document(
            document_content=document.content,
            document_id=str(db_document.id),
            metadata={
                "user_id": current_user.id,
                "title": document.title,
                "file_type": document.file_type,
                **(document.metadata or {})
            }
        )
        
        # Update document with vector IDs
        db_document.vector_id = ",".join(chunk_ids)
        await db.commit()
        
    except Exception as e:
        # If vector indexing fails, we still keep the document but log the error
        print(f"Failed to index document {db_document.id}: {e}")
    
    return db_document


@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload and process a document file"""
    # Validate file type
    allowed_types = {".txt", ".pdf", ".docx", ".md"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Allowed types: {allowed_types}"
        )
    
    # Save file
    file_path = UPLOAD_DIR / f"{current_user.id}_{file.filename}"
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Extract text content based on file type
    try:
        if file_extension == ".txt" or file_extension == ".md":
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                file_content = await f.read()
        elif file_extension == ".pdf":
            # Import here to avoid dependency issues if not installed
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            file_content = ""
            for page in reader.pages:
                file_content += page.extract_text() + "\n"
        elif file_extension == ".docx":
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            file_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type"
            )
    
    except Exception as e:
        # Clean up file if processing fails
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process file: {str(e)}"
        )
    
    # Create document record
    document_title = title or file.filename
    db_document = DocumentModel(
        title=document_title,
        content=file_content,
        file_path=str(file_path),
        file_type=file_extension,
        user_id=current_user.id,
        metadata={"original_filename": file.filename}
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Add to vector database
    try:
        chunk_ids = await rag_system.add_document(
            document_content=file_content,
            document_id=str(db_document.id),
            metadata={
                "user_id": current_user.id,
                "title": document_title,
                "file_type": file_extension,
                "original_filename": file.filename
            }
        )
        
        db_document.vector_id = ",".join(chunk_ids)
        await db.commit()
        
    except Exception as e:
        print(f"Failed to index uploaded document {db_document.id}: {e}")
    
    return db_document


@router.post("/upload-enhanced", response_model=Document)
async def upload_document_enhanced(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: Optional[str] = Form("general"),
    tags: Optional[str] = Form(""),  # Comma-separated tags
    auto_extract_info: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enhanced document upload with intelligent content extraction and categorization
    Supports: PDF, DOCX, TXT, MD files with metadata extraction
    """
    # Validate file type
    allowed_types = {".txt", ".pdf", ".docx", ".md", ".rtf"}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_extension} not supported. Allowed types: {allowed_types}"
        )
    
    # Generate unique filename to avoid conflicts
    unique_filename = f"{current_user.id}_{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Extract text content with enhanced processing
    try:
        file_content, extracted_metadata = await _extract_content_enhanced(file_path, file_extension)
        
        if not file_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text content could be extracted from the file"
            )
        
    except Exception as e:
        # Clean up file if processing fails
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process file: {str(e)}"
        )
    
    # Prepare document metadata
    document_title = title or extracted_metadata.get("title", file.filename)
    
    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
    
    # Enhanced metadata
    enhanced_metadata = {
        "original_filename": file.filename,
        "file_size": len(content),
        "upload_timestamp": datetime.utcnow().isoformat(),
        "category": category,
        "tags": tag_list,
        "auto_extracted": auto_extract_info,
        **extracted_metadata
    }
    
    # Create document record
    db_document = DocumentModel(
        title=document_title,
        content=file_content,
        file_path=str(file_path),
        file_type=file_extension,
        user_id=current_user.id,
        metadata=enhanced_metadata
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    
    # Add to both RAG systems for comprehensive indexing
    try:
        # Add to standard RAG system
        chunk_ids = await rag_system.add_document(
            document_content=file_content,
            document_id=str(db_document.id),
            metadata={
                "user_id": current_user.id,
                "title": document_title,
                "file_type": file_extension,
                "category": category,
                **enhanced_metadata
            }
        )
        
        # Add to enhanced RAG system for user-specific knowledge
        await enhanced_rag_system.add_document(
            user_id=str(current_user.id),
            content=file_content,
            metadata={
                "document_id": str(db_document.id),
                "title": document_title,
                "category": category,
                "tags": tag_list,
                **enhanced_metadata
            }
        )
        
        # Update document with vector IDs
        db_document.vector_id = ",".join(chunk_ids)
        await db.commit()
        
        # Log this interaction for user learning
        await enhanced_rag_system.add_user_interaction(
            user_id=str(current_user.id),
            interaction={
                "action": "document_upload",
                "document_title": document_title,
                "category": category,
                "file_type": file_extension,
                "content_length": len(file_content),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Failed to index uploaded document {db_document.id}: {e}")
        # Don't fail the upload, just log the error
    
    return db_document


async def _extract_content_enhanced(file_path: Path, file_extension: str) -> tuple[str, dict]:
    """
    Enhanced content extraction with metadata extraction
    Returns: (content, metadata_dict)
    """
    content = ""
    metadata = {}
    
    try:
        if file_extension in [".txt", ".md"]:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
            # Extract basic metadata for text files
            lines = content.split('\n')
            metadata["line_count"] = len(lines)
            metadata["word_count"] = len(content.split())
            
            # Try to extract title from first line if it looks like a title
            if lines and (lines[0].startswith('#') or len(lines[0]) < 100):
                metadata["title"] = lines[0].strip('#').strip()
                
        elif file_extension == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(file_path))
                
                # Extract text
                for page in reader.pages:
                    content += page.extract_text() + "\n"
                
                # Extract metadata
                if reader.metadata:
                    metadata["pdf_title"] = reader.metadata.get('/Title', '')
                    metadata["pdf_author"] = reader.metadata.get('/Author', '')
                    metadata["pdf_subject"] = reader.metadata.get('/Subject', '')
                    metadata["pdf_creator"] = reader.metadata.get('/Creator', '')
                
                metadata["page_count"] = len(reader.pages)
                metadata["word_count"] = len(content.split())
                
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF processing not available. Please install pypdf."
                )
                
        elif file_extension == ".docx":
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(str(file_path))
                
                # Extract text
                content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                
                # Extract metadata
                core_props = doc.core_properties
                metadata["docx_title"] = core_props.title or ""
                metadata["docx_author"] = core_props.author or ""
                metadata["docx_subject"] = core_props.subject or ""
                metadata["docx_keywords"] = core_props.keywords or ""
                
                if core_props.created:
                    metadata["created_date"] = core_props.created.isoformat()
                if core_props.modified:
                    metadata["modified_date"] = core_props.modified.isoformat()
                
                metadata["paragraph_count"] = len(doc.paragraphs)
                metadata["word_count"] = len(content.split())
                
            except ImportError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="DOCX processing not available. Please install python-docx."
                )
                
        elif file_extension == ".rtf":
            # Basic RTF support (you might want to add striprtf library)
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                raw_content = await f.read()
                # Simple RTF cleaning (basic approach)
                content = raw_content  # TODO: Add proper RTF parsing
                metadata["format"] = "rtf"
                
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error extracting content: {str(e)}"
        )
    
    return content, metadata


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get specific document"""
    result = await db.execute(
        select(DocumentModel)
        .where(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a document"""
    result = await db.execute(
        select(DocumentModel)
        .where(
            DocumentModel.id == document_id,
            DocumentModel.user_id == current_user.id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Remove from vector database
    try:
        await rag_system.delete_document(str(document.id))
    except Exception as e:
        print(f"Failed to remove document from vector database: {e}")
    
    # Remove file if exists
    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Remove from database
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}


@router.post("/search")
async def search_documents(
    query: str,
    top_k: int = 5,
    current_user: User = Depends(get_current_active_user)
):
    """Search documents using RAG"""
    try:
        results = await rag_system.search_documents(
            query=query,
            user_id=current_user.id,
            top_k=top_k
        )
        return {"results": results}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
