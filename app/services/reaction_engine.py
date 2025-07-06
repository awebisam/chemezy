import hashlib
import json
import uuid
import asyncio
from typing import Optional, Dict, Any, List, Tuple

from sqlmodel import Session, select
import dspy

# Local application imports
from app.core.config import settings
from app.models.reaction import ReactionCache, Discovery
from app.services.pubchem_service import PubChemService
from app.schemas.reaction import ReactionResponse, ChemicalProduct, ReactionPredictionOutput

# Assuming dspy_extended provides a robust module for typed, retried predictions.
from app.services.dspy_extended import TypedCOTPredict
from app.services.dspy_signatures import ReactionPrediction


class RAGReactionPredictor(dspy.Module):
    """A DSPy Module that orchestrates the Retrieval-Augmented Generation pipeline."""

    def __init__(self):
        super().__init__()
        # Use the robust TypedCOTPredict for reliable Pydantic output.
        # This module is expected to handle parsing, validation, and retries internally.
        self.generate_prediction = TypedCOTPredict(
            ReactionPrediction,
            reflect=True,
            feedback_retries=settings.dspy_retries
        )

    def forward(self, reactants: str, environment: str, context: str) -> dspy.Prediction:
        """
        Executes the RAG pipeline.
        The TypedCOTPredict module is responsible for returning a valid Pydantic model
        within the `reaction_prediction` attribute of the output Prediction object.
        """
        return self.generate_prediction(
            reactants=reactants,
            environment=environment,
            context=context
        )


class ReactionEngineService:
    """Core service for processing chemical reactions using a cache-first, RAG-second approach."""

    def __init__(self):
        self.pubchem_service = PubChemService()
        if settings.dspy_enabled:
            self.reaction_predictor: Optional[RAGReactionPredictor] = RAGReactionPredictor(
            )
        else:
            self.reaction_predictor = None

    def _generate_cache_key(self, chemicals: List[str], environment: str) -> str:
        """Generates a deterministic SHA256 cache key from sorted inputs."""
        sorted_chemicals = sorted(c.strip().upper() for c in chemicals)
        key_data = {"chemicals": sorted_chemicals,
                    "environment": environment.strip()}
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def predict_reaction(
        self,
        chemicals: List[str],
        environment: str,
        user_id: int,
        db: Session
    ) -> ReactionResponse:
        """Orchestrates the full reaction prediction process."""
        request_id = str(uuid.uuid4())
        cache_key = self._generate_cache_key(chemicals, environment)

        cached_result = db.exec(select(ReactionCache).where(
            ReactionCache.cache_key == cache_key)).first()

        if cached_result:
            is_world_first = await self._check_and_log_discoveries(cached_result.effects, user_id, cached_result.id, db)
            return ReactionResponse(
                request_id=request_id,
                products=[ChemicalProduct(**p)
                          for p in cached_result.products],
                effects=cached_result.effects,
                state_change=cached_result.state_change,
                description=cached_result.description,
                is_world_first=is_world_first
            )

        prediction_dict, from_llm = await self._generate_prediction_with_fallbacks(chemicals, environment)

        if from_llm:
            cache_entry = ReactionCache(
                cache_key=cache_key,
                reactants=chemicals,
                environment=environment,
                products=prediction_dict["products"],
                effects=prediction_dict["effects"],
                state_change=prediction_dict["state_change"],
                description=prediction_dict["description"],
                user_id=user_id,
            )
            db.add(cache_entry)
            db.flush()
            is_world_first = await self._check_and_log_discoveries(prediction_dict["effects"], user_id, cache_entry.id, db)
        else:
            is_world_first = False

        return ReactionResponse(
            request_id=request_id,
            products=[ChemicalProduct(**p)
                      for p in prediction_dict["products"]],
            effects=prediction_dict["effects"],
            state_change=prediction_dict["state_change"],
            description=prediction_dict["description"],
            is_world_first=is_world_first
        )

    async def _generate_prediction_with_fallbacks(self, chemicals: List[str], environment: str) -> Tuple[Dict[str, Any], bool]:
        """
        Attempts prediction using the robust DSPy RAG module.
        This method fully trusts the `TypedCOTPredict` module to handle all parsing,
        validation, and retries. It expects either a valid Pydantic model or an exception.
        """
        context_data = await self._get_chemical_context_with_retries(chemicals)
        context_str = json.dumps(context_data, indent=2)
        reactants_str = ", ".join(chemicals)

        if self.reaction_predictor:
            try:
                result = self.reaction_predictor(
                    reactants=reactants_str,
                    environment=environment,
                    context=context_str
                )
                prediction_model = result.reaction_prediction

                if not isinstance(prediction_model, ReactionPredictionOutput):
                    raise TypeError(
                        f"DSPy module returned an unexpected type: {type(prediction_model)}")

                print("INFO: DSPy prediction and validation successful.")
                return prediction_model.model_dump(), True

            except Exception as e:
                print(
                    f"ERROR: DSPy `TypedCOTPredict` module failed after all retries: {e}")

        print("INFO: Falling back to physics-based heuristic prediction.")
        fallback_data = self._get_physics_based_fallback(
            chemicals, environment)
        validated_fallback = ReactionPredictionOutput(**fallback_data)
        return validated_fallback.model_dump(), False

    async def _get_chemical_context_with_retries(self, chemicals: List[str]) -> Dict[str, Any]:
        """Retrieves chemical data from PubChem with exponential backoff."""
        for attempt in range(settings.pubchem_retries):
            try:
                context_data = await self.pubchem_service.get_multiple_compounds_data(chemicals)
                if context_data and all(v is not None for v in context_data.values()):
                    return context_data
            except Exception as e:
                print(
                    f"ERROR: PubChem API call failed on attempt {attempt + 1}: {e}")
                if attempt < settings.pubchem_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        print(
            "CRITICAL: All PubChem API attempts failed. Proceeding with no factual context.")
        return {chem: {"error": "Failed to retrieve data"} for chem in chemicals}

    def _get_physics_based_fallback(self, chemicals: List[str], environment: str) -> Dict[str, Any]:
        """Provides a deterministic, rule-based fallback prediction as a dictionary."""
        products = [{"formula": chem, "name": "Mixed Substance",
                     "state": "aqueous"} for chem in chemicals]
        effects = ["physical_mixing", "no_reaction_observed"]
        description = (
            "A fallback prediction was generated as the primary AI reasoning core was unavailable. "
            "The substances are predicted to have mixed physically with no significant chemical reaction "
            f"under the specified conditions: {environment}."
        )
        return {
            "products": products,
            "effects": effects,
            "state_change": None,
            "description": description
        }

    async def _check_and_log_discoveries(
        self,
        effects: List[str],
        user_id: int,
        reaction_cache_id: int,
        db: Session
    ) -> bool:
        """Checks if any effects are world-first discoveries and logs them."""
        is_world_first = False
        for effect in effects:
            existing_discovery = db.exec(select(Discovery).where(
                Discovery.effect == effect)).first()
            if not existing_discovery:
                is_world_first = True
                discovery = Discovery(
                    effect=effect,
                    discovered_by=user_id,
                    reaction_cache_id=reaction_cache_id
                )
                db.add(discovery)
                print(
                    f"INFO: World-first discovery logged for effect '{effect}' by user {user_id}.")
        return is_world_first
