import os
import chromadb
from typing import Dict, List, Any, Optional, cast, TypedDict
from chromadb.api.types import Metadata, Documents, Embeddings
from sentence_transformers import SentenceTransformer


class SearchResult(TypedDict, total=False):
    """Type definition for search results"""
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    distance: Optional[float]


class VectorStore:
    """Store and retrieve document vectors for semantic search"""
    
    def __init__(self, persist_directory="./chroma_db", model_name="all-MiniLM-L6-v2"):
        """Initialize the vector store with embeddings model"""
        self.model = SentenceTransformer(model_name)
        
        # Create ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create collection for document chunks
        self.collection = self.client.get_or_create_collection(
            name="document_chunks",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_chunks(self, chunks):
        """Add document chunks to the vector store"""
        if not chunks:
            return
            
        # Process in batches to avoid overwhelming memory
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Prepare data for ChromaDB
            ids = [str(chunk["chunk_id"]) for chunk in batch]
            documents = [str(chunk["content"]) for chunk in batch]
            
            # Create properly typed metadata
            metadatas: List[Metadata] = []
            for chunk in batch:
                metadata: Metadata = {
                    "document_id": str(chunk["document_id"]),
                    "chunk_index": str(chunk["chunk_index"]),  # Convert to string to satisfy Metadata type
                    "source": str(chunk["metadata"].get("source", "")),
                    "type": str(chunk["metadata"].get("type", ""))
                }
                metadatas.append(metadata)
            
            # Generate embeddings
            embeddings = self.model.encode(documents).tolist()
            
            # Add to collection
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
    
    def search(self, query, n_results=5, filters=None):
        """Search for relevant chunks using semantic similarity"""
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Perform search with optional filters
        where_clause = {}
        if filters:
            for key, value in filters.items():
                where_clause[key] = value
                
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        # Format results with proper safety checks
        formatted_results: List[SearchResult] = []
        
        # Check if we have valid IDs to process
        if (results and 
            'ids' in results and 
            isinstance(results['ids'], list) and 
            len(results['ids']) > 0):
                
            # Process each result
            for i in range(len(results['ids'][0])):
                # Build result with safety checks for each field
                result_item: SearchResult = {
                    "chunk_id": results['ids'][0][i]
                }
                
                # Safely add content if available
                if ('documents' in results and 
                    isinstance(results['documents'], list) and 
                    len(results['documents']) > 0 and 
                    i < len(results['documents'][0])):
                    result_item["content"] = results['documents'][0][i]
                else:
                    result_item["content"] = ""
                
                # Safely add metadata if available
                if ('metadatas' in results and 
                    isinstance(results['metadatas'], list) and 
                    len(results['metadatas']) > 0 and 
                    i < len(results['metadatas'][0])):
                    result_item["metadata"] = dict(results['metadatas'][0][i])
                else:
                    result_item["metadata"] = {}
                
                # Safely add distance if available
                if ('distances' in results and 
                    isinstance(results['distances'], list) and 
                    len(results['distances']) > 0 and 
                    i < len(results['distances'][0])):
                    result_item["distance"] = float(results['distances'][0][i])
                else:
                    result_item["distance"] = None
                
                formatted_results.append(result_item)
            
        return formatted_results
    
    def delete_document(self, document_id):
        """Delete all chunks for a specific document"""
        self.collection.delete(
            where={"document_id": str(document_id)}
        )
        
    def get_collection_stats(self):
        """Get statistics about the vector collection"""
        return {
            "count": self.collection.count()
        }