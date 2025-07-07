from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreateSchema(BaseModel):
    """Schema for user creation requests."""
    username: str
    email: EmailStr
    password: str


class UserLoginSchema(BaseModel):
    """Schema for user login requests."""
    username: str
    password: str


class UserResponseSchema(BaseModel):
    """Schema for user response data."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateSchema(BaseModel):
    """Schema for user update requests."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None