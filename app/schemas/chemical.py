from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.chemical import StateOfMatter


class ChemicalCreate(BaseModel):
    molecular_formula: str = Field(
        ..., description="The molecular formula of the chemical, e.g., 'H2O'.")


class ChemicalGenerated(BaseModel):
    common_name: str = Field(...,
                             description="The common name of the chemical, e.g., 'Water'.")
    state_of_matter: StateOfMatter = Field(
        ..., description="The state of matter at room temperature.")
    color: str = Field(..., description="The color of the chemical.")
    density: float = Field(...,
                           description="The density of the chemical in g/cm³.")
    properties: Dict[str, Any] = Field(
        {}, description="Additional properties, e.g., melting point, boiling point.")


class ChemicalRead(BaseModel):
    id: int
    molecular_formula: str
    common_name: str
    state_of_matter: StateOfMatter
    color: str
    density: float
    properties: Dict[str, Any]

    class Config:
        from_attributes = True


class PaginatedChemicalRead(BaseModel):
    count: int
    results: List[ChemicalRead]
