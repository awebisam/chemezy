import json
from typing import List, Dict, Any

from sqlmodel import Session, select
import dspy

from app.core.config import settings
from app.models.chemical import Chemical
from app.schemas.reaction import ReactionRequest, ReactionPrediction, ProductOutput, ReactionPredictionDSPyOutput
from app.schemas.chemical import ChemicalCreate
from app.services.chemical_service import ChemicalService
from app.services.dspy_extended import TypedCOTPredict
from app.services.dspy_signatures import PredictReactionProductsAndEffects

class ReactionPredictionModule(dspy.Module):
    """DSPy module for reaction prediction."""
    def __init__(self):
        super().__init__()
        self.generate_prediction = TypedCOTPredict(
            PredictReactionProductsAndEffects,
            reflect=True,
            feedback_retries=settings.dspy_retries
        )

    def forward(self, reactants_data: str, environment: str, catalyst_data: str) -> dspy.Prediction:
        return self.generate_prediction(reactants_data=reactants_data, environment=environment, catalyst_data=catalyst_data)

class ReactionService:
    """Service for predicting chemical reactions."""
    def __init__(self, db: Session):
        self.db = db
        self.chemical_service = ChemicalService(db)
        if settings.dspy_enabled:
            self.reaction_predictor = ReactionPredictionModule()
        else:
            self.reaction_predictor = None

    async def predict_reaction(
        self, request: ReactionRequest
    ) -> ReactionPrediction:
        """Predicts the outcome of a chemical reaction."""
        reactants = self._get_reactants_from_db(request.reactants)
        reactants_data_str = self._serialize_reactants(reactants, request.reactants)

        catalyst_data_str = "None"
        if request.catalyst_id:
            catalyst = self._get_catalyst_from_db(request.catalyst_id)
            if catalyst:
                catalyst_data_str = json.dumps(catalyst.model_dump())

        if not self.reaction_predictor:
            return self._fallback_prediction(reactants)

        prediction = self.reaction_predictor(
            reactants_data=reactants_data_str, 
            environment=request.environment.value,
            catalyst_data=catalyst_data_str
        )
        
        validated_prediction = await self._process_and_validate_prediction(
            prediction.prediction
        )
        return validated_prediction

    def _get_reactants_from_db(self, reactant_inputs: List[Dict[str, Any]]) -> List[Chemical]:
        """Fetches chemical data from the database for the given reactants."""
        chemical_ids = [r.chemical_id for r in reactant_inputs]
        statement = select(Chemical).where(Chemical.id.in_(chemical_ids))
        return self.db.exec(statement).all()

    def _get_catalyst_from_db(self, catalyst_id: int) -> Chemical | None:
        """Fetches chemical data from the database for the given catalyst."""
        return self.db.get(Chemical, catalyst_id)

    def _serialize_reactants(self, reactants: List[Chemical], reactant_inputs: List[Dict[str, Any]]) -> str:
        """Serializes reactant data into a JSON string for the DSPy model."""
        reactant_data_map = {r.id: r.model_dump() for r in reactants}
        serialized_reactants = []
        for r_input in reactant_inputs:
            if r_input.chemical_id in reactant_data_map:
                data = reactant_data_map[r_input.chemical_id]
                data["quantity"] = r_input.quantity
                serialized_reactants.append(data)
        return json.dumps(serialized_reactants)

    async def _process_and_validate_prediction(
        self, prediction_dspy_output: ReactionPredictionDSPyOutput
    ) -> ReactionPrediction:
        """Processes the prediction, creating new chemicals if necessary."""
        processed_products = []
        for p in prediction_dspy_output.products:
            chemical = await self.chemical_service.get_by_molecular_formula(
                p.molecular_formula
            )
            if not chemical:
                chemical = await self.chemical_service.create_chemical(ChemicalCreate(molecular_formula=p.molecular_formula))
            
            processed_products.append(
                ProductOutput(
                    chemical_id=chemical.id,
                    molecular_formula=p.molecular_formula,
                    quantity=p.quantity
                )
            )
        
        return ReactionPrediction(products=processed_products, effects=prediction_dspy_output.effects)

    def _fallback_prediction(self, reactants: List[Chemical]) -> ReactionPrediction:
        """Provides a fallback prediction when the DSPy model is disabled."""
        products = [
            ProductOutput(
                chemical_id=r.id, 
                molecular_formula=r.molecular_formula, 
                quantity=1
            ) for r in reactants
        ]
        return ReactionPrediction(products=products, effects=[])