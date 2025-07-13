import json
import hashlib
from typing import List, Dict, Any

from sqlmodel import Session, select, func, delete
import dspy

from app.core.config import settings
from app.models.chemical import Chemical
from app.models.reaction import ReactionCache, Discovery
from app.schemas.reaction import ReactionRequest, ReactionPrediction, ProductOutput, ReactionPredictionDSPyOutput
from app.schemas.chemical import ChemicalCreate
from app.services.chemical_service import ChemicalService
from app.services.dspy_extended import ChemistryReasoningModule
from app.services.dspy_signatures import PredictReactionProductsAndEffects

class ReactionPredictionModule(dspy.Module):
    """DSPy module for reaction prediction."""
    def __init__(self):
        super().__init__()
        self.generate_prediction = ChemistryReasoningModule(
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
        self, request: ReactionRequest, user_id: int
    ) -> ReactionPrediction:
        """Predicts the outcome of a chemical reaction, utilizing cache and discovery."""
        reactants = self._get_reactants_from_db(request.reactants)
        reactants_data_str = self._serialize_reactants(reactants, request.reactants)

        catalyst_data_str = "None"
        if request.catalyst_id:
            catalyst = self._get_catalyst_from_db(request.catalyst_id)
            if catalyst:
                catalyst_data_str = json.dumps(catalyst.model_dump())

        # Generate a cache key
        cache_key = self._generate_cache_key(reactants_data_str, request.environment.value, catalyst_data_str)

        # Check cache first
        cached_reaction = self.db.exec(
            select(ReactionCache).where(ReactionCache.cache_key == cache_key)
        ).first()

        if cached_reaction:
            # Process cached result
            prediction = ReactionPrediction(
                products=cached_reaction.products,
                effects=cached_reaction.effects,
                state_of_product=cached_reaction.state_of_product,
                explanation=cached_reaction.explanation,
                is_world_first=False # Assume not world first if from cache, will be updated by _check_and_log_discoveries
            )
            is_world_first = await self._check_and_log_discoveries(
                prediction.effects, user_id, cached_reaction.id, self.db
            )
            prediction.is_world_first = is_world_first
            return prediction

        # If not in cache, predict using DSPy
        if not self.reaction_predictor:
            # Fallback prediction for non-configured DSPy
            fallback_pred = self._fallback_prediction(reactants)
            # No cache for fallback, so no world-first check here
            return fallback_pred

        prediction_dspy_output = self.reaction_predictor(
            reactants_data=reactants_data_str, 
            environment=request.environment.value,
            catalyst_data=catalyst_data_str
        ).prediction
        
        validated_prediction = await self._process_and_validate_prediction(
            prediction_dspy_output
        )

        # Save new prediction to cache
        new_reaction_cache = ReactionCache(
            cache_key=cache_key,
            reactants=[r.molecular_formula for r in reactants],
            environment=request.environment.value,
            products=[p.model_dump() for p in validated_prediction.products],
            effects=[effect.model_dump() for effect in validated_prediction.effects],
            state_of_product=validated_prediction.state_of_product,
            explanation=validated_prediction.explanation,
            user_id=user_id
        )
        self.db.add(new_reaction_cache)
        self.db.commit()
        self.db.refresh(new_reaction_cache)

        # Check and log discoveries for newly generated reaction
        is_world_first = await self._check_and_log_discoveries(
            validated_prediction.effects, user_id, new_reaction_cache.id, self.db
        )
        validated_prediction.is_world_first = is_world_first
        
        return validated_prediction

    def _generate_cache_key(self, reactants_data_str: str, environment: str, catalyst_data_str: str) -> str:
        """Generates a deterministic cache key for a reaction."""
        # Sort reactants data to ensure consistent key generation
        sorted_reactants_data = json.dumps(json.loads(reactants_data_str), sort_keys=True)
        
        # Combine all relevant parameters into a single string
        key_string = f"{sorted_reactants_data}-{environment}-{catalyst_data_str}"
        
        # Hash the string to create a fixed-size cache key
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

    async def _check_and_log_discoveries(
        self, effects: List[str], user_id: int, reaction_cache_id: int, db: Session
    ) -> bool:
        """Checks if any effects are world-first discoveries and logs them."""
        is_world_first_overall = False
        for effect_obj in effects:
            effect_str = effect_obj.effect_type # Use the string representation of the effect
            existing_discovery = db.exec(
                select(Discovery).where(Discovery.effect == effect_str)
            ).first()

            if not existing_discovery:
                new_discovery = Discovery(
                    effect=effect_str,
                    discovered_by=user_id,
                    reaction_cache_id=reaction_cache_id
                )
                db.add(new_discovery)
                is_world_first_overall = True
        
        if is_world_first_overall:
            db.commit()
        
        return is_world_first_overall

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
        
        return ReactionPrediction(
            products=processed_products, 
            effects=prediction_dspy_output.effects,
            state_of_product=prediction_dspy_output.state_of_product,
            explanation=prediction_dspy_output.explanation
        )

    def _fallback_prediction(self, reactants: List[Chemical]) -> ReactionPrediction:
        """Provides a fallback prediction when the DSPy model is disabled."""
        products = [
            ProductOutput(
                chemical_id=r.id, 
                molecular_formula=r.molecular_formula, 
                quantity=1
            ) for r in reactants
        ]
        return ReactionPrediction(products=products, effects=[], state_of_product="unknown", explanation="Fallback prediction.")

    def get_user_reaction_cache(self, user_id: int) -> List[ReactionCache]:
        """Retrieves all cached reactions for a given user."""
        return self.db.exec(
            select(ReactionCache).where(ReactionCache.user_id == user_id)
        ).all()

    def get_user_reaction_stats(self, user_id: int) -> Dict[str, Any]:
        """Retrieves statistics about a user's reactions and discoveries."""
        total_reactions = self.db.exec(
            select(func.count(ReactionCache.id)).where(ReactionCache.user_id == user_id)
        ).one()

        total_discoveries = self.db.exec(
            select(func.count(Discovery.id)).where(Discovery.discovered_by == user_id)
        ).one()

        return {
            "total_reactions": total_reactions,
            "total_discoveries": total_discoveries
        }

    def clear_all_reactions(self) -> Dict[str, Any]:
        """Clears all reactions from the database."""
        
        deleted_reactions_count = self.db.exec(delete(ReactionCache)).rowcount
        self.db.commit()

        return {"message": f"Successfully deleted {deleted_reactions_count} reactions."}