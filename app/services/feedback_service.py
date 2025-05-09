"""Service for managing question-answer feedback and storage"""

from typing import Dict, List, Any, Optional, Union, cast
import uuid
from datetime import datetime

from app.database.qa_storage import QAStorage
from app.database.qa_vector_store import QAVectorStore
from app.schemas.qa_pair import QAPair, Source, FeedbackItem


class FeedbackService:
    """Service for collecting and managing user feedback on question-answer pairs"""
    
    def __init__(self, qa_storage: QAStorage, qa_vector_store: QAVectorStore):
        """
        Initialize the feedback service
        
        Args:
            qa_storage: Storage for QA pairs
            qa_vector_store: Vector storage for semantic search
        """
        self.qa_storage = qa_storage
        self.qa_vector_store = qa_vector_store
    
    def store_qa_pair(self, question: str, answer: str, sources: List[Dict[str, Any]]) -> str:
        """
        Store a new question-answer pair
        
        Args:
            question: User's question
            answer: Generated answer
            sources: Source information for the answer
            
        Returns:
            str: QA pair ID
        """
        # Create a new QA pair
        qa_pair = QAPair(
            qa_id=str(uuid.uuid4()),
            question=question,
            answer=answer,
            sources=[Source(**source) for source in sources],
            is_validated=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Convert to dictionary for storage
        qa_dict = qa_pair.model_dump()
        
        # Store in MongoDB
        self.qa_storage.save_qa_pair(qa_dict)
        
        # Add to vector store for semantic search
        self.qa_vector_store.add_qa_pair(qa_dict)
        
        return qa_pair.qa_id
    
    def add_feedback(self, qa_id: str, is_accurate: bool, feedback_text: Optional[str] = None) -> bool:
        """
        Add user feedback to a QA pair
        
        Args:
            qa_id: QA pair identifier
            is_accurate: Whether the answer was accurate
            feedback_text: Optional feedback text
            
        Returns:
            bool: True if feedback was added successfully
        """
        # Add feedback to MongoDB
        success = self.qa_storage.add_feedback(qa_id, is_accurate, feedback_text)
        
        if success and is_accurate:
            # If the feedback is positive, update the vector store
            qa_pair = self.qa_storage.get_qa_pair(qa_id)
            if qa_pair:
                self.qa_vector_store.add_qa_pair(qa_pair)
                
        return success
    
    def find_similar_questions(self, query: str, n_results: int = 3, validated_only: bool = True) -> List[Dict[str, Any]]:
        """
        Find similar questions to the query
        
        Args:
            query: User's question
            n_results: Number of results to return
            validated_only: Whether to only return validated QA pairs
            
        Returns:
            List of similar QA pairs with similarity scores
        """
        # Search vector store for similar questions
        results = self.qa_vector_store.search_similar(query, n_results, validated_only)
        
        # Enrich with full QA pair data
        enriched_results = []
        for result in results:
            qa_id = result.get("qa_id")
            if qa_id:
                # Get full QA pair data
                qa_pair = self.qa_storage.get_qa_pair(qa_id)
                if qa_pair:
                    # Combine the search result with the full QA pair data
                    enriched_result = {
                        **result,
                        "full_answer": qa_pair.get("answer", ""),
                        "sources": qa_pair.get("sources", []),
                        "is_validated": qa_pair.get("is_validated", False)
                    }
                    enriched_results.append(enriched_result)
        
        return enriched_results
    
    def get_all_validated_qa_pairs(self) -> List[Dict[str, Any]]:
        """
        Get all validated QA pairs
        
        Returns:
            List of validated QA pairs
        """
        return self.qa_storage.get_all_qa_pairs(validated_only=True)
    
    def delete_qa_pair(self, qa_id: str) -> bool:
        """
        Delete a QA pair
        
        Args:
            qa_id: QA pair identifier
            
        Returns:
            bool: True if deleted successfully
        """
        # Delete from MongoDB
        mongo_deleted = self.qa_storage.delete_qa_pair(qa_id)
        
        # Delete from vector store
        self.qa_vector_store.delete_qa_pair(qa_id)
        
        return mongo_deleted 