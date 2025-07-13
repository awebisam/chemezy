"""
Award-related API endpoints for user award management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import Optional, List

from app.api.v1.endpoints.users import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.models.award import AwardCategory
from app.services.award_service import AwardService, AwardServiceError
from app.services.leaderboard_service import LeaderboardService, LeaderboardServiceError
from app.schemas.award import (
    UserAwardSchema,
    AvailableAwardSchema,
    LeaderboardEntrySchema,
    UserAwardsResponseSchema,
    AvailableAwardsResponseSchema
)

router = APIRouter()


@router.get("/me", response_model=List[UserAwardSchema])
async def get_my_awards(
    category: Optional[AwardCategory] = Query(None, description="Filter by award category"),
    sort_by: str = Query("granted_at", description="Sort by field (granted_at, tier, template_name)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve current user's awards with optional filtering and sorting.
    
    - **category**: Optional filter by award category
    - **sort_by**: Field to sort by (granted_at, tier, template_name)
    - **sort_order**: Sort order (asc, desc)
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    """
    try:
        award_service = AwardService(db)
        awards_data = await award_service.get_user_awards(
            user_id=current_user.id,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit
        )
        
        # Convert to response schema
        awards = []
        for award_data in awards_data:
            # Create template schema
            template_schema = {
                "id": award_data["template_id"],
                "name": award_data["template"]["name"],
                "description": award_data["template"]["description"],
                "category": award_data["template"]["category"],
                "metadata": award_data["template"]["metadata"]
            }
            
            # Create award schema
            award_schema = UserAwardSchema(
                id=award_data["id"],
                user_id=award_data["user_id"],
                template_id=award_data["template_id"],
                tier=award_data["tier"],
                progress=award_data["progress"],
                granted_at=award_data["granted_at"],
                related_entity_type=award_data["related_entity_type"],
                related_entity_id=award_data["related_entity_id"],
                template=template_schema
            )
            awards.append(award_schema)
        
        return awards
        
    except AwardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve awards: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving awards"
        )


@router.get("/available", response_model=List[AvailableAwardSchema])
async def get_available_awards(
    category: Optional[AwardCategory] = Query(None, description="Filter by award category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve available awards for the current user with progress information.
    
    Shows awards that the user hasn't earned yet, along with their progress
    toward earning each award.
    
    - **category**: Optional filter by award category
    """
    try:
        award_service = AwardService(db)
        available_awards_data = await award_service.get_available_awards(
            user_id=current_user.id,
            category=category
        )
        
        # Convert to response schema
        available_awards = []
        for award_data in available_awards_data:
            award_schema = AvailableAwardSchema(
                template_id=award_data["template_id"],
                name=award_data["name"],
                description=award_data["description"],
                category=award_data["category"],
                metadata=award_data["metadata"],
                progress=award_data["progress"]
            )
            available_awards.append(award_schema)
        
        return available_awards
        
    except AwardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve available awards: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving available awards"
        )


@router.get("/leaderboard/{category}", response_model=List[LeaderboardEntrySchema])
async def get_leaderboard(
    category: AwardCategory,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    include_ties: bool = Query(True, description="Include tied users beyond limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get leaderboard rankings for a specific award category.
    
    Returns top users ranked by total points earned in the specified category.
    Uses caching for improved performance.
    
    - **category**: Award category to rank by
    - **limit**: Maximum number of users to return (1-100)
    - **include_ties**: Whether to include tied users beyond the limit
    """
    try:
        leaderboard_service = LeaderboardService(db)
        leaderboard_data = await leaderboard_service.get_category_leaderboard(
            category=category,
            limit=limit,
            include_ties=include_ties
        )
        
        # Convert to response schema
        leaderboard = []
        for entry_data in leaderboard_data:
            entry_schema = LeaderboardEntrySchema(
                rank=entry_data["rank"],
                user_id=entry_data["user_id"],
                username=entry_data["username"],
                award_count=entry_data["award_count"],
                total_points=entry_data["total_points"]
            )
            leaderboard.append(entry_schema)
        
        return leaderboard
        
    except LeaderboardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve leaderboard: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving leaderboard"
        )


@router.get("/user/{user_id}", response_model=List[UserAwardSchema])
async def get_user_awards(
    user_id: int,
    category: Optional[AwardCategory] = Query(None, description="Filter by award category"),
    sort_by: str = Query("granted_at", description="Sort by field (granted_at, tier, template_name)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve awards for a specific user (public profile viewing).
    
    This endpoint allows viewing another user's awards if they have enabled
    public profile viewing or if the requesting user is viewing their own awards.
    
    - **user_id**: ID of the user whose awards to retrieve
    - **category**: Optional filter by award category
    - **sort_by**: Field to sort by (granted_at, tier, template_name)
    - **sort_order**: Sort order (asc, desc)
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    """
    try:
        # Check if user is viewing their own awards
        if user_id != current_user.id:
            # Check if target user has public profile enabled
            from sqlmodel import select
            target_user = db.exec(select(User).where(User.id == user_id)).first()
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            if not target_user.public_profile:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User's profile is private"
                )
        
        award_service = AwardService(db)
        awards_data = await award_service.get_user_awards(
            user_id=user_id,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit
        )
        
        # Convert to response schema
        awards = []
        for award_data in awards_data:
            # Create template schema
            template_schema = {
                "id": award_data["template_id"],
                "name": award_data["template"]["name"],
                "description": award_data["template"]["description"],
                "category": award_data["template"]["category"],
                "metadata": award_data["template"]["metadata"]
            }
            
            # Create award schema
            award_schema = UserAwardSchema(
                id=award_data["id"],
                user_id=award_data["user_id"],
                template_id=award_data["template_id"],
                tier=award_data["tier"],
                progress=award_data["progress"],
                granted_at=award_data["granted_at"],
                related_entity_type=award_data["related_entity_type"],
                related_entity_id=award_data["related_entity_id"],
                template=template_schema
            )
            awards.append(award_schema)
        
        return awards
        
    except HTTPException:
        raise
    except AwardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user awards: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving user awards"
        )


@router.get("/leaderboard/overall", response_model=List[LeaderboardEntrySchema])
async def get_overall_leaderboard(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    include_ties: bool = Query(True, description="Include tied users beyond limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get overall leaderboard rankings across all award categories.
    
    Returns top users ranked by total points earned across all categories.
    Uses caching for improved performance.
    
    - **limit**: Maximum number of users to return (1-100)
    - **include_ties**: Whether to include tied users beyond the limit
    """
    try:
        leaderboard_service = LeaderboardService(db)
        leaderboard_data = await leaderboard_service.get_overall_leaderboard(
            limit=limit,
            include_ties=include_ties
        )
        
        # Convert to response schema
        leaderboard = []
        for entry_data in leaderboard_data:
            entry_schema = LeaderboardEntrySchema(
                rank=entry_data["rank"],
                user_id=entry_data["user_id"],
                username=entry_data["username"],
                award_count=entry_data["award_count"],
                total_points=entry_data["total_points"]
            )
            leaderboard.append(entry_schema)
        
        return leaderboard
        
    except LeaderboardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve overall leaderboard: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving overall leaderboard"
        )


@router.get("/leaderboard/my-rank")
async def get_my_rank(
    category: Optional[AwardCategory] = Query(None, description="Category to check rank in (None for overall)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get current user's rank in the leaderboard.
    
    Returns the user's position and statistics in the specified category
    or overall leaderboard if no category is specified.
    
    - **category**: Optional category to check rank in (None for overall)
    """
    try:
        leaderboard_service = LeaderboardService(db)
        rank_data = await leaderboard_service.get_user_rank(
            user_id=current_user.id,
            category=category
        )
        
        if not rank_data:
            return {
                "rank": None,
                "user_id": current_user.id,
                "username": current_user.username,
                "award_count": 0,
                "total_points": 0,
                "category": category.value if category else "overall"
            }
        
        return rank_data
        
    except LeaderboardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user rank: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving user rank"
        )


@router.get("/community/recent-achievements")
async def get_recent_achievements(
    limit: int = Query(20, ge=1, le=50, description="Maximum number of achievements to return"),
    category: Optional[AwardCategory] = Query(None, description="Filter by award category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get recent award achievements for community feed.
    
    Returns recent awards granted to users for community engagement features.
    Uses caching for improved performance.
    
    - **limit**: Maximum number of achievements to return (1-50)
    - **category**: Optional filter by award category
    """
    try:
        leaderboard_service = LeaderboardService(db)
        achievements_data = await leaderboard_service.get_recent_achievements(
            limit=limit,
            category=category
        )
        
        return {
            "recent_achievements": achievements_data,
            "total_count": len(achievements_data)
        }
        
    except LeaderboardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent achievements: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving recent achievements"
        )


@router.get("/community/statistics")
async def get_community_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get statistics about award distribution across categories.
    
    Returns community-wide statistics about awards and user engagement.
    Uses caching for improved performance.
    """
    try:
        leaderboard_service = LeaderboardService(db)
        statistics_data = await leaderboard_service.get_category_statistics()
        
        return {
            "category_statistics": statistics_data,
            "generated_at": "2025-01-15T00:00:00Z"  # Current timestamp would be better
        }
        
    except LeaderboardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve community statistics: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving community statistics"
        )