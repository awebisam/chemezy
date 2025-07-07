import hashlib
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from sqlmodel import Session, select

import dspy
from app.core.config import settings
from app.models.reaction import ReactionCache, Discovery
from app.models.user import User
from app.services.pubchem_service import PubChemService
from app.schemas.reaction import ReactionResponse, ChemicalProduct


class ReactionPrediction(dspy.Signature):
    """Predicts the outcome of a chemical reaction based on provided context."""

    reactants = dspy.InputField(desc="List of chemical formulas reacting, e.g., ['H2O', 'NaCl']")
    environment = dspy.InputField(desc="The environmental conditions, e.g., 'Earth (Normal)'")
    context = dspy.InputField(desc="Factual data from PubChem about reactants.")
    
    structured_json_output = dspy.OutputField(
        desc="A single, valid JSON object with no extra text or explanations.",
        prefix='''{
            "products": [{"formula": str, "name": str, "state": str}],
            "effects": [str],
            "state_change": str | null,
            "description": str
        }'''
    )


class ReactionEngineService:
    """Core service for processing chemical reactions using RAG."""
    
    def __init__(self):
        self.pubchem_service = PubChemService()
        self._setup_dspy()
        
    def _setup_dspy(self):
        """Initialize DSPy with LLM configuration."""
        if settings.openai_api_key:
            lm = dspy.OpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key
            )
            dspy.settings.configure(lm=lm)
            
            # Create the DSPy program
            self.reaction_predictor = dspy.ChainOfThought(ReactionPrediction)
        else:
            print("Warning: OpenAI API key not configured. Using mock predictions.")
            self.reaction_predictor = None
    
    def _generate_cache_key(self, chemicals: List[str], environment: str) -> str:
        """Generate a deterministic cache key from inputs."""
        # Sort chemicals to ensure deterministic key
        sorted_chemicals = sorted(chemicals)
        key_data = {
            "chemicals": sorted_chemicals,
            "environment": environment
        }
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
        Predict chemical reaction outcome using cache-first, then RAG approach.
        
        Args:
            chemicals: List of chemical formulas
            environment: Environmental conditions
            user_id: ID of the user making the request
            db: Database session
            
        Returns:
            ReactionResponse with prediction results
        """
        request_id = str(uuid.uuid4())
        cache_key = self._generate_cache_key(chemicals, environment)
        
        # Step 1: Check cache first
        cached_result = db.exec(
            select(ReactionCache).where(ReactionCache.cache_key == cache_key)
        ).first()
        
        if cached_result:
            # Check for world-first discoveries
            is_world_first = await self._check_world_first_effects(
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
        
        # Step 2: Use RAG to generate new prediction
        prediction_result = await self._generate_prediction(chemicals, environment)
        
        # Step 3: Save to cache
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
        db.commit()
        db.refresh(cache_entry)
        
        # Step 4: Check for world-first discoveries
        is_world_first = await self._check_world_first_effects(
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
    
    async def _generate_prediction(self, chemicals: List[str], environment: str) -> Dict:
        """Generate prediction using DSPy RAG pipeline."""
        # Step 1: Retrieve context from PubChem
        context_data = await self.pubchem_service.get_multiple_compounds_data(chemicals)
        context_str = json.dumps(context_data, indent=2)
        
        # Step 2: Use DSPy to generate prediction
        if self.reaction_predictor:
            try:
                result = self.reaction_predictor(
                    reactants=chemicals,
                    environment=environment,
                    context=context_str
                )
                
                # Parse the JSON output
                prediction_json = json.loads(result.structured_json_output)
                return prediction_json
                
            except Exception as e:
                print(f"Error in DSPy prediction: {str(e)}")
                return self._get_fallback_prediction(chemicals, environment)
        else:
            return self._get_fallback_prediction(chemicals, environment)
    
    def _get_fallback_prediction(self, chemicals: List[str], environment: str) -> Dict:
        """Provide fallback prediction when DSPy is not available."""
        return {
            "products": [
                {
                    "formula": "H2O",
                    "name": "Water",
                    "state": "liquid"
                }
            ],
            "effects": ["mixing", "temperature_change"],
            "state_change": None,
            "description": f"Chemical reaction between {', '.join(chemicals)} in {environment} environment. This is a fallback prediction - configure OpenAI API key for full functionality."
        }
    
    async def _check_world_first_effects(
        self, 
        effects: List[str], 
        user_id: int, 
        reaction_cache_id: int, 
        db: Session
    ) -> bool:
        """Check if any effects are world-first discoveries."""
        world_first = False
        
        for effect in effects:
            # Check if this effect has been discovered before
            existing_discovery = db.exec(
                select(Discovery).where(Discovery.effect == effect)
            ).first()
            
            if not existing_discovery:
                # This is a world-first discovery!
                discovery = Discovery(
                    effect=effect,
                    discovered_by=user_id,
                    reaction_cache_id=reaction_cache_id
                )
                db.add(discovery)
                world_first = True
        
        if world_first:
            db.commit()
        
        return world_first