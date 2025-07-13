"""
Admin configuration and feature flag management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any, List, Optional

from app.api.v1.endpoints.users import get_current_admin_user
from app.db.session import get_session
from app.models.user import User
from app.services.config_service import config_service, FeatureFlagStatus
from app.services.audit_service import AuditService, AuditAction
from app.schemas.admin_config import (
    ConfigurationInfoSchema,
    FeatureFlagsResponseSchema,
    FeatureFlagDetailSchema,
    FeatureFlagToggleResponseSchema,
    ConfigurationReloadResponseSchema,
    UserFeaturesResponseSchema,
    SystemStatusResponseSchema,
    FeatureFlagSchema
)

router = APIRouter()


@router.get("/info", response_model=ConfigurationInfoSchema)
async def get_configuration_info(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get configuration information and system status.
    
    Only admin users can access configuration information.
    """
    try:
        config_info = config_service.get_configuration_info()
        config_data = config_service.get_config()
        
        return ConfigurationInfoSchema(
            configuration_info=config_info,
            current_config={
                "evaluation_enabled": config_data.evaluation_enabled,
                "cache_enabled": config_data.cache_enabled,
                "notifications_enabled": config_data.notifications_enabled,
                "rate_limiting_enabled": config_data.rate_limiting_enabled,
                "batch_size": config_data.batch_size,
                "cache_ttl_seconds": config_data.cache_ttl_seconds,
                "requests_per_minute": config_data.requests_per_minute,
                "admin_requests_per_minute": config_data.admin_requests_per_minute
            },
            retrieved_at="2025-01-15T00:00:00Z",
            retrieved_by=admin_user.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration info: {str(e)}"
        )


@router.get("/feature-flags", response_model=FeatureFlagsResponseSchema)
async def get_feature_flags(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get all feature flags and their current status.
    
    Only admin users can access feature flag information.
    """
    try:
        feature_flags = config_service.get_all_feature_flags()
        
        flags_data = []
        for name, flag in feature_flags.items():
            flags_data.append(FeatureFlagSchema(
                name=name,
                status=flag.status.value,
                description=flag.description,
                rollout_percentage=flag.rollout_percentage,
                target_users=flag.target_users,
                target_groups=flag.target_groups,
                environments=flag.environments,
                metadata=flag.metadata
            ))
        
        return FeatureFlagsResponseSchema(
            feature_flags=flags_data,
            total_count=len(flags_data),
            retrieved_at="2025-01-15T00:00:00Z",
            retrieved_by=admin_user.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feature flags: {str(e)}"
        )


@router.get("/feature-flags/{feature_name}", response_model=FeatureFlagDetailSchema)
async def get_feature_flag(
    feature_name: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get a specific feature flag configuration.
    
    Only admin users can access feature flag details.
    """
    try:
        flag = config_service.get_feature_flag(feature_name)
        
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{feature_name}' not found"
            )
        
        return FeatureFlagDetailSchema(
            feature_flag=FeatureFlagSchema(
                name=flag.name,
                status=flag.status.value,
                description=flag.description,
                rollout_percentage=flag.rollout_percentage,
                target_users=flag.target_users,
                target_groups=flag.target_groups,
                environments=flag.environments,
                metadata=flag.metadata
            ),
            retrieved_at="2025-01-15T00:00:00Z",
            retrieved_by=admin_user.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve feature flag: {str(e)}"
        )


@router.post("/feature-flags/{feature_name}/toggle", response_model=FeatureFlagToggleResponseSchema)
async def toggle_feature_flag(
    feature_name: str,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Toggle a feature flag between enabled and disabled.
    
    Only admin users can toggle feature flags.
    """
    try:
        flag = config_service.get_feature_flag(feature_name)
        
        if not flag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature flag '{feature_name}' not found"
            )
        
        # Toggle logic
        if flag.status == FeatureFlagStatus.ENABLED:
            new_status = FeatureFlagStatus.DISABLED
        elif flag.status == FeatureFlagStatus.DISABLED:
            new_status = FeatureFlagStatus.ENABLED
        else:
            # For rollout/testing flags, default to enabled
            new_status = FeatureFlagStatus.ENABLED
        
        # Update the flag
        flag.status = new_status
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log_action(
            action=AuditAction.SYSTEM_ERROR,  # Using as generic system action
            user_id=admin_user.id,
            details={
                "action": "feature_flag_toggle",
                "feature_name": feature_name,
                "old_status": flag.status.value,
                "new_status": new_status.value
            }
        )
        
        return FeatureFlagToggleResponseSchema(
            success=True,
            feature_name=feature_name,
            old_status=flag.status.value,
            new_status=new_status.value,
            message=f"Feature flag '{feature_name}' toggled to {new_status.value}",
            toggled_at="2025-01-15T00:00:00Z",
            toggled_by=admin_user.username
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle feature flag: {str(e)}"
        )


@router.post("/reload", response_model=ConfigurationReloadResponseSchema)
async def reload_configuration(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Reload configuration from file.
    
    Only admin users can reload configuration.
    """
    try:
        config_service.reload_configuration()
        
        # Log the action
        audit_service = AuditService(db)
        await audit_service.log_action(
            action=AuditAction.SYSTEM_ERROR,  # Using as generic system action
            user_id=admin_user.id,
            details={
                "action": "configuration_reload",
                "config_file": config_service.config_file
            }
        )
        
        return ConfigurationReloadResponseSchema(
            success=True,
            message="Configuration reloaded successfully",
            reloaded_at="2025-01-15T00:00:00Z",
            reloaded_by=admin_user.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload configuration: {str(e)}"
        )


@router.get("/user-features", response_model=UserFeaturesResponseSchema)
async def get_user_features(
    user_id: Optional[int] = None,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get enabled features for a specific user or the current admin user.
    
    Only admin users can check user features.
    """
    try:
        target_user_id = user_id or admin_user.id
        
        # Get user groups (simplified - in real implementation, you'd query the database)
        user_groups = ["admin"] if admin_user.is_admin else []
        
        enabled_features = config_service.get_enabled_features(
            user_id=target_user_id,
            user_groups=user_groups
        )
        
        return UserFeaturesResponseSchema(
            user_id=target_user_id,
            user_groups=user_groups,
            enabled_features=enabled_features,
            total_enabled=len(enabled_features),
            checked_at="2025-01-15T00:00:00Z",
            checked_by=admin_user.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user features: {str(e)}"
        )


@router.get("/system-status", response_model=SystemStatusResponseSchema)
async def get_system_status(
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get overall system status based on configuration.
    
    Only admin users can access system status.
    """
    try:
        config_data = config_service.get_config()
        config_info = config_service.get_configuration_info()
        
        # Calculate system health score
        health_factors = {
            "evaluation_enabled": config_data.evaluation_enabled,
            "cache_enabled": config_data.cache_enabled,
            "notifications_enabled": config_data.notifications_enabled,
            "audit_logging_enabled": config_data.audit_all_actions,
            "rate_limiting_enabled": config_data.rate_limiting_enabled
        }
        
        health_score = sum(health_factors.values()) / len(health_factors) * 100
        
        status = "healthy" if health_score >= 80 else "warning" if health_score >= 60 else "critical"
        
        return SystemStatusResponseSchema(
            system_status=status,
            health_score=round(health_score, 2),
            health_factors=health_factors,
            configuration_info=config_info,
            recommendations=_get_system_recommendations(config_data),
            checked_at="2025-01-15T00:00:00Z",
            checked_by=admin_user.username
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system status: {str(e)}"
        )


def _get_system_recommendations(config_data) -> List[str]:
    """Generate system recommendations based on configuration."""
    recommendations = []
    
    if not config_data.cache_enabled:
        recommendations.append("Enable caching for better performance")
    
    if not config_data.rate_limiting_enabled:
        recommendations.append("Enable rate limiting for better security")
    
    if not config_data.audit_all_actions:
        recommendations.append("Enable audit logging for better monitoring")
    
    if config_data.batch_size > 200:
        recommendations.append("Consider reducing batch size for better memory usage")
    
    if config_data.cache_ttl_seconds < 60:
        recommendations.append("Consider increasing cache TTL for better performance")
    
    return recommendations