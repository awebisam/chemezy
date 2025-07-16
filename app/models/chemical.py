import enum
from typing import Any, Dict, Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, SQLModel


class StateOfMatter(str, enum.Enum):
    SOLID = "solid"
    LIQUID = "liquid"
    GAS = "gas"
    PLASMA = "plasma"
    AQUEOUS = "aqueous"


class Chemical(SQLModel, table=True):
    __tablename__ = "chemicals"
    __table_args__ = (UniqueConstraint("molecular_formula", "common_name", name="unique_molecular_formula_common_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    molecular_formula: str = Field(index=True, max_length=255)
    common_name: str = Field(max_length=255)
    state_of_matter: StateOfMatter
    color: str = Field(max_length=50)
    density: float
    properties: Dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON))
