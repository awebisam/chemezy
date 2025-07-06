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
    quantity: float

class ProductOutputDSPy(BaseModel):
    molecular_formula: str
    quantity: float

class ReactionPrediction(BaseModel):
    products: List[ProductOutput]
    state_of_product: str
    effects: List[Effect]
    explanation: str
    is_world_first: bool = False

class ReactionPredictionDSPyOutput(BaseModel):
    products: List[ProductOutputDSPy]
    state_of_product: str
    effects: List[Effect]
    explanation: str