from typing import List, Optional, Tuple

import dspy
from sqlmodel import Session, select, func, delete

from app.core.config import settings
from app.core.dspy_manager import is_dspy_configured
from app.models.chemical import Chemical
from app.schemas.chemical import ChemicalCreate, ChemicalGenerated
from app.services.dspy_extended import ChemistryReasoningModule
from app.services.dspy_signatures import GenerateChemicalProperties


class ChemicalPropertyGenerator(dspy.Module):
    """A DSPy Module for generating chemical properties."""

    def __init__(self):
        super().__init__()
        self.generate_properties = ChemistryReasoningModule(
            GenerateChemicalProperties,
            reflect=True,
            feedback_retries=settings.dspy_retries
        )

    def forward(self, molecular_formula: str) -> dspy.Prediction:
        """
        Executes the generation pipeline.
        The TypedCOTPredict module will return a Pydantic model inside the prediction object.
        """
        return self.generate_properties(molecular_formula=molecular_formula)


class ChemicalService:
    """Service for managing chemicals."""

    def __init__(self, db: Session):
        self.db = db
        if is_dspy_configured():
            self.property_generator: Optional[ChemicalPropertyGenerator] = ChemicalPropertyGenerator(
            )
        else:
            self.property_generator = None

    async def get(self, chemical_id: int) -> Optional[Chemical]:
        """Get a chemical by its ID."""
        return self.db.get(Chemical, chemical_id)

    async def get_by_molecular_formula(self, molecular_formula: str) -> Optional[Chemical]:
        """Get a chemical by its molecular formula."""
        statement = select(Chemical).where(
            Chemical.molecular_formula == molecular_formula)
        return self.db.exec(statement).first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[Chemical], int]:
        """Get all chemicals with pagination."""
        statement = select(Chemical).offset(skip).limit(limit)
        count_statement = select(func.count(Chemical.id))

        results = self.db.exec(statement).all()
        total = self.db.exec(count_statement).one()

        return results, total

    async def delete(self, chemical_id: int) -> Optional[Chemical]:
        """Delete a chemical."""
        chemical = await self.get(chemical_id)
        if chemical:
            self.db.delete(chemical)
            self.db.commit()
        return chemical

    async def create_chemical(self, chemical_in: ChemicalCreate) -> Chemical:
        """Create a new chemical."""
        existing_chemical = await self.get_by_molecular_formula(chemical_in.molecular_formula)
        if existing_chemical:
            raise ValueError(
                f"Chemical with formula {chemical_in.molecular_formula} already exists.")

        if not self.property_generator:
            raise RuntimeError(
                "Chemical property generator is not configured. Cannot create new chemicals.")

        try:
            prediction = self.property_generator(
                molecular_formula=chemical_in.molecular_formula)

            generated_data = ChemicalGenerated(
                common_name=prediction.common_name,
                state_of_matter=prediction.state_of_matter,
                color=prediction.color,
                density=prediction.density,
                properties=prediction.properties,
            )
        except Exception as e:
            print(
                f"ERROR: Failed to generate chemical properties for {chemical_in.molecular_formula}: {e}")
            raise RuntimeError(
                "Failed to generate properties from LLM.") from e

        db_chemical = Chemical(
            molecular_formula=chemical_in.molecular_formula,
            **generated_data.model_dump()
        )

        self.db.add(db_chemical)
        self.db.commit()
        self.db.refresh(db_chemical)
        return db_chemical

    def clear_all_chemicals(self) -> dict[str, any]:
        """Clears all chemicals from the database."""
        
        deleted_chemicals_count = self.db.exec(delete(Chemical)).rowcount
        self.db.commit()

        return {"message": f"Successfully deleted {deleted_chemicals_count} chemicals."}
