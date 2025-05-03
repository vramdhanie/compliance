from typing import Dict, List, Optional, Any, cast
from bson.objectid import ObjectId
from app.database import db
from app.database.types import MongoCollection, InsertOneResult, UpdateResult, DeleteResult
from app.schemas.user import UserCreate, UserUpdate, UserInDB, UserResponse, validate_user


class UserService:
    """Service for handling user-related operations with MongoDB"""
    
    def __init__(self):
        self.collection: MongoCollection[Dict[str, Any]] = db.get_collection("users")
    
    def create_user(self, user_data: Dict[str, Any] | UserCreate) -> str:
        """
        Create a new user
        
        Args:
            user_data: Dictionary or UserCreate model containing user information
            
        Returns:
            str: ID of the created user
        """
        # Convert to dict if it's a Pydantic model
        if isinstance(user_data, UserCreate):
            user_dict = user_data.model_dump()
        else:
            user_dict = user_data
            
        # Validate and normalize user data
        validated_data = validate_user(user_dict)
        
        # Insert into database
        result: InsertOneResult = self.collection.insert_one(validated_data)
        return str(result.inserted_id)
    
    def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """
        Get a user by ID
        
        Args:
            user_id: The user ID to search for
            
        Returns:
            UserResponse or None: The user if found, None otherwise
        """
        user_dict = self.collection.find_one({"_id": ObjectId(user_id)})
        if user_dict is None:
            return None
            
        # Convert ObjectId to string for the response
        user_id_str = str(user_dict.pop("_id"))
        return UserResponse(id=user_id_str, **user_dict)
    
    def get_users(self, query: Optional[Dict[str, Any]] = None) -> List[UserResponse]:
        """
        Get users matching the query
        
        Args:
            query: Query dictionary (default: {})
            
        Returns:
            List[UserResponse]: List of matching users
        """
        query = query or {}
        users = []
        
        for user_dict in self.collection.find(query):
            # Convert ObjectId to string for the response
            user_id_str = str(user_dict.pop("_id"))
            users.append(UserResponse(id=user_id_str, **user_dict))
            
        return users
    
    def update_user(self, user_id: str, update_data: Dict[str, Any] | UserUpdate) -> bool:
        """
        Update a user
        
        Args:
            user_id: The user ID to update
            update_data: Dictionary or UserUpdate model containing fields to update
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        # Convert to dict if it's a Pydantic model
        if isinstance(update_data, UserUpdate):
            update_dict = update_data.model_dump(exclude_unset=True)
        else:
            update_dict = {k: v for k, v in update_data.items() if v is not None}
        
        # Add updated_at timestamp
        from datetime import datetime
        update_dict["updated_at"] = datetime.utcnow()
        
        result: UpdateResult = self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user
        
        Args:
            user_id: The user ID to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        result: DeleteResult = self.collection.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0 