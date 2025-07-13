"""
Admin configuration and feature flag related Pydantic schemas.
"""

from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class ConfigurationInfoSchema(BaseModel):
    """Schema for configuration information response."""
    configuration_info: Dict[str, Any]
    current_config: Dict[str, Any]
    retrieved_at: str
    retrieved_by: str

    class Config:
        from_attributes = True


class FeatureFlagSchema(BaseModel):
    """Schema for individual feature flag."""
    name: str
    status: str
    description: str
    rollout_percentage: Optional[int] = None
    target_users: Optional[List[int]] = None
    target_groups: Optional[List[str]] = None
    environments: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class FeatureFlagsResponseSchema(BaseModel):
    """Schema for feature flags list response."""
    feature_flags: List[FeatureFlagSchema]
    total_count: int
    retrieved_at: str
    retrieved_by: str

    class Config:
        from_attributes = True


class FeatureFlagDetailSchema(BaseModel):
    """Schema for single feature flag detail response."""
    feature_flag: FeatureFlagSchema
    retrieved_at: str
    retrieved_by: str

    class Config:
        from_attributes = True


class FeatureFlagToggleResponseSchema(BaseModel):
    """Schema for feature flag toggle response."""
    success: bool
    feature_name: str
    old_status: str
    new_status: str
    message: str
    toggled_at: str
    toggled_by: str

    class Config:
        from_attributes = True


class ConfigurationReloadResponseSchema(BaseModel):
    """Schema for configuration reload response."""
    success: bool
    message: str
    reloaded_at: str
    reloaded_by: str

    class Config:
        from_attributes = True


class UserFeaturesResponseSchema(BaseModel):
    """Schema for user features response."""
    user_id: int
    user_groups: List[str]
    enabled_features: List[str]
    total_enabled: int
    checked_at: str
    checked_by: str

    class Config:
        from_attributes = True


class SystemStatusResponseSchema(BaseModel):
    """Schema for system status response."""
    system_status: str
    health_score: float
    health_factors: Dict[str, bool]
    configuration_info: Dict[str, Any]
    recommendations: List[str]
    checked_at: str
    checked_by: str

    class Config:
        from_attributes = True