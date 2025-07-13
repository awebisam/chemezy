"""
Award Evaluation Engine

Handles criteria checking, tier calculation, and progress tracking for awards.
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlmodel import Session, select, func
from datetime import datetime, timedelta

from app.models.award import AwardTemplate, UserAward, AwardCategory
from app.models.reaction import ReactionCache, Discovery
from app.models.debug import DeletionRequest
from app.models.user import User


class AwardEvaluationError(Exception):
    """Raised when award evaluation encounters an error."""
    pass


class AwardEvaluator:
    """
    Core award evaluation engine that checks criteria, calculates tiers,
    and tracks progress for award templates.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    async def check_criteria(
        self, 
        template: AwardTemplate, 
        user_id: int, 
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if a user meets the criteria for a specific award template.
        
        Args:
            template: The award template to evaluate
            user_id: ID of the user to evaluate
            context: Additional context data for evaluation
            
        Returns:
            True if criteria are met, False otherwise
        """
        if not template.is_active:
            return False
        
        criteria = template.criteria
        criteria_type = criteria.get("type")
        
        if not criteria_type:
            raise AwardEvaluationError(f"Award template {template.id} missing criteria type")
        
        # Get user statistics for evaluation
        user_stats = await self._get_user_statistics(user_id, criteria_type, context)
        
        # Check criteria based on type
        if criteria_type == "discovery_count":
            return await self._check_discovery_count_criteria(criteria, user_stats)
        elif criteria_type == "unique_effects":
            return await self._check_unique_effects_criteria(criteria, user_stats)
        elif criteria_type == "reaction_complexity":
            return await self._check_reaction_complexity_criteria(criteria, user_stats, context)
        elif criteria_type == "debug_submissions":
            return await self._check_debug_submissions_criteria(criteria, user_stats)
        elif criteria_type == "correction_accuracy":
            return await self._check_correction_accuracy_criteria(criteria, user_stats)
        elif criteria_type == "data_quality_impact":
            return await self._check_data_quality_impact_criteria(criteria, user_stats)
        elif criteria_type == "profile_completeness":
            return await self._check_profile_completeness_criteria(criteria, user_stats)
        elif criteria_type == "consecutive_days":
            return await self._check_consecutive_days_criteria(criteria, user_stats)
        elif criteria_type == "help_others":
            return await self._check_help_others_criteria(criteria, user_stats)
        else:
            raise AwardEvaluationError(f"Unknown criteria type: {criteria_type}")
    
    async def calculate_progress(
        self, 
        template: AwardTemplate, 
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate progress toward earning an award.
        
        Args:
            template: The award template to evaluate
            user_id: ID of the user to evaluate
            context: Additional context data for evaluation
            
        Returns:
            Dictionary containing progress information
        """
        criteria = template.criteria
        criteria_type = criteria.get("type")
        
        if not criteria_type:
            raise AwardEvaluationError(f"Award template {template.id} missing criteria type")
        
        # Get user statistics
        user_stats = await self._get_user_statistics(user_id, criteria_type, context)
        
        # Calculate progress based on criteria type
        progress = {
            "criteria_type": criteria_type,
            "current_value": 0,
            "target_value": criteria.get("threshold", 1),
            "percentage": 0.0,
            "is_complete": False
        }
        
        if criteria_type in ["discovery_count", "debug_submissions", "consecutive_days"]:
            current = user_stats.get("count", 0)
            target = criteria.get("threshold", 1)
            progress.update({
                "current_value": current,
                "target_value": target,
                "percentage": min(100.0, (current / target) * 100.0),
                "is_complete": current >= target
            })
        elif criteria_type == "unique_effects":
            current = user_stats.get("unique_effects_count", 0)
            target = criteria.get("threshold", 1)
            progress.update({
                "current_value": current,
                "target_value": target,
                "percentage": min(100.0, (current / target) * 100.0),
                "is_complete": current >= target
            })
        elif criteria_type == "correction_accuracy":
            accuracy = user_stats.get("accuracy_percentage", 0.0)
            target = criteria.get("threshold", 80.0)
            progress.update({
                "current_value": accuracy,
                "target_value": target,
                "percentage": min(100.0, (accuracy / target) * 100.0),
                "is_complete": accuracy >= target
            })
        elif criteria_type == "profile_completeness":
            completeness = user_stats.get("completeness_percentage", 0.0)
            target = criteria.get("threshold", 100.0)
            progress.update({
                "current_value": completeness,
                "target_value": target,
                "percentage": completeness,
                "is_complete": completeness >= target
            })
        
        return progress
    
    async def determine_tier(
        self, 
        template: AwardTemplate, 
        user_stats: Dict[str, Any]
    ) -> int:
        """
        Determine the appropriate tier for an award based on user statistics.
        
        Args:
            template: The award template
            user_stats: User statistics dictionary
            
        Returns:
            Tier number (1-based)
        """
        metadata = template.award_metadata
        tiers = metadata.get("tiers", [])
        
        if not tiers:
            return 1  # Default tier
        
        criteria_type = template.criteria.get("type")
        
        # Get the relevant statistic for tier calculation
        if criteria_type in ["discovery_count", "debug_submissions", "consecutive_days"]:
            stat_value = user_stats.get("count", 0)
        elif criteria_type == "unique_effects":
            stat_value = user_stats.get("unique_effects_count", 0)
        elif criteria_type == "correction_accuracy":
            stat_value = user_stats.get("accuracy_percentage", 0.0)
        elif criteria_type == "profile_completeness":
            stat_value = user_stats.get("completeness_percentage", 0.0)
        else:
            stat_value = user_stats.get("count", 0)
        
        # Find the highest tier the user qualifies for
        qualified_tier = 1
        for tier in sorted(tiers, key=lambda t: t.get("threshold", 0)):
            threshold = tier.get("threshold", 0)
            if stat_value >= threshold:
                qualified_tier = max(qualified_tier, tiers.index(tier) + 1)
        
        return qualified_tier
    
    async def _get_user_statistics(
        self, 
        user_id: int, 
        criteria_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get user statistics relevant to the criteria type."""
        stats = {}
        
        if criteria_type == "discovery_count":
            # Count total discoveries by user
            discovery_count = self.db.exec(
                select(func.count(Discovery.id)).where(Discovery.discovered_by == user_id)
            ).first() or 0
            stats["count"] = discovery_count
            
        elif criteria_type == "unique_effects":
            # Count unique effects discovered by user
            unique_effects = self.db.exec(
                select(func.count(func.distinct(Discovery.effect)))
                .where(Discovery.discovered_by == user_id)
            ).first() or 0
            stats["unique_effects_count"] = unique_effects
            
        elif criteria_type == "reaction_complexity":
            # Get complexity from context (calculated during reaction processing)
            if context:
                stats["complexity"] = context.get("complexity", 0)
            else:
                stats["complexity"] = 0
                
        elif criteria_type == "debug_submissions":
            # Count debug submissions by user
            debug_count = self.db.exec(
                select(func.count(DeletionRequest.id))
                .where(DeletionRequest.status == "completed")  # Assuming completed submissions
            ).first() or 0
            stats["count"] = debug_count
            
        elif criteria_type == "correction_accuracy":
            # Calculate accuracy of debug submissions
            total_submissions = self.db.exec(
                select(func.count(DeletionRequest.id))
            ).first() or 0
            
            successful_submissions = self.db.exec(
                select(func.count(DeletionRequest.id))
                .where(DeletionRequest.status == "completed")
            ).first() or 0
            
            if total_submissions > 0:
                accuracy = (successful_submissions / total_submissions) * 100.0
            else:
                accuracy = 0.0
            
            stats["accuracy_percentage"] = accuracy
            stats["total_submissions"] = total_submissions
            stats["successful_submissions"] = successful_submissions
            
        elif criteria_type == "data_quality_impact":
            # Placeholder for data quality impact calculation
            # This would require more complex analysis of data improvements
            stats["impact_score"] = 0
            
        elif criteria_type == "profile_completeness":
            # Check user profile completeness
            user = self.db.exec(select(User).where(User.id == user_id)).first()
            if user:
                completeness = self._calculate_profile_completeness(user)
                stats["completeness_percentage"] = completeness
            else:
                stats["completeness_percentage"] = 0.0
                
        elif criteria_type == "consecutive_days":
            # Calculate consecutive days of activity
            consecutive_days = await self._calculate_consecutive_days(user_id)
            stats["count"] = consecutive_days
            
        elif criteria_type == "help_others":
            # Placeholder for community help metrics
            stats["help_score"] = 0
        
        return stats
    
    async def _check_discovery_count_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check discovery count criteria."""
        threshold = criteria.get("threshold", 1)
        current_count = user_stats.get("count", 0)
        
        # Check additional conditions if present
        conditions = criteria.get("conditions", [])
        if conditions:
            # Implement condition checking logic here
            pass
        
        return current_count >= threshold
    
    async def _check_unique_effects_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check unique effects criteria."""
        threshold = criteria.get("threshold", 1)
        current_count = user_stats.get("unique_effects_count", 0)
        return current_count >= threshold
    
    async def _check_reaction_complexity_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check reaction complexity criteria."""
        threshold = criteria.get("threshold", 1)
        complexity = user_stats.get("complexity", 0)
        return complexity >= threshold
    
    async def _check_debug_submissions_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check debug submissions criteria."""
        threshold = criteria.get("threshold", 1)
        current_count = user_stats.get("count", 0)
        return current_count >= threshold
    
    async def _check_correction_accuracy_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check correction accuracy criteria."""
        threshold = criteria.get("threshold", 80.0)
        accuracy = user_stats.get("accuracy_percentage", 0.0)
        min_submissions = criteria.get("min_submissions", 5)
        total_submissions = user_stats.get("total_submissions", 0)
        
        # Require minimum number of submissions for accuracy calculation
        return total_submissions >= min_submissions and accuracy >= threshold
    
    async def _check_data_quality_impact_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check data quality impact criteria."""
        threshold = criteria.get("threshold", 1)
        impact_score = user_stats.get("impact_score", 0)
        return impact_score >= threshold
    
    async def _check_profile_completeness_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check profile completeness criteria."""
        threshold = criteria.get("threshold", 100.0)
        completeness = user_stats.get("completeness_percentage", 0.0)
        return completeness >= threshold
    
    async def _check_consecutive_days_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check consecutive days criteria."""
        threshold = criteria.get("threshold", 1)
        consecutive_days = user_stats.get("count", 0)
        return consecutive_days >= threshold
    
    async def _check_help_others_criteria(
        self, 
        criteria: Dict[str, Any], 
        user_stats: Dict[str, Any]
    ) -> bool:
        """Check help others criteria."""
        threshold = criteria.get("threshold", 1)
        help_score = user_stats.get("help_score", 0)
        return help_score >= threshold
    
    def _calculate_profile_completeness(self, user: User) -> float:
        """Calculate user profile completeness percentage."""
        total_fields = 3  # username, email, and assuming some profile fields
        completed_fields = 0
        
        if user.username and user.username.strip():
            completed_fields += 1
        if user.email and user.email.strip():
            completed_fields += 1
        if user.is_active:  # Basic activity indicator
            completed_fields += 1
        
        return (completed_fields / total_fields) * 100.0
    
    async def _calculate_consecutive_days(self, user_id: int) -> int:
        """Calculate consecutive days of user activity."""
        # Get recent reaction cache entries to determine activity
        recent_reactions = self.db.exec(
            select(ReactionCache.created_at)
            .where(ReactionCache.user_id == user_id)
            .order_by(ReactionCache.created_at.desc())
            .limit(30)  # Look at last 30 days
        ).all()
        
        if not recent_reactions:
            return 0
        
        # Convert to dates and count consecutive days
        activity_dates = set()
        for reaction in recent_reactions:
            activity_dates.add(reaction.date())
        
        # Sort dates in descending order
        sorted_dates = sorted(activity_dates, reverse=True)
        
        consecutive_days = 0
        current_date = datetime.utcnow().date()
        
        for date in sorted_dates:
            if date == current_date - timedelta(days=consecutive_days):
                consecutive_days += 1
            else:
                break
        
        return consecutive_days