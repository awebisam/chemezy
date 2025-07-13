"""
Admin monitoring and audit related Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class SystemHealthSchema(BaseModel):
    """Schema for system health statistics response."""
    system_health: Dict[str, Any]
    checked_at: datetime
    checked_by: str

    class Config:
        from_attributes = True


class UserActivitySchema(BaseModel):
    """Schema for user activity statistics response."""
    user_activity: Dict[str, Any]
    checked_at: datetime
    checked_by: str

    class Config:
        from_attributes = True


class MonitoringAlertsSchema(BaseModel):
    """Schema for monitoring alerts response."""
    alerts: List[Dict[str, Any]]
    alert_count: int
    checked_at: datetime
    checked_by: str

    class Config:
        from_attributes = True


class LogCleanupResponseSchema(BaseModel):
    """Schema for log cleanup response."""
    success: bool
    deleted_count: int
    days_kept: int
    cleaned_at: datetime
    cleaned_by: str

    class Config:
        from_attributes = True


class AlertSummarySchema(BaseModel):
    """Schema for alert summary."""
    items: List[Dict[str, Any]]
    count: int
    critical_count: int
    warning_count: int

    class Config:
        from_attributes = True


class RecentActivitySchema(BaseModel):
    """Schema for recent activity item."""
    id: int
    action: str
    user_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdminDashboardSchema(BaseModel):
    """Schema for admin dashboard response."""
    system_health: Dict[str, Any]
    alerts: AlertSummarySchema
    recent_activity: List[RecentActivitySchema]
    generated_at: datetime
    generated_by: str

    class Config:
        from_attributes = True