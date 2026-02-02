"""User domain models"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserModel(BaseModel):
    """User domain model"""
    
    # Pydantic V2 configuration
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "User1",
                "email": "user1@robot.com",
                "role": "operator",
                "phone": "+82-10-1234-5678",
                "address": "Seoul, Korea",
                "bio": "Lorem ipsum dolor sit amet...",
                "avatar_url": "https://example.com/avatar1.jpg",
                "site_id": 1
            }
        }
    )
    
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None  # Large field for over-fetching test
    avatar_url: Optional[str] = None
    site_id: int
