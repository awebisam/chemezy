"""
Core Award Service

Main orchestrator for award operations including evaluation, granting, retrieval, and revocation.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, and_, or_, desc, asc, func
from datetime import datetime
import logging

from app.models.award import AwardTemplate, UserAward, AwardCategory
from app.models.user import User
from app.services.award_evaluator import AwardEvaluator, AwardEvaluationError
from app.services.award_template_service import AwardTemplateService


logger = logging.getLogger(__name__)


class AwardServiceError(Exception):
    """Base exception for award service operations."""
    pass


class AwardGrantError(AwardServiceError):
    """Raised when award granting fails."""
    pass


class AwardRevocationError(AwardServiceError):
    """Raised when award revocation fails."""
    pass


class AwardService:
    """
    Core award service that orchestrates all award-related operations.
    
    This service acts as the main interface for:
    - Evaluating users for awards
    - Granting awards to users
    - Retrieving user awards with filtering and sorting
    - Revoking awards (admin functionality)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.evaluator = AwardEvaluator(db)
        self.template_service = AwardTemplateService(db)
    
    async def evaluate_discovery_awards(
        self, 
        user_id: int, 
        reaction_cache_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> List[UserAward]:
        """
        Evaluate and grant discovery-related awards for a user.
        
        Args:
            user_id: ID of the user to evaluate
            reaction_cache_id: ID of the reaction that triggered the evaluation
            context: Additional context data (e.g., complexity, effects)
            
        Returns:
            List of newly granted awards
            
        Raises:
            AwardServiceError: If evaluation fails
        """
        try:
            # Get all active discovery award templates
            templates = await self.template_service.get_templates(
                category=AwardCategory.DISCOVERY,
                active_only=True
            )
            
            granted_awards = []
            evaluation_context = context or {}
            evaluation_context["reaction_cache_id"] = reaction_cache_id
            
            for template in templates:
                try:
                    # Check if user already has this award
                    existing_award = await self._get_user_award(user_id, template.id)
                    
                    # Check if criteria are met
                    criteria_met = await self.evaluator.check_criteria(
                        template, user_id, evaluation_context
                    )
                    
                    if criteria_met:
                        if existing_award:
                            # Check for tier upgrade
                            upgraded_award = await self._check_tier_upgrade(
                                existing_award, template, user_id, evaluation_context
                            )
                            if upgraded_award:
                                granted_awards.append(upgraded_award)
                        else:
                            # Grant new award
                            new_award = await self.grant_award(
                                user_id, template.id, evaluation_context
                            )
                            granted_awards.append(new_award)
                            
                except Exception as e:
                    logger.warning(
                        f"Failed to evaluate template {template.id} for user {user_id}: {e}"
                    )
                    continue
            
            return granted_awards
            
        except Exception as e:
            logger.error(f"Discovery award evaluation failed for user {user_id}: {e}")
            raise AwardServiceError(f"Discovery award evaluation failed: {e}")
    
    async def evaluate_debug_contribution_awards(
        self, 
        user_id: int, 
        contribution_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[UserAward]:
        """
        Evaluate and grant debug contribution awards for a user.
        
        Args:
            user_id: ID of the user to evaluate
            contribution_type: Type of contribution (e.g., "chemical_correction")
            context: Additional context data
            
        Returns:
            List of newly granted awards
            
        Raises:
            AwardServiceError: If evaluation fails
        """
        try:
            # Get all active database contribution award templates
            templates = await self.template_service.get_templates(
                category=AwardCategory.DATABASE_CONTRIBUTION,
                active_only=True
            )
            
            granted_awards = []
            evaluation_context = context or {}
            evaluation_context["contribution_type"] = contribution_type
            
            for template in templates:
                try:
                    # Check if user already has this award
                    existing_award = await self._get_user_award(user_id, template.id)
                    
                    # Check if criteria are met
                    criteria_met = await self.evaluator.check_criteria(
                        template, user_id, evaluation_context
                    )
                    
                    if criteria_met:
                        if existing_award:
                            # Check for tier upgrade
                            upgraded_award = await self._check_tier_upgrade(
                                existing_award, template, user_id, evaluation_context
                            )
                            if upgraded_award:
                                granted_awards.append(upgraded_award)
                        else:
                            # Grant new award
                            new_award = await self.grant_award(
                                user_id, template.id, evaluation_context
                            )
                            granted_awards.append(new_award)
                            
                except Exception as e:
                    logger.warning(
                        f"Failed to evaluate template {template.id} for user {user_id}: {e}"
                    )
                    continue
            
            return granted_awards
            
        except Exception as e:
            logger.error(f"Debug contribution award evaluation failed for user {user_id}: {e}")
            raise AwardServiceError(f"Debug contribution award evaluation failed: {e}")
    
    async def grant_award(
        self, 
        user_id: int, 
        template_id: int, 
        context: Optional[Dict[str, Any]] = None
    ) -> UserAward:
        """
        Grant an award to a user.
        
        Args:
            user_id: ID of the user to grant the award to
            template_id: ID of the award template
            context: Additional context data for the award
            
        Returns:
            The granted UserAward instance
            
        Raises:
            AwardGrantError: If award granting fails
        """
        try:
            # Verify user exists
            user = self.db.exec(select(User).where(User.id == user_id)).first()
            if not user:
                raise AwardGrantError(f"User {user_id} not found")
            
            # Get award template
            template = await self.template_service.get_template(template_id)
            if not template:
                raise AwardGrantError(f"Award template {template_id} not found")
            
            if not template.is_active:
                raise AwardGrantError(f"Award template {template_id} is not active")
            
            # Check if user already has this award
            existing_award = await self._get_user_award(user_id, template_id)
            if existing_award:
                raise AwardGrantError(
                    f"User {user_id} already has award {template_id}"
                )
            
            # Get user statistics for tier calculation
            user_stats = await self.evaluator._get_user_statistics(
                user_id, template.criteria.get("type"), context
            )
            
            # Determine appropriate tier
            tier = await self.evaluator.determine_tier(template, user_stats)
            
            # Calculate progress
            progress = await self.evaluator.calculate_progress(
                template, user_id, context
            )
            
            # Create award record
            award = UserAward(
                user_id=user_id,
                template_id=template_id,
                tier=tier,
                progress=progress,
                granted_at=datetime.utcnow(),
                related_entity_type=context.get("entity_type") if context else None,
                related_entity_id=context.get("entity_id") if context else None
            )
            
            self.db.add(award)
            self.db.commit()
            self.db.refresh(award)
            
            logger.info(
                f"Granted award {template.name} (tier {tier}) to user {user_id}"
            )
            
            return award
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to grant award {template_id} to user {user_id}: {e}")
            raise AwardGrantError(f"Failed to grant award: {e}")
    
    async def get_user_awards(
        self,
        user_id: int,
        category: Optional[AwardCategory] = None,
        sort_by: str = "granted_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve awards for a specific user with filtering and sorting.
        
        Args:
            user_id: ID of the user
            category: Optional category filter
            sort_by: Field to sort by (granted_at, tier, template_name)
            sort_order: Sort order (asc, desc)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of award dictionaries with template information
        """
        try:
            # Build base query
            query = (
                select(UserAward, AwardTemplate)
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .where(UserAward.user_id == user_id)
            )
            
            # Apply category filter
            if category:
                query = query.where(AwardTemplate.category == category)
            
            # Apply sorting
            if sort_by == "granted_at":
                sort_column = UserAward.granted_at
            elif sort_by == "tier":
                sort_column = UserAward.tier
            elif sort_by == "template_name":
                sort_column = AwardTemplate.name
            else:
                sort_column = UserAward.granted_at
            
            if sort_order.lower() == "asc":
                query = query.order_by(asc(sort_column))
            else:
                query = query.order_by(desc(sort_column))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            results = self.db.exec(query).all()
            
            # Format results
            awards = []
            for user_award, template in results:
                award_dict = {
                    "id": user_award.id,
                    "user_id": user_award.user_id,
                    "template_id": user_award.template_id,
                    "tier": user_award.tier,
                    "progress": user_award.progress,
                    "granted_at": user_award.granted_at,
                    "related_entity_type": user_award.related_entity_type,
                    "related_entity_id": user_award.related_entity_id,
                    "template": {
                        "name": template.name,
                        "description": template.description,
                        "category": template.category,
                        "metadata": template.award_metadata
                    }
                }
                awards.append(award_dict)
            
            return awards
            
        except Exception as e:
            logger.error(f"Failed to retrieve awards for user {user_id}: {e}")
            raise AwardServiceError(f"Failed to retrieve user awards: {e}")
    
    async def get_available_awards(
        self,
        user_id: int,
        category: Optional[AwardCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available awards for a user with progress information.
        
        Args:
            user_id: ID of the user
            category: Optional category filter
            
        Returns:
            List of available awards with progress information
        """
        try:
            # Get all active templates
            templates = await self.template_service.get_templates(
                category=category,
                active_only=True
            )
            
            # Get user's existing awards
            user_award_template_ids = set()
            existing_awards = self.db.exec(
                select(UserAward.template_id).where(UserAward.user_id == user_id)
            ).all()
            user_award_template_ids.update(existing_awards)
            
            available_awards = []
            
            for template in templates:
                # Skip if user already has this award
                if template.id in user_award_template_ids:
                    continue
                
                try:
                    # Calculate progress toward this award
                    progress = await self.evaluator.calculate_progress(
                        template, user_id
                    )
                    
                    award_info = {
                        "template_id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "category": template.category,
                        "metadata": template.award_metadata,
                        "progress": progress
                    }
                    
                    available_awards.append(award_info)
                    
                except Exception as e:
                    logger.warning(
                        f"Failed to calculate progress for template {template.id}: {e}"
                    )
                    continue
            
            return available_awards
            
        except Exception as e:
            logger.error(f"Failed to get available awards for user {user_id}: {e}")
            raise AwardServiceError(f"Failed to get available awards: {e}")
    
    async def revoke_award(
        self, 
        award_id: int, 
        reason: Optional[str] = None
    ) -> bool:
        """
        Revoke an award (admin functionality).
        
        Args:
            award_id: ID of the award to revoke
            reason: Optional reason for revocation
            
        Returns:
            True if revocation was successful
            
        Raises:
            AwardRevocationError: If revocation fails
        """
        try:
            # Get the award
            award = self.db.exec(
                select(UserAward).where(UserAward.id == award_id)
            ).first()
            
            if not award:
                raise AwardRevocationError(f"Award {award_id} not found")
            
            # Delete the award record
            self.db.delete(award)
            self.db.commit()
            
            logger.info(
                f"Revoked award {award_id} from user {award.user_id}. Reason: {reason}"
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to revoke award {award_id}: {e}")
            raise AwardRevocationError(f"Failed to revoke award: {e}")
    
    async def get_leaderboard(
        self,
        category: Optional[AwardCategory] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard rankings based on award points.
        
        Args:
            category: Optional category filter
            limit: Maximum number of users to return
            
        Returns:
            List of user rankings with award statistics
        """
        try:
            # Build query to calculate user points
            query = (
                select(
                    UserAward.user_id,
                    User.username,
                    func.count(UserAward.id).label("award_count"),
                    func.sum(
                        func.json_extract(AwardTemplate.award_metadata, "$.points")
                    ).label("total_points")
                )
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .join(User, UserAward.user_id == User.id)
                .where(User.is_active == True)
            )
            
            # Apply category filter
            if category:
                query = query.where(AwardTemplate.category == category)
            
            # Group and order
            query = (
                query.group_by(UserAward.user_id, User.username)
                .order_by(desc("total_points"), desc("award_count"))
                .limit(limit)
            )
            
            results = self.db.exec(query).all()
            
            leaderboard = []
            for rank, (user_id, username, award_count, total_points) in enumerate(results, 1):
                leaderboard.append({
                    "rank": rank,
                    "user_id": user_id,
                    "username": username,
                    "award_count": award_count or 0,
                    "total_points": int(total_points or 0)
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            raise AwardServiceError(f"Failed to get leaderboard: {e}")
    
    async def _get_user_award(self, user_id: int, template_id: int) -> Optional[UserAward]:
        """Get existing award for user and template."""
        return self.db.exec(
            select(UserAward).where(
                and_(
                    UserAward.user_id == user_id,
                    UserAward.template_id == template_id
                )
            )
        ).first()
    
    async def _check_tier_upgrade(
        self,
        existing_award: UserAward,
        template: AwardTemplate,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[UserAward]:
        """
        Check if an existing award should be upgraded to a higher tier.
        
        Args:
            existing_award: The existing award
            template: The award template
            user_id: ID of the user
            context: Additional context data
            
        Returns:
            Updated award if tier was upgraded, None otherwise
        """
        try:
            # Get current user statistics
            user_stats = await self.evaluator._get_user_statistics(
                user_id, template.criteria.get("type"), context
            )
            
            # Determine new tier
            new_tier = await self.evaluator.determine_tier(template, user_stats)
            
            # Check if tier should be upgraded
            if new_tier > existing_award.tier:
                existing_award.tier = new_tier
                existing_award.progress = await self.evaluator.calculate_progress(
                    template, user_id, context
                )
                
                self.db.add(existing_award)
                self.db.commit()
                self.db.refresh(existing_award)
                
                logger.info(
                    f"Upgraded award {template.name} to tier {new_tier} for user {user_id}"
                )
                
                return existing_award
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to check tier upgrade: {e}")
            return None