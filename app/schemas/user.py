from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class UserBase(BaseModel):
    """Base User model with common fields"""
    name: str
    email: EmailStr
    role: str = "user"
    is_active: bool = True
    
    # Use Pydantic's config for customization
    model_config = ConfigDict(
        extra="allow",  # Allow extra fields
    )


class UserCreate(UserBase):
    """Model for creating a new user"""
    # Additional fields specific to user creation can be added here
    pass


class UserUpdate(BaseModel):
    """Model for updating a user"""
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(
        extra="allow",
    )


class UserInDB(UserBase):
    """Model for a user stored in the database"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserResponse(UserInDB):
    """Model for user responses"""
    id: str  # MongoDB ObjectId as string


def validate_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and normalizes user data using Pydantic
    
    Args:
        user_data: Dictionary containing user information
        
    Returns:
        Dict: Validated and normalized user data
    """
    # Create a UserCreate model from the dict
    user = UserCreate(**user_data)
    
    # Convert to UserInDB to add timestamps
    user_in_db = UserInDB(**user.model_dump())
    
    # Return as dict with any extra fields
    return user_in_db.model_dump() 