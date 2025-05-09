"""Vector storage for question-answer pairs"""

import os
import chromadb
from typing import Dict, List, Any, Optional, cast, TypedDict
from chromadb.api.types import Metadata, Documents, Embeddings, Where, ID
from sentence_transformers import SentenceTransformer


class QASearchResult(TypedDict, total=False):
    """Type definition for QA search results"""
    qa_id: str
    content: str
    question: str
    metadata: Dict[str, Any]
    similarity: float


class QAVectorStore:
    """Store and retrieve question-answer vectors for semantic search"""
    
    def __init__(self, persist_directory="./chroma_qa_db", model_name="all-MiniLM-L6-v2"):
        """Initialize the vector store with embeddings model"""
        self.model = SentenceTransformer(model_name)
        
        # Create ChromaDB client
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Create collection for QA pairs
        self.collection = self.client.get_or_create_collection(
            name="qa_pairs",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_qa_pair(self, qa_pair: Dict[str, Any]) -> None:
        """
        Add a question-answer pair to the vector store
        
        Args:
            qa_pair: The QA pair data to add
        """
        if not qa_pair:
            return
            
        # Extract the ID and text content
        qa_id = qa_pair.get("qa_id")
        question = qa_pair.get("question", "")
        answer = qa_pair.get("answer", "")
        
        if not qa_id or not question:
            return
            
        # Combine question and answer for embedding
        combined_text = f"Question: {question}\nAnswer: {answer}"
        
        # Generate embedding
        embedding = self.model.encode(combined_text).tolist()
        
        # Prepare metadata
        metadata: Metadata = {
            "qa_id": str(qa_id),
            "question": str(question),
            "is_validated": str(qa_pair.get("is_validated", False)),
            "created_at": qa_pair.get("created_at", "").isoformat() if hasattr(qa_pair.get("created_at", ""), "isoformat") else str(qa_pair.get("created_at", ""))
        }
        
        # Add to collection
        self.collection.upsert(
            ids=[str(qa_id)],
            embeddings=[embedding],
            documents=[combined_text],
            metadatas=[metadata]
        )
    
    def search_similar(self, query: str, n_results: int = 5, validated_only: bool = True) -> List[Dict[str, Any]]:
        """
        Search for similar QA pairs using semantic similarity
        
        Args:
            query: The search query
            n_results: Number of results to return
            validated_only: Whether to only return validated QA pairs
            
        Returns:
            List of QA pair matches with similarity scores
        """
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Define where clause if needed
        where_clause: Optional[Where] = None
        if validated_only:
            where_clause = {"is_validated": "True"}
                
        # Perform search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
        
        # Format results with proper safety checks
        formatted_results: List[Dict[str, Any]] = []
        
        # Check if we have valid IDs to process
        if (results and 
            'ids' in results and 
            isinstance(results['ids'], list) and 
            len(results['ids']) > 0):
                
            # Process each result
            for i in range(len(results['ids'][0])):
                # Create a properly typed result
                result_item: Dict[str, Any] = {
                    "qa_id": results['ids'][0][i]
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
                    meta = dict(results['metadatas'][0][i])
                    result_item["metadata"] = meta
                    # Extract question from metadata
                    result_item["question"] = meta.get("question", "")
                else:
                    result_item["metadata"] = {}
                    result_item["question"] = ""
                
                # Safely add distance if available
                if ('distances' in results and 
                    isinstance(results['distances'], list) and 
                    len(results['distances']) > 0 and 
                    i < len(results['distances'][0])):
                    result_item["similarity"] = 1.0 - float(results['distances'][0][i])
                else:
                    result_item["similarity"] = 0.0
                
                formatted_results.append(result_item)
        
        return formatted_results
    
    def delete_qa_pair(self, qa_id: str) -> None:
        """
        Delete a QA pair from the vector store
        
        Args:
            qa_id: QA pair identifier
        """
        self.collection.delete(ids=[str(qa_id)])
        
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection
        
        Returns:
            Dict with collection statistics
        """
        return {
            "count": self.collection.count()
        } 