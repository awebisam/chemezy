"""
Award Template Management Service

Provides CRUD operations and validation for award templates.
"""

from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from datetime import datetime

from app.models.award import AwardTemplate, AwardCategory
from app.core.config import settings


class AwardTemplateValidationError(Exception):
    """Raised when award template validation fails."""
    pass


class AwardTemplateService:
    """Service for managing award templates with CRUD operations and validation."""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = settings
    
    async def create_template(
        self, 
        name: str,
        description: str,
        category: AwardCategory,
        criteria: Dict[str, Any],
        metadata: Dict[str, Any],
        created_by: int
    ) -> AwardTemplate:
        """Create a new award template with validation."""
        # Validate template data
        self._validate_template_data(name, description, criteria, metadata)
        
        # Check for duplicate names
        existing = self.db.exec(
            select(AwardTemplate).where(AwardTemplate.name == name)
        ).first()
        
        if existing:
            raise AwardTemplateValidationError(f"Award template with name '{name}' already exists")
        
        # Create new template
        template = AwardTemplate(
            name=name,
            description=description,
            category=category,
            criteria=criteria,
            award_metadata=metadata,
            created_by=created_by,
            is_active=True
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    async def get_template(self, template_id: int) -> Optional[AwardTemplate]:
        """Get a specific award template by ID."""
        return self.db.exec(
            select(AwardTemplate).where(AwardTemplate.id == template_id)
        ).first()
    
    async def get_templates(
        self, 
        category: Optional[AwardCategory] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[AwardTemplate]:
        """Get award templates with optional filtering."""
        query = select(AwardTemplate)
        
        if category:
            query = query.where(AwardTemplate.category == category)
        
        if active_only:
            query = query.where(AwardTemplate.is_active == True)
        
        query = query.offset(skip).limit(limit)
        
        return list(self.db.exec(query).all())
    
    async def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[AwardTemplate]:
        """Update an existing award template."""
        template = await self.get_template(template_id)
        if not template:
            return None
        
        # Validate updated data
        update_name = name if name is not None else template.name
        update_description = description if description is not None else template.description
        update_criteria = criteria if criteria is not None else template.criteria
        update_metadata = metadata if metadata is not None else template.award_metadata
        
        self._validate_template_data(update_name, update_description, update_criteria, update_metadata)
        
        # Check for duplicate names (excluding current template)
        if name and name != template.name:
            existing = self.db.exec(
                select(AwardTemplate).where(
                    AwardTemplate.name == name,
                    AwardTemplate.id != template_id
                )
            ).first()
            
            if existing:
                raise AwardTemplateValidationError(f"Award template with name '{name}' already exists")
        
        # Update fields
        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if criteria is not None:
            template.criteria = criteria
        if metadata is not None:
            template.award_metadata = metadata
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    async def activate_template(self, template_id: int) -> Optional[AwardTemplate]:
        """Activate an award template."""
        template = await self.get_template(template_id)
        if not template:
            return None
        
        template.is_active = True
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    async def deactivate_template(self, template_id: int) -> Optional[AwardTemplate]:
        """Deactivate an award template."""
        template = await self.get_template(template_id)
        if not template:
            return None
        
        template.is_active = False
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    async def delete_template(self, template_id: int) -> bool:
        """Soft delete an award template by deactivating it."""
        template = await self.deactivate_template(template_id)
        return template is not None
    
    def _validate_template_data(
        self, 
        name: str, 
        description: str, 
        criteria: Dict[str, Any], 
        metadata: Dict[str, Any]
    ) -> None:
        """Validate award template data structure and content."""
        # Validate basic fields
        if not name or not name.strip():
            raise AwardTemplateValidationError("Award template name cannot be empty")
        
        if len(name) > 100:
            raise AwardTemplateValidationError("Award template name cannot exceed 100 characters")
        
        if not description or not description.strip():
            raise AwardTemplateValidationError("Award template description cannot be empty")
        
        if len(description) > 500:
            raise AwardTemplateValidationError("Award template description cannot exceed 500 characters")
        
        # Validate criteria structure
        self._validate_criteria(criteria)
        
        # Validate metadata structure
        self._validate_metadata(metadata)
    
    def _validate_criteria(self, criteria: Dict[str, Any]) -> None:
        """Validate award criteria structure."""
        if not isinstance(criteria, dict):
            raise AwardTemplateValidationError("Criteria must be a dictionary")
        
        # Required fields
        if "type" not in criteria:
            raise AwardTemplateValidationError("Criteria must include a 'type' field")
        
        criteria_type = criteria["type"]
        valid_types = [
            "discovery_count", "unique_effects", "reaction_complexity",
            "debug_submissions", "correction_accuracy", "data_quality_impact",
            "profile_completeness", "consecutive_days", "help_others"
        ]
        
        if criteria_type not in valid_types:
            raise AwardTemplateValidationError(f"Invalid criteria type: {criteria_type}")
        
        # Validate threshold for count-based criteria
        if criteria_type in ["discovery_count", "debug_submissions", "consecutive_days"]:
            if "threshold" not in criteria:
                raise AwardTemplateValidationError(f"Criteria type '{criteria_type}' requires a 'threshold' field")
            
            threshold = criteria["threshold"]
            if not isinstance(threshold, (int, float)) or threshold <= 0:
                raise AwardTemplateValidationError("Threshold must be a positive number")
        
        # Validate conditions if present
        if "conditions" in criteria:
            conditions = criteria["conditions"]
            if not isinstance(conditions, list):
                raise AwardTemplateValidationError("Conditions must be a list")
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate award metadata structure."""
        if not isinstance(metadata, dict):
            raise AwardTemplateValidationError("Metadata must be a dictionary")
        
        # Validate icon if present
        if "icon" in metadata:
            icon = metadata["icon"]
            if not isinstance(icon, str) or len(icon) > 10:
                raise AwardTemplateValidationError("Icon must be a string with max 10 characters")
        
        # Validate rarity if present
        if "rarity" in metadata:
            rarity = metadata["rarity"]
            valid_rarities = ["common", "uncommon", "rare", "epic", "legendary"]
            if rarity not in valid_rarities:
                raise AwardTemplateValidationError(f"Invalid rarity: {rarity}")
        
        # Validate points if present
        if "points" in metadata:
            points = metadata["points"]
            if not isinstance(points, (int, float)) or points < 0:
                raise AwardTemplateValidationError("Points must be a non-negative number")
        
        # Validate tiers if present
        if "tiers" in metadata:
            tiers = metadata["tiers"]
            if not isinstance(tiers, list):
                raise AwardTemplateValidationError("Tiers must be a list")
            
            for i, tier in enumerate(tiers):
                if not isinstance(tier, dict):
                    raise AwardTemplateValidationError(f"Tier {i} must be a dictionary")
                
                required_tier_fields = ["name", "threshold", "points"]
                for field in required_tier_fields:
                    if field not in tier:
                        raise AwardTemplateValidationError(f"Tier {i} missing required field: {field}")
                
                if not isinstance(tier["threshold"], (int, float)) or tier["threshold"] <= 0:
                    raise AwardTemplateValidationError(f"Tier {i} threshold must be a positive number")
                
                if not isinstance(tier["points"], (int, float)) or tier["points"] < 0:
                    raise AwardTemplateValidationError(f"Tier {i} points must be a non-negative number")