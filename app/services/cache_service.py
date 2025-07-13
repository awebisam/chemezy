"""
Cache Service for Award System Performance

Provides caching functionality for frequently accessed data.
"""

import json
import time
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """
    Simple in-memory cache service with TTL (Time To Live) support.
    
    In a production environment, this would be replaced with Redis or Memcached.
    """
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
    
    def _generate_key(self, key: str, **kwargs) -> str:
        """Generate a cache key with optional parameters."""
        if not kwargs:
            return key
        
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        params_str = json.dumps(sorted_kwargs, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        
        return f"{key}:{params_hash}"
    
    def get(self, key: str, **kwargs) -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._generate_key(key, **kwargs)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Check if expired
            if entry["expires_at"] > time.time():
                self.stats["hits"] += 1
                return entry["value"]
            else:
                # Remove expired entry
                del self.cache[cache_key]
                self.stats["evictions"] += 1
        
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, **kwargs) -> None:
        """Set value in cache with TTL."""
        cache_key = self._generate_key(key, **kwargs)
        ttl = ttl or self.default_ttl
        
        self.cache[cache_key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time()
        }
        
        self.stats["sets"] += 1
    
    def delete(self, key: str, **kwargs) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_key(key, **kwargs)
        
        if cache_key in self.cache:
            del self.cache[cache_key]
            return True
        
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry["expires_at"] <= current_time:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        self.stats["evictions"] += len(expired_keys)
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            "hit_rate_percentage": round(hit_rate, 2),
            "total_entries": len(self.cache),
            "total_requests": total_requests
        }
    
    def get_size_info(self) -> Dict[str, Any]:
        """Get cache size information."""
        try:
            import sys
            total_size = sum(sys.getsizeof(entry) for entry in self.cache.values())
            avg_size = total_size / len(self.cache) if self.cache else 0
            
            return {
                "total_entries": len(self.cache),
                "total_size_bytes": total_size,
                "average_entry_size_bytes": round(avg_size, 2)
            }
        except ImportError:
            return {
                "total_entries": len(self.cache),
                "total_size_bytes": -1,
                "average_entry_size_bytes": -1
            }


# Global cache instance
cache = CacheService()


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            func_name = f"{key_prefix}:{func.__name__}" if key_prefix else func.__name__
            
            # Create a hashable representation of arguments
            args_str = str(args) + str(sorted(kwargs.items()))
            args_hash = hashlib.md5(args_str.encode()).hexdigest()[:8]
            cache_key = f"{func_name}:{args_hash}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func_name}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func_name}, result cached")
            
            return result
        return wrapper
    return decorator


class LeaderboardCache:
    """Specialized cache for leaderboard data."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.leaderboard_ttl = 300  # 5 minutes
        self.user_rank_ttl = 60     # 1 minute
    
    def get_category_leaderboard(self, category: str, limit: int = 50) -> Optional[Any]:
        """Get cached category leaderboard."""
        return self.cache.get("leaderboard:category", category=category, limit=limit)
    
    def set_category_leaderboard(self, category: str, limit: int, data: Any) -> None:
        """Cache category leaderboard."""
        self.cache.set("leaderboard:category", data, self.leaderboard_ttl, 
                      category=category, limit=limit)
    
    def get_overall_leaderboard(self, limit: int = 50) -> Optional[Any]:
        """Get cached overall leaderboard."""
        return self.cache.get("leaderboard:overall", limit=limit)
    
    def set_overall_leaderboard(self, limit: int, data: Any) -> None:
        """Cache overall leaderboard."""
        self.cache.set("leaderboard:overall", data, self.leaderboard_ttl, limit=limit)
    
    def get_user_rank(self, user_id: int, category: Optional[str] = None) -> Optional[Any]:
        """Get cached user rank."""
        return self.cache.get("user:rank", user_id=user_id, category=category)
    
    def set_user_rank(self, user_id: int, category: Optional[str], data: Any) -> None:
        """Cache user rank."""
        self.cache.set("user:rank", data, self.user_rank_ttl, 
                      user_id=user_id, category=category)
    
    def invalidate_user_data(self, user_id: int) -> None:
        """Invalidate all cached data for a user."""
        # In a real implementation, you'd have better key management
        # For now, we'll clear related patterns
        self.cache.delete("user:rank", user_id=user_id)
        # Could also invalidate leaderboards, but that's expensive
    
    def invalidate_leaderboards(self) -> None:
        """Invalidate all leaderboard caches."""
        # In a real implementation, you'd use pattern matching
        # For now, clear the whole cache (not ideal but simple)
        keys_to_delete = [key for key in self.cache.cache.keys() 
                         if key.startswith("leaderboard:")]
        for key in keys_to_delete:
            del self.cache.cache[key]


class AwardCache:
    """Specialized cache for award data."""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.template_ttl = 600     # 10 minutes
        self.user_awards_ttl = 300  # 5 minutes
        self.progress_ttl = 180     # 3 minutes
    
    def get_active_templates(self, category: Optional[str] = None) -> Optional[Any]:
        """Get cached active templates."""
        return self.cache.get("templates:active", category=category)
    
    def set_active_templates(self, category: Optional[str], data: Any) -> None:
        """Cache active templates."""
        self.cache.set("templates:active", data, self.template_ttl, category=category)
    
    def get_user_awards(self, user_id: int, category: Optional[str] = None) -> Optional[Any]:
        """Get cached user awards."""
        return self.cache.get("user:awards", user_id=user_id, category=category)
    
    def set_user_awards(self, user_id: int, category: Optional[str], data: Any) -> None:
        """Cache user awards."""
        self.cache.set("user:awards", data, self.user_awards_ttl, 
                      user_id=user_id, category=category)
    
    def get_user_progress(self, user_id: int) -> Optional[Any]:
        """Get cached user progress."""
        return self.cache.get("user:progress", user_id=user_id)
    
    def set_user_progress(self, user_id: int, data: Any) -> None:
        """Cache user progress."""
        self.cache.set("user:progress", data, self.progress_ttl, user_id=user_id)
    
    def invalidate_user_data(self, user_id: int) -> None:
        """Invalidate all cached data for a user."""
        self.cache.delete("user:awards", user_id=user_id)
        self.cache.delete("user:progress", user_id=user_id)
    
    def invalidate_templates(self) -> None:
        """Invalidate template caches."""
        keys_to_delete = [key for key in self.cache.cache.keys() 
                         if key.startswith("templates:")]
        for key in keys_to_delete:
            del self.cache.cache[key]


# Global cache instances
leaderboard_cache = LeaderboardCache(cache)
award_cache = AwardCache(cache)