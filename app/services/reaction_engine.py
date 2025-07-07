import hashlib
import json
import uuid
import asyncio
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
    """
    Predicts the outcome of a chemical reaction based on scientific data and thermodynamic principles.
    
    Use the provided chemical context to reason step-by-step about:
    1. Molecular interactions and bond formation/breaking
    2. Thermodynamic feasibility (enthalpy, entropy, Gibbs free energy)
    3. Reaction kinetics and activation energy barriers
    4. Environmental effects on reaction pathways
    
    Generate scientifically accurate predictions grounded in the provided factual data.
    """

    reactants = dspy.InputField(
        desc="Chemical formulas of reacting substances with their molecular properties",
        format="List of chemical formulas, e.g., ['H2O', 'NaCl', 'HCl']"
    )
    
    environment = dspy.InputField(
        desc="Physical conditions affecting the reaction",
        format="Environment description including temperature, pressure, medium, e.g., 'Earth (Normal)', 'High Temperature', 'Vacuum'"
    )
    
    context = dspy.InputField(
        desc="Scientific data about reactants including molecular properties, known reactions, and thermodynamic data from PubChem database",
        format="JSON object containing molecular weights, bond information, and chemical properties for each reactant"
    )
    
    structured_json_output = dspy.OutputField(
        desc="Valid JSON object containing reaction prediction with scientific justification. Must include products, observable effects, state changes, and detailed description.",
        format='''Exact JSON format required:
{
  "products": [
    {
      "formula": "chemical_formula",
      "name": "IUPAC_or_common_name", 
      "state": "solid|liquid|gas|aqueous|plasma"
    }
  ],
  "effects": ["observable_phenomenon_1", "observable_phenomenon_2"],
  "state_change": "phase_transition_description_or_null",
  "description": "detailed_scientific_explanation_with_mechanism"
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
        
        # Step 3: Save to cache (will be committed later with discoveries)
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
        db.flush()  # Get the ID without committing
        
        # Ensure we have a valid cache entry ID
        if cache_entry.id is None:
            raise ValueError("Failed to create cache entry")
        
        # Step 4: Check for world-first discoveries (adds to same transaction)
        is_world_first = await self._check_world_first_effects(
            prediction_result["effects"], user_id, cache_entry.id, db, commit=False
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
        """Generate prediction using DSPy RAG pipeline with robust fallback strategies."""
        # Step 1: Retrieve context from PubChem with retry logic
        context_data = await self._get_chemical_context_with_retries(chemicals)
        context_str = json.dumps(context_data, indent=2)
        
        # Step 2: Use DSPy to generate prediction with multiple fallback levels
        if self.reaction_predictor:
            # Try DSPy prediction with retries
            for attempt in range(3):
                try:
                    result = self.reaction_predictor(
                        reactants=chemicals,
                        environment=environment,
                        context=context_str
                    )
                    
                    # Validate and parse the JSON output
                    prediction_json = self._validate_and_parse_prediction(
                        result.structured_json_output, chemicals, environment
                    )
                    if prediction_json:
                        return prediction_json
                        
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error on attempt {attempt + 1}: {str(e)}")
                    if attempt == 2:  # Last attempt
                        return self._get_physics_based_fallback(chemicals, environment, context_data)
                except Exception as e:
                    print(f"DSPy prediction error on attempt {attempt + 1}: {str(e)}")
                    if attempt == 2:  # Last attempt
                        return self._get_physics_based_fallback(chemicals, environment, context_data)
        
        # Final fallback if DSPy is not configured
        return self._get_physics_based_fallback(chemicals, environment, context_data)
    
    async def _get_chemical_context_with_retries(self, chemicals: List[str]) -> Dict[str, Dict]:
        """Get chemical context with retry logic for PubChem failures."""
        for attempt in range(3):
            try:
                context_data = await self.pubchem_service.get_multiple_compounds_data(chemicals)
                if context_data:
                    return context_data
            except Exception as e:
                print(f"PubChem API error on attempt {attempt + 1}: {str(e)}")
                if attempt < 2:  # Not the last attempt
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # Return minimal context if all attempts fail
        return {
            chemical: {
                "formula": chemical,
                "molecular_weight": None,
                "h_bond_donors": 0,
                "h_bond_acceptors": 0,
                "source": "Fallback"
            }
            for chemical in chemicals
        }
    
    def _validate_and_parse_prediction(self, json_output: str, chemicals: List[str], environment: str) -> Optional[Dict]:
        """Validate and parse DSPy JSON output with error handling."""
        try:
            prediction = json.loads(json_output)
            
            # Validate required fields
            required_fields = ["products", "effects", "description"]
            if not all(field in prediction for field in required_fields):
                print(f"Missing required fields in prediction: {prediction}")
                return None
            
            # Validate products structure
            if not isinstance(prediction["products"], list) or not prediction["products"]:
                print("Invalid products structure")
                return None
                
            for product in prediction["products"]:
                if not all(key in product for key in ["formula", "name", "state"]):
                    print(f"Invalid product structure: {product}")
                    return None
            
            # Validate effects
            if not isinstance(prediction["effects"], list):
                print("Effects must be a list")
                return None
            
            # Ensure state_change is optional and properly typed
            if "state_change" not in prediction:
                prediction["state_change"] = None
            
            return prediction
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            return None
        except Exception as e:
            print(f"Validation error: {str(e)}")
            return None
    
    def _get_physics_based_fallback(self, chemicals: List[str], environment: str, context_data: Dict[str, Dict]) -> Dict:
        """Provide physics-based fallback prediction using chemical properties."""
        # Analyze chemical properties to make educated predictions
        products = []
        effects = []
        state_change = None
        
        # Basic chemical analysis
        has_water = any("H2O" in chemical or "water" in chemical.lower() for chemical in chemicals)
        has_salt = any("Cl" in chemical and ("Na" in chemical or "K" in chemical) for chemical in chemicals)
        has_acid = any("H" in chemical and any(acid_marker in chemical for acid_marker in ["SO4", "NO3", "Cl"]) for chemical in chemicals)
        has_base = any("OH" in chemical for chemical in chemicals)
        has_metal = any(metal in chemical for chemical in chemicals for metal in ["Na", "K", "Ca", "Mg", "Fe", "Al", "Zn"])
        
        # Generate realistic products based on chemical types
        if has_water and has_salt:
            products.extend([
                {"formula": chemicals[0], "name": self._get_compound_name(chemicals[0]), "state": "dissolved"},
                {"formula": "H2O", "name": "Water", "state": "liquid"}
            ])
            effects.extend(["dissolving", "ionic_dissociation"])
            
        elif has_acid and has_base:
            products.extend([
                {"formula": "H2O", "name": "Water", "state": "liquid"},
                {"formula": "Salt", "name": "Salt Product", "state": "solid"}
            ])
            effects.extend(["neutralization", "heat_release", "bubbling"])
            
        elif has_metal and has_water:
            products.extend([
                {"formula": "H2", "name": "Hydrogen Gas", "state": "gas"},
                {"formula": f"{chemicals[0]}OH", "name": "Metal Hydroxide", "state": "aqueous"}
            ])
            effects.extend(["gas_evolution", "vigorous_reaction", "heat_release"])
            
        else:
            # Default mixing behavior
            products = [
                {"formula": chemical, "name": self._get_compound_name(chemical), "state": "mixed"}
                for chemical in chemicals
            ]
            effects.extend(["physical_mixing"])
        
        # Environment-specific modifications
        if "vacuum" in environment.lower():
            effects.append("rapid_boiling")
            state_change = "gas"
        elif "high_temperature" in environment.lower():
            effects.extend(["thermal_decomposition", "phase_change"])
        elif "low_temperature" in environment.lower():
            effects.append("crystallization")
        
        # Ensure we have at least basic effects
        if not effects:
            effects = ["mixing", "temperature_change"]
        
        description = self._generate_physics_description(chemicals, environment, products, effects)
        
        return {
            "products": products,
            "effects": effects,
            "state_change": state_change,
            "description": description
        }
    
    def _get_compound_name(self, formula: str) -> str:
        """Get a reasonable compound name from formula."""
        common_names = {
            "H2O": "Water",
            "NaCl": "Sodium Chloride",
            "HCl": "Hydrochloric Acid",
            "NaOH": "Sodium Hydroxide",
            "H2SO4": "Sulfuric Acid",
            "CaCO3": "Calcium Carbonate",
            "O2": "Oxygen",
            "H2": "Hydrogen",
            "CO2": "Carbon Dioxide",
            "NH3": "Ammonia"
        }
        return common_names.get(formula, f"Compound {formula}")
    
    def _generate_physics_description(self, chemicals: List[str], environment: str, products: List[Dict], effects: List[str]) -> str:
        """Generate a physics-based description of the reaction."""
        chemical_names = [self._get_compound_name(chem) for chem in chemicals]
        
        if "dissolving" in effects:
            return f"{' and '.join(chemical_names)} undergo dissolution in {environment}, forming a homogeneous solution with ionic dissociation."
        elif "neutralization" in effects:
            return f"Acid-base neutralization occurs between {' and '.join(chemical_names)} in {environment}, producing water and salt."
        elif "gas_evolution" in effects:
            return f"Vigorous reaction between {' and '.join(chemical_names)} in {environment} produces gas evolution and heat release."
        else:
            return f"Physical mixing of {' and '.join(chemical_names)} occurs in {environment} environment with minimal chemical change."
    
    def _get_fallback_prediction(self, chemicals: List[str], environment: str) -> Dict:
        """Simple fallback when all other methods fail."""
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
            "description": f"Basic interaction between {', '.join(chemicals)} in {environment} environment. Enhanced prediction unavailable."
        }
    
    async def _check_world_first_effects(
        self, 
        effects: List[str], 
        user_id: int, 
        reaction_cache_id: int, 
        db: Session,
        commit: bool = True
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
        
        # Only commit if requested (for transaction control)
        if world_first and commit:
            db.commit()
        
        return world_first