"""Storage module for question-answer pairs"""

from typing import Dict, List, Any, Optional, cast
from bson import ObjectId
import pymongo
from datetime import datetime

from app.database.connection import db
from app.database.types import MongoCollection


class QAStorage:
    """Store and retrieve question-answer pairs with feedback"""
    
    def __init__(self, collection_prefix: str = ""):
        """
        Initialize QA storage using the shared MongoDB connection
        
        Args:
            collection_prefix: Optional prefix for collection names
        """
        # Use the MongoDB singleton instance from connection.py
        self.db = db.get_database()
        if self.db is None:
            raise ConnectionError("Failed to connect to MongoDB")
            
        # Create collections with proper type annotations
        prefix = f"{collection_prefix}_" if collection_prefix else ""
        self.qa_pairs: MongoCollection[Dict[str, Any]] = db.get_collection(f"{prefix}qa_pairs")
        
        # Create indexes for faster retrieval
        self._create_indexes()
    
    def _create_indexes(self) -> None:
        """Create necessary indexes for efficient querying"""
        # QA pair indexes
        self.qa_pairs.create_index("qa_id", unique=True)
        self.qa_pairs.create_index("is_validated")
        self.qa_pairs.create_index("created_at")
        self.qa_pairs.create_index([("question", pymongo.TEXT), ("answer", pymongo.TEXT)])
    
    def save_qa_pair(self, qa_pair: Dict[str, Any]) -> str:
        """
        Save a question-answer pair to the database
        
        Args:
            qa_pair: The QA pair data to save
            
        Returns:
            str: QA pair ID
        """
        # Insert or update QA pair
        self.qa_pairs.update_one(
            {"qa_id": qa_pair["qa_id"]},
            {"$set": qa_pair},
            upsert=True
        )
        
        return qa_pair["qa_id"]
    
    def get_qa_pair(self, qa_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a QA pair by ID
        
        Args:
            qa_id: QA pair identifier
            
        Returns:
            Optional[Dict[str, Any]]: QA pair data or None if not found
        """
        return self.qa_pairs.find_one({"qa_id": qa_id})
    
    def get_qa_pair_by_object_id(self, object_id: ObjectId) -> Optional[Dict[str, Any]]:
        """
        Retrieve a QA pair by MongoDB ObjectId
        
        Args:
            object_id: MongoDB ObjectId
            
        Returns:
            Optional[Dict[str, Any]]: QA pair data or None if not found
        """
        return self.qa_pairs.find_one({"_id": object_id})
    
    def get_all_qa_pairs(self, validated_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get all QA pairs, optionally filtered by validation status
        
        Args:
            validated_only: If True, only return validated QA pairs
            
        Returns:
            List[Dict[str, Any]]: List of QA pairs
        """
        query = {}
        if validated_only:
            query["is_validated"] = True
            
        return list(self.qa_pairs.find(query).sort("created_at", -1))
    
    def search_qa_pairs(self, query_text: str, validated_only: bool = False) -> List[Dict[str, Any]]:
        """
        Search QA pairs by text content
        
        Args:
            query_text: Text to search for
            validated_only: If True, only search validated QA pairs
            
        Returns:
            List[Dict[str, Any]]: List of matching QA pairs
        """
        search_query: Dict[str, Any] = {"$text": {"$search": query_text}}
        
        if validated_only:
            search_query["is_validated"] = True
            
        return list(self.qa_pairs.find(search_query))
    
    def add_feedback(self, qa_id: str, is_accurate: bool, feedback_text: Optional[str] = None) -> bool:
        """
        Add feedback to a QA pair
        
        Args:
            qa_id: QA pair identifier
            is_accurate: Whether the answer is accurate
            feedback_text: Optional feedback text
            
        Returns:
            bool: True if feedback was added successfully, False otherwise
        """
        qa_pair = self.get_qa_pair(qa_id)
        if not qa_pair:
            return False
            
        # Create feedback item
        feedback_item = {
            "timestamp": datetime.now(),
            "is_accurate": is_accurate,
            "feedback_text": feedback_text
        }
        
        # Update QA pair with new feedback
        update_data: Dict[str, Any] = {
            "$push": {"feedback": feedback_item},
            "$set": {"updated_at": datetime.now()}
        }
        
        # If marked as accurate, update validation status
        if is_accurate:
            update_data["$set"]["is_validated"] = True
            
        self.qa_pairs.update_one(
            {"qa_id": qa_id},
            update_data
        )
        
        return True
    
    def delete_qa_pair(self, qa_id: str) -> bool:
        """
        Delete a QA pair
        
        Args:
            qa_id: QA pair identifier
            
        Returns:
            bool: True if deleted successfully, False if not found
        """
        result = self.qa_pairs.delete_one({"qa_id": qa_id})
        return result.deleted_count > 0 