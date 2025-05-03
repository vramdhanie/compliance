import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.user import UserBase, UserCreate, UserUpdate, UserInDB, UserResponse


def test_user_create():
    """Test UserCreate model validation"""
    # Valid data
    user = UserCreate(name="Test User", email="test@example.com")
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    assert user.role == "user"  # default value
    assert user.is_active is True  # default value
    
    # Invalid email
    with pytest.raises(ValidationError):
        UserCreate(name="Test User", email="invalid-email")
    
    # Missing required field should fail validation
    try:
        UserCreate(email="test@example.com")
        pytest.fail("Should fail when name is missing")
    except ValidationError:
        pass
    
    # Extra fields are allowed
    user = UserCreate(
        name="Test User", 
        email="test@example.com", 
        custom_field="value"
    )
    assert user.model_dump().get("custom_field") == "value"


def test_user_update():
    """Test UserUpdate model"""
    # All fields optional
    user_update = UserUpdate()
    assert user_update.name is None
    assert user_update.email is None
    
    # Partial update
    user_update = UserUpdate(role="admin")
    assert user_update.role == "admin"
    assert user_update.name is None
    
    # Invalid email still validated
    with pytest.raises(ValidationError):
        UserUpdate(email="invalid-email")


def test_user_in_db():
    """Test UserInDB model"""
    user = UserInDB(name="Test User", email="test@example.com")
    
    # Check default timestamps
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


def test_user_response():
    """Test UserResponse model"""
    user = UserResponse(
        id="507f1f77bcf86cd799439011",
        name="Test User",
        email="test@example.com",
        created_at=datetime(2023, 1, 1),
        updated_at=datetime(2023, 1, 1)
    )
    
    # ID is required
    assert user.id == "507f1f77bcf86cd799439011"
    
    # Inherits from UserInDB
    assert user.name == "Test User"
    assert user.email == "test@example.com"
    
    # Without id should fail validation
    try:
        UserResponse(name="Test User", email="test@example.com")
        pytest.fail("Should fail when id is missing")
    except ValidationError:
        pass 