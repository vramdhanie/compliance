"""Document schema definitions for the compliance system"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    source: str = ""
    type: str = ""
    author: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    

class DocumentChunk(BaseModel):
    """A chunk of a document for storage and retrieval"""
    chunk_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    chunk_index: int
    content: str
    concepts: List[str] = Field(default_factory=list)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class Document(BaseModel):
    """Document schema for the compliance system"""
    document_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: Optional[str] = None
    source_path: Optional[str] = None
    file_type: str = ""
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    concepts: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class DocumentSearchResult(BaseModel):
    """Search result for document queries"""
    document: Document
    chunks: List[DocumentChunk] = Field(default_factory=list)
    score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        } 