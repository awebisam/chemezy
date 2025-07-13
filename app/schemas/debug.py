"""
Debug-related Pydantic schemas for API request/response serialization.
"""

from pydantic import BaseModel
from typing import Optional


class DebugClearResponseSchema(BaseModel):
    """Schema for debug clear operation response."""
    message: str

    class Config:
        from_attributes = True


class DebugDeletionRequestSchema(BaseModel):
    """Schema for debug deletion request input."""
    reason: str

    class Config:
        from_attributes = True


class DebugDeletionResponseSchema(BaseModel):
    """Schema for debug deletion request response."""
    message: str
    request_id: int

    class Config:
        from_attributes = True