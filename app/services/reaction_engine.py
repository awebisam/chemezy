import hashlib
import json
import uuid
import asyncio
from typing import Optional
from sqlmodel import Session, select

import dspy
from app.core.config import settings
from app.models.reaction import ReactionCache, Discovery
from app.services.pubchem_service import PubChemService
from app.schemas.reaction import ReactionResponse, ChemicalProduct, ReactionPredictionOutput


class ReactionPrediction(dspy.Signature):
    """
    You are a computational chemist AI. Your task is to predict the outcome of a chemical reaction
    with scientific rigor, acting as the core intelligence for a chemistry simulation engine.

    Given a set of reactants, environmental conditions, and factual data from the PubChem database,
    you must perform a step-by-step analysis to generate a plausible and scientifically-grounded prediction.

    Your reasoning process MUST follow these steps:
    1.  Analyze Reactants: Examine the properties of each reactant from the provided `context`.
    2.  Identify Potential Pathways: Consider possible reaction types (e.g., acid-base, redox).
    3.  Evaluate Feasibility: Assess likelihood based on `environment` and chemical principles.
    4.  Determine Products: Predict the most likely chemical products.
    5.  Describe Phenomena: Detail observable `effects`.
    6.  Synthesize Explanation: Write a clear `description` of the reaction.

    CRITICAL: You must return ONLY a valid JSON object that matches the ReactionPredictionOutput schema.
    Do NOT include markdown formatting, code blocks, or any explanatory text.
    The JSON must have these exact fields:
    - "products": array of objects with "formula", "name", "state" fields
    - "effects": array of strings describing observable phenomena
    - "state_change": string or null for overall state change
    - "description": string explaining the reaction mechanism and outcome
    """

    reactants: str = dspy.InputField(
        desc="A comma-separated string of chemical formulas for the reacting substances."
    )
    environment: str = dspy.InputField(
        desc="A string describing the physical conditions of the reaction."
    )
    context: str = dspy.InputField(
        desc="A stringified JSON containing factual data about the reactants from PubChem. This is your primary source of truth."
    )
    # The OutputField now directly references the Pydantic model for robust, typed output.
    reaction_prediction: ReactionPredictionOutput = dspy.OutputField(
        desc="A structured prediction of the reaction outcome, conforming to the Pydantic schema."
    )


class RAGReactionPredictor(dspy.Module):
    """A DSPy Module that orchestrates the Retrieval-Augmented Generation pipeline."""

    def __init__(self):
        super().__init__()
        # ChainOfThought works seamlessly with Pydantic-based signatures.
        self.generate_prediction = dspy.ChainOfThought(ReactionPrediction)

    def forward(self, reactants: str, environment: str, context: str) -> ReactionPredictionOutput:
        """Executes the RAG pipeline."""
        return self.generate_prediction(
            reactants=reactants,
            environment=environment,
            context=context
        )


class ReactionEngineService:
    """Core service for processing chemical reactions using a cache-first, RAG-second approach."""

    def __init__(self):
        self.pubchem_service = PubChemService()
        self.reaction_predictor = self._setup_dspy()

    def _setup_dspy(self) -> Optional[RAGReactionPredictor]:
        """Configures DSPy with the appropriate language model."""
        lm_provider = None
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
                print(f"WARNING: Azure OpenAI configuration failed: {e}")

        if lm_provider:
            dspy.settings.configure(lm=lm_provider)
            # Enable better Pydantic model handling
            dspy.settings.configure(parse_json=True)

            return RAGReactionPredictor()

        print("CRITICAL: No LLM provider configured. The engine will rely solely on physics-based fallbacks.")
        return None

    def _generate_cache_key(self, chemicals: list[str], environment: str) -> str:
        """Generates a deterministic SHA256 cache key from sorted inputs."""
        sorted_chemicals = sorted(c.strip().upper() for c in chemicals)
        key_data = {"chemicals": sorted_chemicals,
                    "environment": environment.strip()}
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    async def predict_reaction(
        self,
        chemicals: list[str],
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

        # RAG generation now returns a dict from a Pydantic model.
        prediction_dict, from_llm = await self._generate_prediction_with_fallbacks(chemicals, environment)

        if from_llm:
            cache_entry = ReactionCache(
                cache_key=cache_key,
                reactants=chemicals,
                environment=environment,
                # Ensure products are dicts
                products=[p.model_dump() for p in prediction_dict["products"]],
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

        # Create the final response using the Pydantic models directly.
        return ReactionResponse(
            request_id=request_id,
            products=prediction_dict["products"],
            effects=prediction_dict["effects"],
            state_change=prediction_dict["state_change"],
            description=prediction_dict["description"],
            is_world_first=is_world_first
        )

    async def _generate_prediction_with_fallbacks(self, chemicals: list[str], environment: str) -> tuple[dict[str, object], bool]:
        """Attempts prediction using DSPy RAG, with fallbacks. Returns a dictionary and if the prediction was from the LLM or the fallback."""
        context_data = await self._get_chemical_context_with_retries(chemicals)
        context_str = json.dumps(context_data, indent=2)

        # Convert the list of reactants to a comma-separated string
        reactants_str = ", ".join(chemicals)
        if self.reaction_predictor:
            for attempt in range(settings.dspy_retries):
                try:
                    result = self.reaction_predictor(
                        reactants=reactants_str,
                        environment=environment,
                        context=context_str
                    )
                    prediction_model = result.reaction_prediction
                    print(
                        f"\n\n\nprediction_model type: {type(prediction_model)}")
                    print(f"prediction_model: {prediction_model}")
                    print(
                        f"INFO: DSPy prediction and validation successful on attempt {attempt + 1}.")
                    # Handle string output from LLM
                    if isinstance(prediction_model, str):
                        # Extract JSON from markdown-formatted string if needed
                        cleaned_json = prediction_model.strip()
                        if cleaned_json.startswith('```json'):
                            cleaned_json = cleaned_json[7:]  # Remove ```json
                        if cleaned_json.endswith('```'):
                            cleaned_json = cleaned_json[:-3]  # Remove ```

                        try:
                            prediction_dict = json.loads(cleaned_json.strip())
                        except json.JSONDecodeError as e:
                            print(f"JSON parsing failed: {e}")
                            print(f"Attempting to fix truncated JSON...")
                            # Try to complete truncated JSON
                            fixed_json = self._fix_truncated_json(
                                cleaned_json.strip())
                            prediction_dict = json.loads(fixed_json)
                    else:
                        prediction_dict = prediction_model.model_dump() if hasattr(
                            prediction_model, "model_dump") else dict(prediction_model)
                    return prediction_dict, True
                except Exception as e:
                    # This now catches LLM failures, network issues, or Pydantic validation errors from DSPy.
                    print(
                        f"ERROR: DSPy prediction or validation failed on attempt {attempt + 1}: {e}")
                    await asyncio.sleep(1)

        print("INFO: Falling back to physics-based heuristic prediction.")
        fallback_data = self._get_physics_based_fallback(
            chemicals, environment)
        # Ensure the fallback also conforms to the expected dictionary structure
        validated_fallback = ReactionPredictionOutput(**fallback_data)
        return validated_fallback.model_dump(), False

    async def _get_chemical_context_with_retries(self, chemicals: list[str]) -> dict[str, object]:
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

    def _fix_truncated_json(self, json_str: str) -> str:
        """Attempts to fix truncated JSON by completing missing parts."""
        # Count opening and closing brackets/braces
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')

        # Add missing closing brackets/braces
        fixed_json = json_str
        for _ in range(open_brackets - close_brackets):
            fixed_json += ']'
        for _ in range(open_braces - close_braces):
            fixed_json += '}'

        # If we have an unterminated string, try to close it
        if fixed_json.count('"') % 2 != 0:
            # Find the last quote and add a closing quote
            last_quote_pos = fixed_json.rfind('"')
            if last_quote_pos != -1:
                # Check if we're in the middle of a string
                if not fixed_json[last_quote_pos:].strip().startswith('"'):
                    fixed_json += '"'

        return fixed_json

    # THIS METHOD IS NO LONGER NEEDED AND HAS BEEN REMOVED.
    # def _validate_and_parse_prediction(self, json_output: str) -> Optional[Dict[str, Any]]:

    def _get_physics_based_fallback(self, chemicals: list[str], environment: str) -> dict[str, object]:
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
        effects: list[str],
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
