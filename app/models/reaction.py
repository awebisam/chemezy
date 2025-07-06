from typing import Optional
from sqlmodel import SQLModel, Field, JSON, Column
from datetime import datetime


class ReactionCache(SQLModel, table=True):
    """Cache table for storing reaction results."""
    __tablename__ = "reaction_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(unique=True, index=True, max_length=255)
    reactants: list[str] = Field(sa_column=Column(JSON))
    environment: str = Field(max_length=100)
    products: list[dict] = Field(sa_column=Column(JSON))
    effects: list[str] = Field(sa_column=Column(JSON))
    state_change: Optional[str] = Field(default=None, max_length=100)
    description: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: int = Field(foreign_key="user.id", index=True)


class Discovery(SQLModel, table=True):
    """Discovery ledger for tracking world-first effects."""
    __tablename__ = "discovery"

    id: Optional[int] = Field(default=None, primary_key=True)
    effect: str = Field(unique=True, index=True, max_length=100)
    discovered_by: int = Field(foreign_key="user.id", index=True)
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    reaction_cache_id: int = Field(foreign_key="reaction_cache.id")
