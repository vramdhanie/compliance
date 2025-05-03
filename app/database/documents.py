from typing import Dict, List, Any, Optional
from bson import ObjectId
import pymongo

from app.database.connection import db
from app.database.types import MongoCollection


class DocumentStorage:
    """Store and retrieve document data from MongoDB"""
    
    def __init__(self, collection_prefix: str = ""):
        """
        Initialize document storage using the shared MongoDB connection
        
        Args:
            collection_prefix: Optional prefix for collection names
        """
        # Use the MongoDB singleton instance from connection.py
        self.db = db.get_database()
        if self.db is None:
            raise ConnectionError("Failed to connect to MongoDB")
            
        # Create collections with proper type annotations
        prefix = f"{collection_prefix}_" if collection_prefix else ""
        self.documents: MongoCollection[Dict[str, Any]] = db.get_collection(f"{prefix}documents")
        self.chunks: MongoCollection[Dict[str, Any]] = db.get_collection(f"{prefix}chunks")
        self.concepts: MongoCollection[Dict[str, Any]] = db.get_collection(f"{prefix}concepts")
        
        # Create indexes for faster retrieval
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """Create necessary indexes for efficient querying"""
        # Document indexes
        self.documents.create_index("document_id", unique=True)
        self.documents.create_index("concepts")
        
        # Chunk indexes
        self.chunks.create_index("chunk_id", unique=True)
        self.chunks.create_index("document_id")
        self.chunks.create_index("concepts")
        self.chunks.create_index([("metadata.source", pymongo.TEXT)])
        
        # Concept indexes
        self.concepts.create_index("concept", unique=True)
    
    def store_document(self, document_summary: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
        """
        Store a document and its chunks
        
        Args:
            document_summary: Document metadata and summary
            chunks: List of document chunks
            
        Returns:
            str: Document ID
        """
        # Insert document summary
        self.documents.update_one(
            {"document_id": document_summary["document_id"]},
            {"$set": document_summary},
            upsert=True
        )
        
        # Insert or update chunks
        for chunk in chunks:
            self.chunks.update_one(
                {"chunk_id": chunk["chunk_id"]},
                {"$set": chunk},
                upsert=True
            )
            
        # Track concepts
        if "concepts" in document_summary and document_summary["concepts"]:
            for concept in document_summary["concepts"]:
                self.concepts.update_one(
                    {"concept": concept},
                    {
                        "$set": {"concept": concept},
                        "$addToSet": {"documents": document_summary["document_id"]}
                    },
                    upsert=True
                )
        
        return document_summary["document_id"]
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID
        
        Args:
            document_id: Unique document identifier
            
        Returns:
            Optional[Dict[str, Any]]: Document data or None if not found
        """
        return self.documents.find_one({"document_id": document_id})
    
    def get_document_by_object_id(self, object_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by MongoDB ObjectId
        
        Args:
            object_id: MongoDB ObjectId
            
        Returns:
            Optional[Dict[str, Any]]: Document data or None if not found
        """
        return self.documents.find_one({"_id": object_id})
    
    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a chunk by ID
        
        Args:
            chunk_id: Unique chunk identifier
            
        Returns:
            Optional[Dict[str, Any]]: Chunk data or None if not found
        """
        return self.chunks.find_one({"chunk_id": chunk_id})
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a document
        
        Args:
            document_id: Document identifier
            
        Returns:
            List[Dict[str, Any]]: List of document chunks
        """
        cursor = self.chunks.find({"document_id": document_id})
        return list(cursor.sort("chunk_index", 1))
    
    def get_documents_by_concept(self, concept: str) -> List[Dict[str, Any]]:
        """
        Find documents that contain a specific concept
        
        Args:
            concept: Concept to search for
            
        Returns:
            List[Dict[str, Any]]: List of documents containing the concept
        """
        concept_record = self.concepts.find_one({"concept": concept})
        if concept_record and "documents" in concept_record:
            return list(self.documents.find({"document_id": {"$in": concept_record["documents"]}}))
        return []
    
    def find_chunks_by_text(self, query_text: str) -> List[Dict[str, Any]]:
        """
        Find chunks containing the query text (basic text search)
        
        Args:
            query_text: Text to search for
            
        Returns:
            List[Dict[str, Any]]: List of matching chunks
        """
        return list(self.chunks.find({"$text": {"$search": query_text}}))
    
    def get_all_concepts(self) -> List[str]:
        """
        Get all concepts in the database
        
        Returns:
            List[str]: List of all concepts
        """
        cursor = self.concepts.find({}, {"concept": 1, "_id": 0})
        result = list(cursor)
        return [doc["concept"] for doc in result]
    
    def find_chunks_by_metadata(self, metadata_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find chunks based on metadata filters
        
        Args:
            metadata_filters: Dictionary of metadata key-value pairs to filter by
            
        Returns:
            List[Dict[str, Any]]: List of matching chunks
        """
        query = {}
        for key, value in metadata_filters.items():
            query[f"metadata.{key}"] = value
        return list(self.chunks.find(query))