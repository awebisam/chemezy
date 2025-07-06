from pydantic import BaseModel, Field
from typing import Union, Literal

class GasProductionEffect(BaseModel):
    effect_type: Literal["gas_production"] = "gas_production"
    gas_type: str = Field(..., description="Type of gas produced, e.g., 'bubbles', 'smoke', 'vapor'.")
    color: str = Field(..., description="Color of the gas.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Intensity of the gas production (0.0 to 1.0).")
    duration: float = Field(..., gt=0, description="Duration of the effect in seconds.")

class LightEmissionEffect(BaseModel):
    effect_type: Literal["light_emission"] = "light_emission"
    color: str = Field(..., description="Color of the light.")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Intensity of the light (0.0 to 1.0).")
    radius: float = Field(..., gt=0, description="Radius of the light emission in meters.")
    duration: float = Field(..., gt=0, description="Duration of the effect in seconds.")

class VolumeChangeEffect(BaseModel):
    effect_type: Literal["volume_change"] = "volume_change"
    factor: float = Field(..., gt=0, description="Factor of volume change (e.g., 1.5 for 50% expansion).")

class SpillEffect(BaseModel):
    effect_type: Literal["spill"] = "spill"
    amount_percentage: float = Field(..., ge=0.0, le=1.0, description="Percentage of the volume that spills.")
    spread_radius: float = Field(..., gt=0, description="Radius the spill spreads to in meters.")

class StateChangeEffect(BaseModel):
    effect_type: Literal["state_change"] = "state_change"
    product_chemical_id: int = Field(..., description="ID of the product chemical undergoing a state change.")
    final_state: str = Field(..., description="The final state of matter for the product.")

class TemperatureChangeEffect(BaseModel):
    effect_type: Literal["temperature_change"] = "temperature_change"
    delta_celsius: float = Field(..., description="Change in temperature in degrees Celsius.")

class TextureChangeEffect(BaseModel):
    effect_type: Literal["texture_change"] = "texture_change"
    product_chemical_id: int = Field(..., description="ID of the product chemical undergoing a texture change.")
    texture_type: str = Field(..., description="Description of the new texture (e.g., 'gooey', 'slimy', 'viscous').")
    color: str = Field(..., description="Resulting color of the textured product.")
    viscosity: float = Field(..., ge=0.0, le=1.0, description="Viscosity of the new texture (0.0 to 1.0).")

class FoamProductionEffect(BaseModel):
    effect_type: Literal["foam_production"] = "foam_production"
    color: str = Field(..., description="Color of the foam.")
    density: float = Field(..., gt=0, description="Density of the foam.")
    bubble_size: Literal["small", "medium", "large"] = Field(..., description="Size of the bubbles in the foam.")
    stability: float = Field(..., gt=0, description="How long the foam lasts in seconds.")

Effect = Union[
    GasProductionEffect,
    LightEmissionEffect,
    VolumeChangeEffect,
    SpillEffect,
    StateChangeEffect,
    TemperatureChangeEffect,
    TextureChangeEffect,
    FoamProductionEffect,
]
