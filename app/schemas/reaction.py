from pydantic import BaseModel, Field
from typing import List, Optional

from .effects import Effect
from .environment import Environment

class ReactantInput(BaseModel):
    chemical_id: int
    quantity: float

class ReactionRequest(BaseModel):
    reactants: List[ReactantInput]
    environment: Environment = Environment.NORMAL
    catalyst_id: Optional[int] = None

class ProductOutput(BaseModel):
    chemical_id: Optional[int] = None
    molecular_formula: str
    common_name: str
    quantity: float
    is_soluble: bool = Field(..., description="Whether the product is soluble in the reaction environment")

class ProductOutputDSPy(BaseModel):
    molecular_formula: str = Field(..., description="The normalized formula of the product i.e proper capitalization and lowercase. like 'NaHSO4' for sodium bisulfate.")
    common_name: str = Field(..., description="The common name of the product chemical, e.g., 'Water', 'Sodium chloride'")
    quantity: float
    is_soluble: bool = Field(..., description="Whether the product is soluble in the reaction environment")

class ReactionPrediction(BaseModel):
    products: List[ProductOutput]
    effects: List[Effect]
    explanation: str
    is_world_first: bool = False

    # DEPRECATED: Use ProductOutputDSPy instead
    state_of_product: Optional[str] = Field(
        None,
        description="The state of matter of the products, if applicable. Can be 'solid', 'liquid', 'gas', or 'plasma'."
    )

class ReactionPredictionDSPyOutput(BaseModel):
    products: List[ProductOutputDSPy]
    effects: List[Effect]
    explanation: str

class UserReactionStatsSchema(BaseModel):
    """Schema for user reaction statistics response."""
    total_reactions: int
    total_discoveries: int

    class Config:
        from_attributes = True