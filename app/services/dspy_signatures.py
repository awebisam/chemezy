import dspy
from typing import Dict, Any
from app.models.chemical import StateOfMatter
from app.schemas.reaction import ReactionPredictionOutput


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
        desc="The molecular formula of the chemical (e.g., 'H2O')."
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
    Keep your response concise to avoid truncation.
    The JSON must have these exact fields:
    - "products": array of objects with "formula", "name", "state" fields
    - "effects": array of strings describing observable phenomena (keep descriptions short)
    - "state_change": string or null for overall state change
    - "description": string explaining the reaction mechanism and outcome (be concise)
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
    reaction_prediction: ReactionPredictionOutput = dspy.OutputField(
        desc="A structured prediction of the reaction outcome, conforming to the Pydantic schema."
    )
