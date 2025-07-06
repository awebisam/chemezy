import hashlib
import json
import uuid
import asyncio
from typing import List, Dict, Optional, Any
from sqlmodel import Session, select

import dspy
from app.core.config import settings
from app.models.reaction import ReactionCache, Discovery
from app.services.pubchem_service import PubChemService
from app.schemas.reaction import ReactionResponse, ChemicalProduct

# ==============================================================================
# 1. DSPy Signature: The Core Instruction for the Language Model
# ==============================================================================

class ReactionPrediction(dspy.Signature):
    """
    You are a computational chemist AI. Your task is to predict the outcome of a chemical reaction
    with scientific rigor, acting as the core intelligence for a chemistry simulation engine.
    
    Given a set of reactants, environmental conditions, and factual data from the PubChem database,
    you must perform a step-by-step analysis to generate a plausible and scientifically-grounded prediction.
    
    Your reasoning process MUST follow these steps:
    1.  **Analyze Reactants**: Examine the properties of each reactant from the provided `context`.
    2.  **Identify Potential Pathways**: Consider possible reaction types (e.g., acid-base, redox, precipitation).
    3.  **Evaluate Feasibility**: Assess the likelihood of these pathways based on the `environment` (temperature, pressure) and chemical principles.
    4.  **Determine Products**: Predict the most likely chemical products formed.
    5.  **Describe Phenomena**: Detail the observable `effects` (e.g., gas evolution, color change, heat release).
    6.  **Synthesize Explanation**: Write a clear, concise `description` of the reaction mechanism and outcome.
    
    Your final output MUST be a single, valid JSON object and nothing else. Do not include any explanatory text
    outside of the JSON structure.
    """

    reactants = dspy.InputField(
        desc="A list of chemical formulas for the reacting substances.",
        format="['H2O', 'NaCl']"
    )

    environment = dspy.InputField(
        desc="A string describing the physical conditions of the reaction.",
        format="'Aqueous solution at 25°C and 1 atm pressure.'"
    )

    context = dspy.InputField(
        desc="A JSON string containing factual data about the reactants, retrieved from the PubChem database. This is your primary source of truth.",
        format='{"H2O": {"molecular_weight": 18.015, ...}, "NaCl": {"molecular_weight": 58.44, ...}}'
    )

    structured_json_output = dspy.OutputField(
        desc="A single, valid JSON object representing the reaction prediction. Adhere strictly to the specified format.",
        # The `prefix` helps guide the model to produce the correct JSON structure.
        prefix='''{
  "products": [
    {
      "formula": "string",
      "name": "string", 
      "state": "solid|liquid|gas|aqueous|plasma"
    }
  ],
  "effects": ["string"],
  "state_change": "string | null",
  "description": "string"
}'''
    )

# ==============================================================================
# 2. DSPy Module: A Reusable, Programmatic Wrapper for the Signature
# ==============================================================================

class RAGReactionPredictor(dspy.Module):
    """A DSPy Module that orchestrates the Retrieval-Augmented Generation pipeline."""
    def __init__(self):
        super().__init__()
        # ChainOfThought is a powerful module that forces the LLM to reason before answering.
        self.generate_prediction = dspy.ChainOfThought(ReactionPrediction)

    def forward(self, reactants: List[str], environment: str, context: str) -> dspy.Prediction:
        """
        Executes the RAG pipeline.
        
        Args:
            reactants: List of chemical formulas.
            environment: Description of the reaction environment.
            context: JSON string of factual data about reactants.

        Returns:
            A dspy.Prediction object containing the structured JSON output.
        """
        return self.generate_prediction(
            reactants=reactants,
            environment=environment,
            context=context
        )

# ==============================================================================
# 3. Reaction Engine Service: The Main Business Logic
# ==============================================================================

class ReactionEngineService:
    """
    Core service for processing chemical reactions using a cache-first, RAG-second approach.
    This service is designed to be robust, with multiple layers of fallbacks.
    """

    def __init__(self):
        self.pubchem_service = PubChemService()
        self.reaction_predictor = self._setup_dspy()

    def _setup_dspy(self) -> Optional[RAGReactionPredictor]:
        """
        Configures DSPy with the appropriate language model, prioritizing Azure OpenAI.
        Returns a configured DSPy module or None if no configuration is available.
        """
        lm_provider = None
        
        # Priority 1: Azure OpenAI
        if all([settings.azure_openai_key, settings.azure_openai_endpoint, settings.azure_openai_deployment_name]):
            try:
                lm_provider = dspy.AzureOpenAI(
                    api_base=settings.azure_openai_endpoint,
                    api_version=settings.azure_openai_api_version,
                    model=settings.azure_openai_deployment_name,
                    api_key=settings.azure_openai_key,
                    model_type="chat"
                )
                print("INFO: DSPy configured with Azure OpenAI.")
            except Exception as e:
                print(f"WARNING: Azure OpenAI configuration failed: {e}. Trying standard OpenAI.")

        # Priority 2: Standard OpenAI
        if not lm_provider and settings.openai_api_key:
            try:
                lm_provider = dspy.OpenAI(
                    model=settings.openai_model,
                    api_key=settings.openai_api_key
                )
                print("INFO: DSPy configured with standard OpenAI.")
            except Exception as e:
                print(f"WARNING: Standard OpenAI configuration failed: {e}.")
        
        if lm_provider:
            dspy.settings.configure(lm=lm_provider)
            return RAGReactionPredictor()

        print("CRITICAL: No LLM provider configured. The engine will rely solely on physics-based fallbacks.")
        return None

    def _generate_cache_key(self, chemicals: List[str], environment: str) -> str:
        """Generates a deterministic SHA256 cache key from sorted inputs."""
        sorted_chemicals = sorted(c.strip().upper() for c in chemicals)
        key_data = {"chemicals": sorted_chemicals, "environment": environment.strip()}
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def predict_reaction(
        self,
        chemicals: List[str],
        environment: str,
        user_id: int,
        db: Session
    ) -> ReactionResponse:
        """
        Orchestrates the full reaction prediction process.
        This method is designed to be part of a single database transaction managed by the API endpoint.
        """
        request_id = str(uuid.uuid4())
        cache_key = self._generate_cache_key(chemicals, environment)

        # Layer 1: Check Cache
        cached_result = db.exec(
            select(ReactionCache).where(ReactionCache.cache_key == cache_key)
        ).first()

        if cached_result:
            # A discovery can still be "world-first" for a new user, even on a cached reaction.
            is_world_first = await self._check_and_log_discoveries(
                cached_result.effects, user_id, cached_result.id, db
            )
            return ReactionResponse(
                request_id=request_id,
                products=[ChemicalProduct(**p) for p in cached_result.products],
                effects=cached_result.effects,
                state_change=cached_result.state_change,
                description=cached_result.description,
                is_world_first=is_world_first
            )

        # Layer 2: Generate New Prediction via RAG
        prediction_result = await self._generate_prediction_with_fallbacks(chemicals, environment)

        # Persist the new prediction to the cache.
        # The commit will be handled by the calling API route to ensure atomicity.
        cache_entry = ReactionCache(
            cache_key=cache_key,
            reactants=chemicals,
            environment=environment,
            products=prediction_result["products"],
            effects=prediction_result["effects"],
            state_change=prediction_result["state_change"],
            description=prediction_result["description"],
            user_id=user_id
        )
        db.add(cache_entry)
        db.flush()  # Use flush to get the ID for the discovery log without committing.

        if cache_entry.id is None:
            # This should ideally never happen if the DB is configured correctly.
            raise RuntimeError("Failed to obtain a cache entry ID after flushing the session.")

        # Log any world-first discoveries from this new prediction.
        is_world_first = await self._check_and_log_discoveries(
            prediction_result["effects"], user_id, cache_entry.id, db
        )

        return ReactionResponse(
            request_id=request_id,
            products=[ChemicalProduct(**p) for p in prediction_result["products"]],
            effects=prediction_result["effects"],
            state_change=prediction_result["state_change"],
            description=prediction_result["description"],
            is_world_first=is_world_first
        )

    async def _generate_prediction_with_fallbacks(self, chemicals: List[str], environment: str) -> Dict[str, Any]:
        """
        Attempts to generate a prediction using the DSPy RAG pipeline, with multiple fallback layers.
        """
        # Fallback Layer 1: Factual Context Retrieval
        context_data = await self._get_chemical_context_with_retries(chemicals)
        context_str = json.dumps(context_data, indent=2)

        # Main Path: DSPy RAG Prediction
        if self.reaction_predictor:
            for attempt in range(settings.dspy_retries):
                try:
                    result = self.reaction_predictor(
                        reactants=chemicals,
                        environment=environment,
                        context=context_str
                    )
                    prediction_json = self._validate_and_parse_prediction(result.structured_json_output)
                    if prediction_json:
                        print(f"INFO: DSPy prediction successful on attempt {attempt + 1}.")
                        return prediction_json
                    
                    print(f"WARNING: DSPy output validation failed on attempt {attempt + 1}.")
                except Exception as e:
                    print(f"ERROR: DSPy prediction failed on attempt {attempt + 1}: {e}")
                
                await asyncio.sleep(1) # Wait before retrying

        # Fallback Layer 2: Physics-Based Heuristics
        print("INFO: Falling back to physics-based heuristic prediction.")
        return self._get_physics_based_fallback(chemicals, environment, context_data)

    async def _get_chemical_context_with_retries(self, chemicals: List[str]) -> Dict[str, Any]:
        """Retrieves chemical data from PubChem with exponential backoff."""
        for attempt in range(settings.pubchem_retries):
            try:
                context_data = await self.pubchem_service.get_multiple_compounds_data(chemicals)
                if context_data and all(v is not None for v in context_data.values()):
                    return context_data
            except Exception as e:
                print(f"ERROR: PubChem API call failed on attempt {attempt + 1}: {e}")
                if attempt < settings.pubchem_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
        
        print("CRITICAL: All PubChem API attempts failed. Proceeding with no factual context.")
        return {chem: {"error": "Failed to retrieve data"} for chem in chemicals}

    def _validate_and_parse_prediction(self, json_output: str) -> Optional[Dict[str, Any]]:
        """Safely parses and validates the structure of the LLM's JSON output."""
        try:
            # The LLM can sometimes wrap its output in markdown ```json ... ```
            if json_output.strip().startswith("```json"):
                json_output = json_output.strip()[7:-3]

            prediction = json.loads(json_output)

            # Structural validation
            if not isinstance(prediction, dict) or not all(k in prediction for k in ["products", "effects", "description"]):
                return None
            if not isinstance(prediction["products"], list) or not isinstance(prediction["effects"], list):
                return None
            for prod in prediction["products"]:
                if not all(k in prod for k in ["formula", "name", "state"]):
                    return None
            
            # Ensure optional field exists
            prediction.setdefault("state_change", None)
            return prediction
        except (json.JSONDecodeError, TypeError) as e:
            print(f"ERROR: Failed to validate or parse LLM JSON output: {e}")
            return None

    def _get_physics_based_fallback(self, chemicals: List[str], environment: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provides a deterministic, rule-based fallback prediction."""
        # This can be expanded with more sophisticated heuristic rules.
        products = [{"formula": chem, "name": "Mixed Substance", "state": "aqueous"} for chem in chemicals]
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
        """
        Checks if any effects are world-first discoveries and logs them.
        This function does NOT commit the transaction, allowing it to be part of a larger atomic operation.
        """
        is_world_first = False
        for effect in effects:
            # Check if this effect has ever been discovered by anyone.
            existing_discovery = db.exec(
                select(Discovery).where(Discovery.effect == effect)
            ).first()

            if not existing_discovery:
                is_world_first = True
                discovery = Discovery(
                    effect=effect,
                    discovered_by=user_id,
                    reaction_cache_id=reaction_cache_id
                )
                db.add(discovery)
                print(f"INFO: World-first discovery logged for effect '{effect}' by user {user_id}.")
        
        return is_world_first
