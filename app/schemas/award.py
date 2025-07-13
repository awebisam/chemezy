"""
Award-related Pydantic schemas for API request/response serialization.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from app.models.award import AwardCategory


class AwardTemplateSchema(BaseModel):
    """Schema for award template information."""
    id: int
    name: str
    description: str
    category: AwardCategory
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class UserAwardSchema(BaseModel):
    """Schema for user award response."""
    id: int
    user_id: int
    template_id: int
    tier: int
    progress: Dict[str, Any]
    granted_at: datetime
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    template: AwardTemplateSchema

    class Config:
        from_attributes = True


class AvailableAwardSchema(BaseModel):
    """Schema for available award with progress information."""
    template_id: int
    name: str
    description: str
    category: AwardCategory
    metadata: Dict[str, Any]
    progress: Dict[str, Any]

    class Config:
        from_attributes = True


class LeaderboardEntrySchema(BaseModel):
    """Schema for leaderboard entry."""
    rank: int
    user_id: int
    username: str
    award_count: int
    total_points: int

    class Config:
        from_attributes = True


class UserAwardsResponseSchema(BaseModel):
    """Schema for user awards list response."""
    awards: List[UserAwardSchema]
    total_count: int

    class Config:
        from_attributes = True


class AvailableAwardsResponseSchema(BaseModel):
    """Schema for available awards list response."""
    available_awards: List[AvailableAwardSchema]
    total_count: int

    class Config:
        from_attributes = True