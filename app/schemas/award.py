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


# Admin-specific schemas
class CreateAwardTemplateSchema(BaseModel):
    """Schema for creating award templates."""
    name: str
    description: str
    category: AwardCategory
    criteria: Dict[str, Any]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


class UpdateAwardTemplateSchema(BaseModel):
    """Schema for updating award templates."""
    name: Optional[str] = None
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ManualAwardGrantSchema(BaseModel):
    """Schema for manually granting awards."""
    user_id: int
    template_id: int
    tier: int = 1
    reason: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None

    class Config:
        from_attributes = True


class AwardRevocationSchema(BaseModel):
    """Schema for award revocation."""
    award_id: int
    reason: str

    class Config:
        from_attributes = True