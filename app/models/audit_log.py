"""
Audit Log Model

Database model for tracking award-related actions and system events.
"""

from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime
from enum import Enum


class AuditAction(str, Enum):
    """Enum for different types of audit actions."""
    AWARD_GRANTED = "award_granted"
    AWARD_REVOKED = "award_revoked"
    AWARD_MANUAL_GRANT = "award_manual_grant"
    TEMPLATE_CREATED = "template_created"
    TEMPLATE_UPDATED = "template_updated"
    TEMPLATE_ACTIVATED = "template_activated"
    TEMPLATE_DEACTIVATED = "template_deactivated"
    USER_PROMOTION = "user_promotion"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ALERT = "performance_alert"


class AuditLogBase(SQLModel):
    """Base audit log model with shared fields."""
    action: AuditAction
    user_id: Optional[int] = Field(default=None, description="User who performed the action")
    target_user_id: Optional[int] = Field(default=None, description="User who was affected by the action")
    entity_type: Optional[str] = Field(default=None, description="Type of entity affected (award, template, etc.)")
    entity_id: Optional[int] = Field(default=None, description="ID of the affected entity")
    details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Additional details about the action")
    ip_address: Optional[str] = Field(default=None, description="IP address of the user")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    status: str = Field(default="success", description="Status of the action (success, failure, warning)")
    error_message: Optional[str] = Field(default=None, description="Error message if action failed")


class AuditLog(AuditLogBase, table=True):
    """Audit log table model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the action occurred")
    session_id: Optional[str] = Field(default=None, description="Session ID if available")


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log entries."""
    pass


class AuditLogResponse(AuditLogBase):
    """Schema for audit log responses."""
    id: int
    created_at: datetime
    session_id: Optional[str] = None