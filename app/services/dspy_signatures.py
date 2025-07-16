import dspy
from typing import Dict, Any, List
from app.models.chemical import StateOfMatter
from app.schemas.reaction import ReactionPrediction, ReactionPredictionDSPyOutput

class GenerateChemicalProperties(dspy.Signature):
    """
    You are a computational chemist AI. Your task is to generate the properties of a chemical based on its molecular formula.
    You must return ONLY a valid JSON object that matches the GenerateChemicalPropertiesOutput schema.
    Do NOT include markdown formatting, code blocks, or any explanatory text.
    Keep your response concise to avoid truncation. The JSON must have these exact fields:
    - "common_name": string
    - "state_of_matter": string
    - "color": string
    - "density": float
    - "properties": dictionary of additional scientific properties
    """
    __doc__ = __doc__.strip()

    molecular_formula: str = dspy.InputField(
        desc="The molecular formula of the chemical (e.g., 'NAHSO4' for sodium bisulfate)."
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
    - "products": array of objects with "molecular_formula", "quantity", and "is_soluble" fields.
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