import dspy
from typing import Dict, Any, List
from app.models.chemical import StateOfMatter
from app.schemas.reaction import ReactionPrediction, ReactionPredictionDSPyOutput

class GenerateChemicalProperties(dspy.Signature):
    """
    You are a chemical data formatting assistant for a chemistry education platform targeting kids and high school students. Your job is to create a structured JSON response using the provided PubChem data as your primary source.

    **INSTRUCTIONS:**
    1. Use the `pubchem_data` as your main source of factual information.
    2. Use the `context` field to disambiguate between isomers with the same molecular formula.
    3. For the `properties` dictionary, include all key-value pairs from the pubchem_data.
    4. When PubChem data is missing specific values, use reasonable chemical knowledge to fill gaps.
    5. Keep explanations simple and educational - this is for students learning chemistry.
    6. Return a valid JSON object matching the required schema.

    **CONTEXT USAGE:**
    - If `context` contains hints like "THC", "cannabis", or "marijuana", identify tetrahydrocannabinol
    - If `context` contains hints like "CBD", "cannabidiol", identify cannabidiol
    - If `context` contains hints like "vitamin C", "ascorbic", identify ascorbic acid
    - If `context` contains hints like "salt", "table salt", identify sodium chloride
    - Use context to select the most educationally relevant isomer for students

    **FIELD GUIDELINES:**
    - `normalized_formula`: Use the formula from pubchem_data, or clean up the input molecular_formula
    - `common_name`: Use context hints to identify the right compound, prefer simple educational names
    - `state_of_matter`: Must be one of: "solid", "liquid", "gas", "plasma", "aqueous"
    - `color`: Provide typical color if known, otherwise "Colorless"
    - `density`: Use reasonable density value based on compound type
    - `properties`: Include all pubchem_data fields plus any additional relevant properties
    """
    __doc__ = __doc__.strip()

    molecular_formula: str = dspy.InputField(
        desc="The molecular formula being processed."
    )
    
    context: str = dspy.InputField(
        desc="Optional context or hint about the specific compound (e.g., 'THC cannabis', 'vitamin C', 'table salt'). Use this to disambiguate between isomers with the same molecular formula."
    )
    
    pubchem_data: str = dspy.InputField(
        desc="A JSON string of factual data retrieved from PubChem. This is your ONLY source of information."
    )

    normalized_formula: str = dspy.OutputField(
        desc="The normalized molecular formula, e.g., 'NaHSO4' for sodium bisulfate."
    )
    common_name: str = dspy.OutputField(
        desc="The common name of the chemical, e.g., 'Water'."
    )
    state_of_matter: StateOfMatter = dspy.OutputField(
        desc="The state of matter at room temperature. Must be one of: 'solid', 'liquid', 'gas', 'plasma', 'aqueous'."
    )
    color: str = dspy.OutputField(
        desc="The color of the chemical."
    )
    density: float = dspy.OutputField(
        desc="The density of the chemical in g/cm³."
    )
    properties: Dict[str, Any] = dspy.OutputField(
        desc="A dictionary of additional scientific properties, e.g., {{'melting_point': 0.0, 'boiling_point': 100.0}}."
    )

class PredictReactionProductsAndEffects(dspy.Signature):
    """
    Predicts the products and observable effects of a chemical reaction.

    You are a computational chemist AI. Your task is to predict the outcome of a chemical reaction with scientific rigor, acting as the core intelligence for a chemistry simulation engine.

    Given a set of reactants, an environment, and an optional catalyst, you must perform a step-by-step analysis to generate a plausible and scientifically-grounded prediction.

    Your reasoning process MUST follow these steps:
    1.  Analyze Reactants and Catalyst: Examine the properties of each reactant from `reactants_data` and the catalyst from `catalyst_data`.
    2.  Consider Environment: Factor in the `environment` conditions.
    3.  Identify Potential Pathways: Consider how the catalyst might influence reaction types (e.g., by lowering activation energy).
    4.  Determine Products: Predict the most likely chemical products. The catalyst itself should not be consumed or appear as a product.
    5.  Describe Phenomena: Detail the observable `effects`, noting any changes due to the catalyst (e.g., increased reaction rate leading to more intense effects).

    CRITICAL: You must return ONLY a valid JSON object that matches the ReactionPrediction schema.
    Do NOT include markdown formatting, code blocks, or any explanatory text.
    The JSON must have these exact fields:
    - "products": array of objects with "molecular_formula", "common_name", "quantity", and "is_soluble" fields.
    - "effects": array of structured `Effect` objects.
    - "explanation": string providing a concise, scientifically accurate explanation of the reaction, suitable for a "tips" section.
    """

    reactants_data: str = dspy.InputField(
        desc="A JSON string representing a list of reactant chemicals, including their properties."
    )
    environment: str = dspy.InputField(
        desc="A string describing the physical conditions of the reaction. Must be one of: 'Earth (Normal)', 'Vacuum', 'Pure Oxygen', 'Inert Gas', 'Acidic Environment', 'Basic Environment'."
    )
    catalyst_data: str = dspy.InputField(
        desc="An optional JSON string representing the catalyst chemical, including its properties."
    )

    prediction: ReactionPredictionDSPyOutput = dspy.OutputField(
        desc="A structured prediction of the reaction outcome, conforming to the Pydantic schema.",
    )