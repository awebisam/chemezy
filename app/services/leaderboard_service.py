"""
Leaderboard Service

Handles leaderboard generation, caching, and community features for the award system.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlmodel import Session, select, func, desc, asc, and_
from datetime import datetime, timedelta
import logging
import json
from functools import lru_cache

from app.models.award import AwardTemplate, UserAward, AwardCategory
from app.models.user import User
from app.services.cache_service import leaderboard_cache


logger = logging.getLogger(__name__)


class LeaderboardServiceError(Exception):
    """Base exception for leaderboard service operations."""
    pass


class LeaderboardService:
    """
    Service for managing leaderboards and community features.
    
    Provides category-based rankings, caching for performance,
    and public profile viewing functionality.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def get_category_leaderboard(
        self,
        category: AwardCategory,
        limit: int = 50,
        include_ties: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get leaderboard rankings for a specific award category.
        
        Args:
            category: Award category to rank by
            limit: Maximum number of users to return
            include_ties: Whether to include tied users beyond limit
            
        Returns:
            List of user rankings with award statistics
        """
        try:
            # Check cache first
            cached_result = leaderboard_cache.get_category_leaderboard(
                category.value, limit
            )
            if cached_result:
                return cached_result
            
            # Build query to calculate user points and awards for category
            query = (
                select(
                    UserAward.user_id,
                    User.username,
                    func.count(UserAward.id).label("award_count"),
                    func.sum(
                        func.coalesce(
                            func.json_extract(AwardTemplate.award_metadata, "$.points"),
                            0
                        )
                    ).label("total_points"),
                    func.max(UserAward.granted_at).label("latest_award")
                )
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .join(User, UserAward.user_id == User.id)
                .where(
                    and_(
                        User.is_active == True,
                        AwardTemplate.category == category
                    )
                )
                .group_by(UserAward.user_id, User.username)
                .order_by(
                    desc("total_points"),
                    desc("award_count"),
                    desc("latest_award")
                )
            )
            
            # Execute query with limit
            results = self.db.exec(query.limit(limit * 2)).all()  # Get extra for ties
            
            # Process results and handle ties
            leaderboard = []
            current_rank = 1
            prev_points = None
            prev_awards = None
            
            for i, (user_id, username, award_count, total_points, latest_award) in enumerate(results):
                points = int(total_points or 0)
                awards = int(award_count or 0)
                
                # Handle ranking with ties
                if prev_points is not None and (points != prev_points or awards != prev_awards):
                    current_rank = i + 1
                
                entry = {
                    "rank": current_rank,
                    "user_id": user_id,
                    "username": username,
                    "award_count": awards,
                    "total_points": points,
                    "latest_award": latest_award,
                    "category": category.value
                }
                
                leaderboard.append(entry)
                prev_points = points
                prev_awards = awards
                
                # Stop if we've reached the limit and not including ties
                if not include_ties and len(leaderboard) >= limit:
                    break
                
                # Stop if we've reached limit and next entry would have different score
                if (include_ties and len(leaderboard) >= limit and 
                    i + 1 < len(results)):
                    next_result = results[i + 1]
                    next_points = int(next_result[2] or 0)
                    next_awards = int(next_result[1] or 0)
                    if next_points != points or next_awards != awards:
                        break
            
            # Cache the result
            leaderboard_cache.set_category_leaderboard(
                category.value, limit, leaderboard
            )
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get category leaderboard for {category}: {e}")
            raise LeaderboardServiceError(f"Failed to get category leaderboard: {e}")
    
    async def get_overall_leaderboard(
        self,
        limit: int = 50,
        include_ties: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get overall leaderboard across all award categories.
        
        Args:
            limit: Maximum number of users to return
            include_ties: Whether to include tied users beyond limit
            
        Returns:
            List of user rankings with overall award statistics
        """
        try:
            cache_key = f"leaderboard_overall_{limit}_{include_ties}"
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Build query to calculate overall user points and awards
            query = (
                select(
                    UserAward.user_id,
                    User.username,
                    func.count(UserAward.id).label("award_count"),
                    func.sum(
                        func.coalesce(
                            func.json_extract(AwardTemplate.award_metadata, "$.points"),
                            0
                        )
                    ).label("total_points"),
                    func.max(UserAward.granted_at).label("latest_award"),
                    func.count(
                        func.distinct(AwardTemplate.category)
                    ).label("category_count")
                )
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .join(User, UserAward.user_id == User.id)
                .where(User.is_active == True)
                .group_by(UserAward.user_id, User.username)
                .order_by(
                    desc("total_points"),
                    desc("award_count"),
                    desc("category_count"),
                    desc("latest_award")
                )
            )
            
            # Execute query with limit
            results = self.db.exec(query.limit(limit * 2)).all()  # Get extra for ties
            
            # Process results and handle ties
            leaderboard = []
            current_rank = 1
            prev_points = None
            prev_awards = None
            
            for i, (user_id, username, award_count, total_points, latest_award, category_count) in enumerate(results):
                points = int(total_points or 0)
                awards = int(award_count or 0)
                categories = int(category_count or 0)
                
                # Handle ranking with ties
                if prev_points is not None and (points != prev_points or awards != prev_awards):
                    current_rank = i + 1
                
                entry = {
                    "rank": current_rank,
                    "user_id": user_id,
                    "username": username,
                    "award_count": awards,
                    "total_points": points,
                    "category_count": categories,
                    "latest_award": latest_award,
                    "category": "overall"
                }
                
                leaderboard.append(entry)
                prev_points = points
                prev_awards = awards
                
                # Stop if we've reached the limit and not including ties
                if not include_ties and len(leaderboard) >= limit:
                    break
                
                # Stop if we've reached limit and next entry would have different score
                if (include_ties and len(leaderboard) >= limit and 
                    i + 1 < len(results)):
                    next_result = results[i + 1]
                    next_points = int(next_result[3] or 0)
                    next_awards = int(next_result[2] or 0)
                    if next_points != points or next_awards != awards:
                        break
            
            # Cache the result
            self._cache_result(cache_key, leaderboard)
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get overall leaderboard: {e}")
            raise LeaderboardServiceError(f"Failed to get overall leaderboard: {e}")
    
    async def get_user_rank(
        self,
        user_id: int,
        category: Optional[AwardCategory] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific user's rank in the leaderboard.
        
        Args:
            user_id: ID of the user
            category: Optional category filter (None for overall)
            
        Returns:
            User's rank information or None if not found
        """
        try:
            if category:
                leaderboard = await self.get_category_leaderboard(
                    category, limit=1000, include_ties=True
                )
            else:
                leaderboard = await self.get_overall_leaderboard(
                    limit=1000, include_ties=True
                )
            
            # Find user in leaderboard
            for entry in leaderboard:
                if entry["user_id"] == user_id:
                    return entry
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user rank for user {user_id}: {e}")
            raise LeaderboardServiceError(f"Failed to get user rank: {e}")
    
    async def get_category_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about award distribution across categories.
        
        Returns:
            Dictionary with category statistics
        """
        try:
            cache_key = "category_statistics"
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Get award counts by category
            query = (
                select(
                    AwardTemplate.category,
                    func.count(UserAward.id).label("total_awards"),
                    func.count(func.distinct(UserAward.user_id)).label("unique_users"),
                    func.avg(
                        func.coalesce(
                            func.json_extract(AwardTemplate.award_metadata, "$.points"),
                            0
                        )
                    ).label("avg_points")
                )
                .join(UserAward, AwardTemplate.id == UserAward.template_id)
                .group_by(AwardTemplate.category)
            )
            
            results = self.db.exec(query).all()
            
            statistics = {}
            for category, total_awards, unique_users, avg_points in results:
                statistics[category.value] = {
                    "total_awards": int(total_awards or 0),
                    "unique_users": int(unique_users or 0),
                    "average_points": float(avg_points or 0)
                }
            
            # Cache the result
            self._cache_result(cache_key, statistics)
            
            return statistics
            
        except Exception as e:
            logger.error(f"Failed to get category statistics: {e}")
            raise LeaderboardServiceError(f"Failed to get category statistics: {e}")
    
    async def get_recent_achievements(
        self,
        limit: int = 20,
        category: Optional[AwardCategory] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent award achievements for community feed.
        
        Args:
            limit: Maximum number of achievements to return
            category: Optional category filter
            
        Returns:
            List of recent achievements
        """
        try:
            cache_key = f"recent_achievements_{limit}_{category.value if category else 'all'}"
            
            # Check cache first
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Build query for recent achievements
            query = (
                select(
                    UserAward.user_id,
                    User.username,
                    UserAward.tier,
                    UserAward.granted_at,
                    AwardTemplate.name.label("award_name"),
                    AwardTemplate.category,
                    AwardTemplate.award_metadata
                )
                .join(AwardTemplate, UserAward.template_id == AwardTemplate.id)
                .join(User, UserAward.user_id == User.id)
                .where(User.is_active == True)
                .order_by(desc(UserAward.granted_at))
            )
            
            # Apply category filter
            if category:
                query = query.where(AwardTemplate.category == category)
            
            # Execute query
            results = self.db.exec(query.limit(limit)).all()
            
            # Format results
            achievements = []
            for (user_id, username, tier, granted_at, award_name, 
                 award_category, metadata) in results:
                
                achievement = {
                    "user_id": user_id,
                    "username": username,
                    "award_name": award_name,
                    "category": award_category.value,
                    "tier": tier,
                    "granted_at": granted_at,
                    "metadata": metadata or {}
                }
                achievements.append(achievement)
            
            # Cache the result
            self._cache_result(cache_key, achievements)
            
            return achievements
            
        except Exception as e:
            logger.error(f"Failed to get recent achievements: {e}")
            raise LeaderboardServiceError(f"Failed to get recent achievements: {e}")
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """
        Invalidate cached results.
        
        Args:
            pattern: Optional pattern to match cache keys (None to clear all)
        """
        if pattern:
            keys_to_remove = [key for key in self._cache.keys() if pattern in key]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
        
        logger.info(f"Invalidated cache with pattern: {pattern}")
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get result from cache if not expired."""
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self._cache_ttl):
                return cached_data
            else:
                # Remove expired entry
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache a result with timestamp."""
        self._cache[cache_key] = (result, datetime.utcnow())
        
        # Simple cache size management - remove oldest entries if cache gets too large
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]