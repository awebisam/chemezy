from enum import Enum

class Environment(str, Enum):
    """Defines the valid environments for a chemical reaction."""
    NORMAL = "Earth (Normal)"
    VACUUM = "Vacuum"
    PURE_OXYGEN = "Pure Oxygen"
    INERT_GAS = "Inert Gas"
    ACIDIC = "Acidic Environment"
    BASIC = "Basic Environment"
