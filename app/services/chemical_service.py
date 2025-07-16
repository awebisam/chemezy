from typing import List, Optional, Tuple
import json

import dspy
from sqlmodel import Session, select, func, delete

from app.core.config import settings
from app.core.dspy_manager import is_dspy_configured
from app.models.chemical import Chemical
from app.schemas.chemical import ChemicalCreate, ChemicalGenerated
from app.services.dspy_extended import ChemistryReasoningModule
from app.services.dspy_signatures import GenerateChemicalProperties
from app.services.pubchem_service import PubChemService


class ChemicalPropertyGenerator(dspy.Module):
    """A DSPy Module for generating chemical properties."""

    def __init__(self):
        super().__init__()
        self.generate_properties = ChemistryReasoningModule(
            GenerateChemicalProperties,
            reflect=True,
            feedback_retries=settings.dspy_retries
        )

    def forward(self, molecular_formula: str, context: str, pubchem_data: str) -> dspy.Prediction:
        """
        Executes the generation pipeline.
        The TypedCOTPredict module will return a Pydantic model inside the prediction object.
        """
        return self.generate_properties(molecular_formula=molecular_formula, context=context, pubchem_data=pubchem_data)


class ChemicalService:
    """Service for managing chemicals."""

    def __init__(self, db: Session):
        self.db = db
        self.pubchem_service = PubChemService()
        if is_dspy_configured():
            self.property_generator: Optional[ChemicalPropertyGenerator] = ChemicalPropertyGenerator(
            )
        else:
            self.property_generator = None

    async def get(self, chemical_id: int) -> Optional[Chemical]:
        """Get a chemical by its ID."""
        return self.db.get(Chemical, chemical_id)

    async def get_by_molecular_formula(self, molecular_formula: str) -> List[Chemical]:
        """Get chemicals by their molecular formula, case-insensitively."""
        statement = select(Chemical).where(
            Chemical.molecular_formula.ilike(molecular_formula))
        return self.db.exec(statement).all()

    async def get_by_formula_and_name(self, molecular_formula: str, common_name: str) -> Optional[Chemical]:
        """Get a chemical by its molecular formula and common name, case-insensitively."""
        statement = select(Chemical).where(
            Chemical.molecular_formula.ilike(molecular_formula),
            Chemical.common_name.ilike(common_name)
        )
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

    async def get_or_create_chemical(self, chemical_in: ChemicalCreate) -> Chemical:
        """Get or create a new chemical."""
        if not self.property_generator:
            raise RuntimeError(
                "Chemical property generator is not configured. Cannot create new chemicals.")

        try:
            # Step 1: Retrieve data from PubChem
            pubchem_data = await self.pubchem_service.get_compound_data(
                chemical_in.molecular_formula)

            # Step 2: Prepare context for LLM
            if pubchem_data:
                pubchem_context = json.dumps(pubchem_data)
            else:
                # Fallback context if PubChem data is not available
                pubchem_context = json.dumps({
                    "formula": chemical_in.molecular_formula,
                    "molecular_weight": None,
                    "h_bond_donors": 0,
                    "h_bond_acceptors": 0,
                    "source": "Not found in PubChem"
                })

            # Step 3: Generate properties using RAG approach
            context = chemical_in.context or "general compound"
            prediction = self.property_generator(
                molecular_formula=chemical_in.molecular_formula,
                context=context,
                pubchem_data=pubchem_context
            )

            generated_data = ChemicalGenerated(
                molecular_formula=prediction.normalized_formula.strip(),
                common_name=prediction.common_name.strip(),
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

        existing_chemical = await self.get_by_formula_and_name(
            generated_data.molecular_formula, generated_data.common_name
        )
        if existing_chemical:
            return existing_chemical

        db_chemical = Chemical(
            **generated_data.model_dump()
        )

        try:
            self.db.add(db_chemical)
            self.db.commit()
            self.db.refresh(db_chemical)
            return db_chemical
        except Exception as e:
            # Handle database constraint violations (race condition)
            self.db.rollback()
            if "UNIQUE constraint failed" in str(e):
                # Another process created the chemical, try to get it
                existing_chemical = await self.get_by_formula_and_name(
                    generated_data.molecular_formula, generated_data.common_name
                )
                if existing_chemical:
                    return existing_chemical
                else:
                    # This case is unlikely but good to handle
                    raise ValueError(
                        f"Chemical with formula {generated_data.molecular_formula} and name '{generated_data.common_name}' should exist but couldn't be found after a race condition."
                    )
            else:
                raise

    def clear_all_chemicals(self) -> dict[str, any]:
        """Clears all chemicals from the database."""
        
        deleted_chemicals_count = self.db.exec(delete(Chemical)).rowcount
        self.db.commit()

        return {"message": f"Successfully deleted {deleted_chemicals_count} chemicals."}
