from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChemicalProduct(BaseModel):
    """Schema for chemical products."""
    formula: str
    name: str
    state: str


class ReactionRequest(BaseModel):
    """Schema for reaction prediction requests."""
    chemicals: list[str]
    environment: str = "Earth (Normal)"
    conditions: Optional[list[str]] = None

# New schema for DSPy's typed output


class ReactionPredictionOutput(BaseModel):
    """
    Defines the structured output for a chemical reaction prediction.
    This schema is used by DSPy to validate and parse the LLM's response.
    """
    products: list[ChemicalProduct] = Field(
        ..., description="A list of chemical products formed in the reaction.")
    effects: list[str] = Field(
        ..., description="Observable phenomena during the reaction (e.g., 'gas evolution', 'color change').")
    state_change: Optional[str] = Field(
        None, description="The overall change in the state of matter, if any.")
    description: str = Field(
        ..., description="A clear, concise scientific explanation of the reaction mechanism and outcome.")


class ReactionResponse(BaseModel):
    """Schema for the final API reaction prediction response."""
    request_id: str
    products: list[ChemicalProduct]
    effects: list[str]
    state_change: Optional[str]
    description: str
    is_world_first: bool


class ReactionCacheSchema(BaseModel):
    """Schema for reaction cache entries."""
    id: int
    cache_key: str
    reactants: list[str]
    environment: str
    products: list[dict]
    effects: list[str]
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
