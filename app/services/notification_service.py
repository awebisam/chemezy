"""
Award Notification Service

Handles award notifications and user dashboard features.
"""

from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, desc
from datetime import datetime, timedelta
import logging

from app.models.award import UserAward, AwardTemplate, AwardCategory
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationServiceError(Exception):
    """Base exception for notification service operations."""
    pass


class NotificationService:
    """Service for managing award notifications and dashboard features."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_recent_awards(
        self, 
        user_id: int, 
        limit: int = 10, 
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get user's recent awards for dashboard display.
        
        Args:
            user_id: User ID to get awards for
            limit: Maximum number of awards to return
            days_back: Number of days back to look for awards
            
        Returns:
            List of recent award dictionaries
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Query recent awards with template information
            query = (
                select(UserAward, AwardTemplate)
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .where(
                    UserAward.user_id == user_id,
                    UserAward.granted_at >= cutoff_date
                )
                .order_by(desc(UserAward.granted_at))
                .limit(limit)
            )
            
            results = self.db.exec(query).all()
            
            recent_awards = []
            for user_award, template in results:
                award_info = {
                    "id": user_award.id,
                    "template_id": template.id,
                    "template_name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "tier": user_award.tier,
                    "granted_at": user_award.granted_at,
                    "metadata": template.award_metadata,
                    "is_new": (datetime.utcnow() - user_award.granted_at).days <= 1
                }
                recent_awards.append(award_info)
            
            return recent_awards
            
        except Exception as e:
            logger.error(f"Failed to get recent awards for user {user_id}: {e}")
            raise NotificationServiceError(f"Failed to get recent awards: {e}")
    
    async def get_award_progress(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's progress toward unearned awards.
        
        Args:
            user_id: User ID to get progress for
            
        Returns:
            Dictionary with progress information
        """
        try:
            # Get all active templates
            active_templates = self.db.exec(
                select(AwardTemplate).where(AwardTemplate.is_active == True)
            ).all()
            
            # Get user's earned awards
            user_awards = self.db.exec(
                select(UserAward).where(UserAward.user_id == user_id)
            ).all()
            
            earned_template_ids = {award.template_id for award in user_awards}
            
            # Calculate progress for unearned awards
            progress_info = {
                "total_awards_available": len(active_templates),
                "total_awards_earned": len(user_awards),
                "progress_percentage": (len(user_awards) / len(active_templates)) * 100 if active_templates else 0,
                "category_progress": {},
                "next_awards": []
            }
            
            # Group by category
            category_counts = {}
            for template in active_templates:
                category = template.category
                if category not in category_counts:
                    category_counts[category] = {"total": 0, "earned": 0}
                category_counts[category]["total"] += 1
                
                if template.id in earned_template_ids:
                    category_counts[category]["earned"] += 1
                else:
                    # Add to next awards (simulate progress)
                    progress_info["next_awards"].append({
                        "template_id": template.id,
                        "name": template.name,
                        "description": template.description,
                        "category": category,
                        "estimated_progress": 0,  # Would need actual progress calculation
                        "metadata": template.award_metadata
                    })
            
            # Calculate category progress
            for category, counts in category_counts.items():
                progress_info["category_progress"][category.value] = {
                    "earned": counts["earned"],
                    "total": counts["total"],
                    "percentage": (counts["earned"] / counts["total"]) * 100 if counts["total"] > 0 else 0
                }
            
            # Limit next awards to top 5
            progress_info["next_awards"] = progress_info["next_awards"][:5]
            
            return progress_info
            
        except Exception as e:
            logger.error(f"Failed to get award progress for user {user_id}: {e}")
            raise NotificationServiceError(f"Failed to get award progress: {e}")
    
    async def get_award_notifications(
        self, 
        user_id: int, 
        unread_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get award notifications for a user.
        
        Args:
            user_id: User ID to get notifications for
            unread_only: Only return unread notifications
            
        Returns:
            List of notification dictionaries
        """
        try:
            # For now, use recent awards as notifications
            # In a real implementation, you'd have a separate notifications table
            recent_awards = await self.get_recent_awards(user_id, limit=20, days_back=30)
            
            notifications = []
            for award in recent_awards:
                notification = {
                    "id": f"award_{award['id']}",
                    "type": "award_granted",
                    "title": f"<Æ Award Earned: {award['template_name']}",
                    "message": f"You earned the {award['template_name']} award (Tier {award['tier']})!",
                    "timestamp": award['granted_at'],
                    "read": not award['is_new'],
                    "metadata": {
                        "award_id": award['id'],
                        "template_id": award['template_id'],
                        "category": award['category'].value,
                        "tier": award['tier']
                    }
                }
                
                if unread_only and notification['read']:
                    continue
                    
                notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            raise NotificationServiceError(f"Failed to get notifications: {e}")
    
    async def get_dashboard_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with dashboard statistics
        """
        try:
            # Get user's awards
            user_awards = self.db.exec(
                select(UserAward).where(UserAward.user_id == user_id)
            ).all()
            
            # Get recent awards
            recent_awards = await self.get_recent_awards(user_id, limit=5)
            
            # Get progress information
            progress_info = await self.get_award_progress(user_id)
            
            # Calculate statistics
            total_points = 0
            category_stats = {}
            tier_distribution = {}
            
            for award in user_awards:
                # Get template for metadata
                template = self.db.exec(
                    select(AwardTemplate).where(AwardTemplate.id == award.template_id)
                ).first()
                
                if template:
                    category = template.category.value
                    tier = award.tier
                    
                    # Points calculation (from metadata or default)
                    points = template.award_metadata.get('points', 10) * tier
                    total_points += points
                    
                    # Category statistics
                    if category not in category_stats:
                        category_stats[category] = {"count": 0, "points": 0}
                    category_stats[category]["count"] += 1
                    category_stats[category]["points"] += points
                    
                    # Tier distribution
                    if tier not in tier_distribution:
                        tier_distribution[tier] = 0
                    tier_distribution[tier] += 1
            
            dashboard_stats = {
                "total_awards": len(user_awards),
                "total_points": total_points,
                "recent_awards": recent_awards,
                "category_breakdown": category_stats,
                "tier_distribution": tier_distribution,
                "progress": progress_info,
                "achievements_this_week": len([a for a in recent_awards if a['is_new']]),
                "next_milestones": progress_info["next_awards"]
            }
            
            return dashboard_stats
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats for user {user_id}: {e}")
            raise NotificationServiceError(f"Failed to get dashboard stats: {e}")
    
    async def mark_notifications_read(
        self, 
        user_id: int, 
        notification_ids: List[str]
    ) -> bool:
        """
        Mark notifications as read.
        
        Args:
            user_id: User ID
            notification_ids: List of notification IDs to mark as read
            
        Returns:
            True if successful
        """
        try:
            # For now, this is a placeholder since we don't have a notifications table
            # In a real implementation, you'd update the read status in the database
            logger.info(f"Marked {len(notification_ids)} notifications as read for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notifications as read for user {user_id}: {e}")
            raise NotificationServiceError(f"Failed to mark notifications as read: {e}")