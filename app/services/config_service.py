"""
Configuration and Feature Flag Service

Manages application configuration and feature flags for the award system.
"""

import os
import json
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FeatureFlagStatus(str, Enum):
    """Feature flag status values."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ROLLOUT = "rollout"  # Gradual rollout
    TESTING = "testing"  # Only for testing environments


@dataclass
class FeatureFlag:
    """Represents a feature flag with its configuration."""
    name: str
    status: FeatureFlagStatus
    description: str
    rollout_percentage: int = 0  # 0-100, used when status is ROLLOUT
    target_users: List[int] = field(default_factory=list)  # Specific users for testing
    target_groups: List[str] = field(default_factory=list)  # User groups (admin, beta, etc.)
    environments: List[str] = field(default_factory=list)  # Target environments
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional configuration


@dataclass
class AwardSystemConfig:
    """Configuration for the award system."""
    
    # Award evaluation settings
    evaluation_enabled: bool = True
    evaluation_frequency_minutes: int = 60
    batch_size: int = 100
    
    # Caching settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    leaderboard_cache_ttl: int = 300
    user_cache_ttl: int = 180
    
    # Database settings
    enable_database_optimization: bool = True
    max_query_time_seconds: int = 30
    connection_pool_size: int = 10
    
    # Notification settings
    notifications_enabled: bool = True
    notification_batch_size: int = 50
    email_notifications: bool = False
    push_notifications: bool = False
    
    # Rate limiting
    rate_limiting_enabled: bool = True
    requests_per_minute: int = 60
    admin_requests_per_minute: int = 300
    
    # Feature flags
    enable_manual_awards: bool = True
    enable_award_revocation: bool = True
    enable_leaderboards: bool = True
    enable_community_features: bool = True
    enable_audit_logging: bool = True
    enable_performance_monitoring: bool = True
    
    # Award template settings
    max_templates_per_category: int = 50
    allow_custom_templates: bool = False
    template_validation_strict: bool = True
    
    # Security settings
    admin_actions_require_confirmation: bool = True
    audit_all_actions: bool = True
    sensitive_data_logging: bool = False
    
    # Performance settings
    enable_background_jobs: bool = True
    max_concurrent_evaluations: int = 10
    enable_query_optimization: bool = True


class ConfigurationService:
    """Service for managing application configuration and feature flags."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "award_system_config.json"
        self.config = AwardSystemConfig()
        self.feature_flags: Dict[str, FeatureFlag] = {}
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # Load configuration and feature flags
        self._load_configuration()
        self._load_feature_flags()
    
    def _load_configuration(self) -> None:
        """Load configuration from file and environment variables."""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    
                # Update configuration with loaded data
                for key, value in config_data.get('award_system', {}).items():
                    if hasattr(self.config, key):
                        setattr(self.config, key, value)
                
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.info(f"Configuration file {self.config_file} not found, using defaults")
        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
        
        # Override with environment variables
        self._apply_environment_overrides()
    
    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        env_mappings = {
            "AWARD_EVALUATION_ENABLED": ("evaluation_enabled", bool),
            "AWARD_CACHE_ENABLED": ("cache_enabled", bool),
            "AWARD_NOTIFICATIONS_ENABLED": ("notifications_enabled", bool),
            "AWARD_RATE_LIMITING_ENABLED": ("rate_limiting_enabled", bool),
            "AWARD_AUDIT_LOGGING_ENABLED": ("audit_all_actions", bool),
            "AWARD_BATCH_SIZE": ("batch_size", int),
            "AWARD_CACHE_TTL": ("cache_ttl_seconds", int),
            "AWARD_REQUESTS_PER_MINUTE": ("requests_per_minute", int),
        }
        
        for env_var, (config_attr, value_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    if value_type == bool:
                        parsed_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        parsed_value = value_type(env_value)
                    
                    setattr(self.config, config_attr, parsed_value)
                    logger.info(f"Configuration override: {config_attr} = {parsed_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid environment variable {env_var}: {e}")
    
    def _load_feature_flags(self) -> None:
        """Load feature flags from configuration."""
        feature_flags_data = self._get_feature_flags_data()
        
        for flag_name, flag_config in feature_flags_data.items():
            try:
                feature_flag = FeatureFlag(
                    name=flag_name,
                    status=FeatureFlagStatus(flag_config.get("status", "disabled")),
                    description=flag_config.get("description", ""),
                    rollout_percentage=flag_config.get("rollout_percentage", 0),
                    target_users=flag_config.get("target_users", []),
                    target_groups=flag_config.get("target_groups", []),
                    environments=flag_config.get("environments", []),
                    metadata=flag_config.get("metadata", {})
                )
                
                self.feature_flags[flag_name] = feature_flag
                logger.debug(f"Loaded feature flag: {flag_name}")
                
            except Exception as e:
                logger.error(f"Error loading feature flag {flag_name}: {e}")
    
    def _get_feature_flags_data(self) -> Dict[str, Any]:
        """Get feature flags data from configuration file or defaults."""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('feature_flags', {})
        except Exception as e:
            logger.error(f"Error reading feature flags: {e}")
        
        # Default feature flags
        return {
            "award_system_v2": {
                "status": "disabled",
                "description": "Enhanced award system with new features",
                "rollout_percentage": 0,
                "environments": ["development", "staging"]
            },
            "advanced_analytics": {
                "status": "testing",
                "description": "Advanced analytics and reporting features",
                "target_groups": ["admin", "beta"]
            },
            "real_time_notifications": {
                "status": "rollout",
                "description": "Real-time notification system",
                "rollout_percentage": 25
            },
            "enhanced_leaderboards": {
                "status": "enabled",
                "description": "Enhanced leaderboard features",
                "environments": ["development", "staging", "production"]
            },
            "ai_powered_recommendations": {
                "status": "disabled",
                "description": "AI-powered award recommendations",
                "metadata": {"model_version": "v1.0", "confidence_threshold": 0.8}
            },
            "social_features": {
                "status": "testing",
                "description": "Social features for community engagement",
                "target_groups": ["beta"]
            },
            "gamification_v2": {
                "status": "rollout",
                "description": "Enhanced gamification features",
                "rollout_percentage": 50
            },
            "performance_optimizations": {
                "status": "enabled",
                "description": "Performance optimization features",
                "environments": ["development", "staging", "production"]
            }
        }
    
    def is_feature_enabled(
        self,
        feature_name: str,
        user_id: Optional[int] = None,
        user_groups: Optional[List[str]] = None
    ) -> bool:
        """
        Check if a feature is enabled for the current context.
        
        Args:
            feature_name: Name of the feature flag
            user_id: Optional user ID for targeted features
            user_groups: Optional user groups for group-based features
            
        Returns:
            True if feature is enabled, False otherwise
        """
        if feature_name not in self.feature_flags:
            logger.warning(f"Feature flag {feature_name} not found, defaulting to disabled")
            return False
        
        flag = self.feature_flags[feature_name]
        
        # Check environment
        if flag.environments and self.environment not in flag.environments:
            return False
        
        # Check status
        if flag.status == FeatureFlagStatus.DISABLED:
            return False
        
        if flag.status == FeatureFlagStatus.ENABLED:
            return True
        
        if flag.status == FeatureFlagStatus.TESTING:
            # Check if user is in target users or groups
            if user_id and user_id in flag.target_users:
                return True
            
            if user_groups and any(group in flag.target_groups for group in user_groups):
                return True
            
            return False
        
        if flag.status == FeatureFlagStatus.ROLLOUT:
            # Check target users first
            if user_id and user_id in flag.target_users:
                return True
            
            # Check target groups
            if user_groups and any(group in flag.target_groups for group in user_groups):
                return True
            
            # Check rollout percentage
            if user_id and flag.rollout_percentage > 0:
                # Simple hash-based rollout
                user_hash = hash(str(user_id)) % 100
                return user_hash < flag.rollout_percentage
            
            return False
        
        return False
    
    def get_feature_flag(self, feature_name: str) -> Optional[FeatureFlag]:
        """Get a specific feature flag configuration."""
        return self.feature_flags.get(feature_name)
    
    def get_all_feature_flags(self) -> Dict[str, FeatureFlag]:
        """Get all feature flags."""
        return self.feature_flags.copy()
    
    def get_enabled_features(
        self,
        user_id: Optional[int] = None,
        user_groups: Optional[List[str]] = None
    ) -> List[str]:
        """Get list of enabled features for the current context."""
        enabled_features = []
        
        for feature_name in self.feature_flags:
            if self.is_feature_enabled(feature_name, user_id, user_groups):
                enabled_features.append(feature_name)
        
        return enabled_features
    
    def get_config(self) -> AwardSystemConfig:
        """Get current configuration."""
        return self.config
    
    def update_config(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Configuration updated: {key} = {value}")
            else:
                logger.warning(f"Unknown configuration key: {key}")
    
    def save_configuration(self) -> None:
        """Save current configuration to file."""
        try:
            config_data = {
                "award_system": {
                    key: getattr(self.config, key)
                    for key in dir(self.config)
                    if not key.startswith('_')
                },
                "feature_flags": {
                    name: {
                        "status": flag.status.value,
                        "description": flag.description,
                        "rollout_percentage": flag.rollout_percentage,
                        "target_users": flag.target_users,
                        "target_groups": flag.target_groups,
                        "environments": flag.environments,
                        "metadata": flag.metadata
                    }
                    for name, flag in self.feature_flags.items()
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def reload_configuration(self) -> None:
        """Reload configuration from file."""
        logger.info("Reloading configuration...")
        self._load_configuration()
        self._load_feature_flags()
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """Get configuration information for monitoring."""
        return {
            "environment": self.environment,
            "config_file": self.config_file,
            "feature_flags_count": len(self.feature_flags),
            "enabled_flags": len([
                f for f in self.feature_flags.values()
                if f.status == FeatureFlagStatus.ENABLED
            ]),
            "testing_flags": len([
                f for f in self.feature_flags.values()
                if f.status == FeatureFlagStatus.TESTING
            ]),
            "rollout_flags": len([
                f for f in self.feature_flags.values()
                if f.status == FeatureFlagStatus.ROLLOUT
            ]),
            "config_summary": {
                "evaluation_enabled": self.config.evaluation_enabled,
                "cache_enabled": self.config.cache_enabled,
                "notifications_enabled": self.config.notifications_enabled,
                "rate_limiting_enabled": self.config.rate_limiting_enabled,
                "audit_logging_enabled": self.config.audit_all_actions
            }
        }


# Global configuration service instance
config_service = ConfigurationService()