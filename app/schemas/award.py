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


# Request schemas for notification endpoints
class NotificationMarkReadSchema(BaseModel):
    """Schema for marking notifications as read."""
    notification_ids: List[str]

    class Config:
        from_attributes = True


# Response schemas for dashboard and notification endpoints
class DashboardStatsSchema(BaseModel):
    """Schema for dashboard statistics response."""
    user_id: int
    username: str
    dashboard_stats: Dict[str, Any]

    class Config:
        from_attributes = True


class RecentAwardsSchema(BaseModel):
    """Schema for recent awards response."""
    user_id: int
    recent_awards: List[Dict[str, Any]]
    days_back: int
    total_count: int

    class Config:
        from_attributes = True


class AwardProgressSchema(BaseModel):
    """Schema for award progress response."""
    user_id: int
    progress: Dict[str, Any]

    class Config:
        from_attributes = True


class AwardNotificationsSchema(BaseModel):
    """Schema for award notifications response."""
    user_id: int
    notifications: List[Dict[str, Any]]
    unread_only: bool
    total_count: int

    class Config:
        from_attributes = True


class NotificationMarkReadResponseSchema(BaseModel):
    """Schema for notification mark read response."""
    success: bool
    marked_count: int
    message: str

    class Config:
        from_attributes = True


class UserRankSchema(BaseModel):
    """Schema for user rank response."""
    rank: Optional[int]
    user_id: int
    username: str
    award_count: int
    total_points: int
    category: Optional[str] = None

    class Config:
        from_attributes = True


class RecentAchievementsSchema(BaseModel):
    """Schema for recent achievements response."""
    recent_achievements: List[Dict[str, Any]]
    total_count: int

    class Config:
        from_attributes = True


class CommunityStatisticsSchema(BaseModel):
    """Schema for community statistics response."""
    category_statistics: Dict[str, Any]
    generated_at: str

    class Config:
        from_attributes = True


class AwardRevocationResponseSchema(BaseModel):
    """Schema for award revocation response."""
    message: str
    award_id: int
    reason: str
    revoked_by: int

    class Config:
        from_attributes = True


# Additional response schemas for admin endpoints
class PaginatedAwardTemplatesSchema(BaseModel):
    """Schema for paginated award templates response."""
    templates: List[AwardTemplateSchema]
    total_count: int

    class Config:
        from_attributes = True