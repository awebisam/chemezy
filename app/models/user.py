from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class UserBase(SQLModel):
    """Base user model with shared fields."""
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False, description="Admin user with management privileges")
    public_profile: bool = Field(default=False, description="Allow public viewing of awards")


class User(UserBase, table=True):
    """User table model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(min_length=8, max_length=100)


class UserLogin(SQLModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)."""
    id: int
    created_at: datetime
