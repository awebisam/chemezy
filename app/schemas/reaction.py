from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ChemicalProduct(BaseModel):
    """Schema for chemical products."""
    formula: str
    name: str
    state: str


class ReactionRequest(BaseModel):
    """Schema for reaction prediction requests."""
    chemicals: List[str]
    environment: str = "Earth (Normal)"
    conditions: Optional[List[str]] = None


class ReactionResponse(BaseModel):
    """Schema for reaction prediction responses."""
    request_id: str
    products: List[ChemicalProduct]
    effects: List[str]
    state_change: Optional[str]
    description: str
    is_world_first: bool


class ReactionCacheSchema(BaseModel):
    """Schema for reaction cache entries."""
    id: int
    cache_key: str
    reactants: List[str]
    environment: str
    products: List[dict]
    effects: List[str]
    state_change: Optional[str]
    description: str
    created_at: datetime
    user_id: int

    class Config:
        from_attributes = True


class DiscoverySchema(BaseModel):
    """Schema for discovery entries."""
    id: int
    effect: str
    discovered_by: int
    discovered_at: datetime
    reaction_cache_id: int

    class Config:
        from_attributes = True