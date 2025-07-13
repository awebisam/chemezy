import enum
from typing import Any, Dict, Optional
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel
from datetime import datetime


class AwardCategory(str, enum.Enum):
    """Categories for different types of awards."""
    DISCOVERY = "discovery"
    DATABASE_CONTRIBUTION = "database_contribution"
    COMMUNITY = "community"
    SPECIAL = "special"
    ACHIEVEMENT = "achievement"


class AwardTemplate(SQLModel, table=True):
    """Template for award definitions with configurable criteria."""
    __tablename__ = "award_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: str = Field(max_length=500)
    category: AwardCategory
    criteria: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    award_metadata: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(foreign_key="user.id", index=True)


class UserAward(SQLModel, table=True):
    """Individual awards granted to users."""
    __tablename__ = "user_awards"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    template_id: int = Field(foreign_key="award_templates.id", index=True)
    tier: int = Field(default=1)
    progress: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    related_entity_type: Optional[str] = Field(default=None, max_length=50)
    related_entity_id: Optional[int] = Field(default=None)