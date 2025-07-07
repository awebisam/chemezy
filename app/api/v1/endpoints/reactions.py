from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.user import User
from app.models.reaction import ReactionCache, Discovery
from app.services.reaction_engine import ReactionEngineService
from app.schemas.reaction import (
    ReactionRequest, 
    ReactionResponse, 
    ReactionCacheSchema,
    DiscoverySchema
)
from app.api.v1.endpoints.users import get_current_user

router = APIRouter()
reaction_engine = ReactionEngineService()


@router.post("/react", response_model=ReactionResponse)
async def predict_reaction(
    request: ReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Process a chemical reaction prediction request.
    
    This is the core endpoint that receives chemical formulas and environmental
    conditions, then returns a structured prediction of the reaction outcome.
    """
    if not request.chemicals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one chemical must be provided"
        )
    
    try:
        result = await reaction_engine.predict_reaction(
            chemicals=request.chemicals,
            environment=request.environment,
            user_id=current_user.id,
            db=db
        )
        
        # Commit the transaction here (atomic operation)
        db.commit()
        return result
        
    except Exception as e:
        # Rollback on any error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing reaction: {str(e)}"
        )


@router.get("/cache", response_model=List[ReactionCacheSchema])
async def get_reaction_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = 50,
    offset: int = 0
):
    """Get cached reactions for the current user."""
    reactions = db.exec(
        select(ReactionCache)
        .where(ReactionCache.user_id == current_user.id)
        .order_by(ReactionCache.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    
    return [ReactionCacheSchema.from_orm(reaction) for reaction in reactions]


@router.get("/cache/{reaction_id}", response_model=ReactionCacheSchema)
async def get_reaction_by_id(
    reaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get a specific cached reaction by ID."""
    reaction = db.exec(
        select(ReactionCache)
        .where(ReactionCache.id == reaction_id)
        .where(ReactionCache.user_id == current_user.id)
    ).first()
    
    if not reaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )
    
    return ReactionCacheSchema.from_orm(reaction)


@router.get("/discoveries", response_model=List[DiscoverySchema])
async def get_user_discoveries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: int = 50,
    offset: int = 0
):
    """Get world-first discoveries made by the current user."""
    discoveries = db.exec(
        select(Discovery)
        .where(Discovery.discovered_by == current_user.id)
        .order_by(Discovery.discovered_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    
    return [DiscoverySchema.from_orm(discovery) for discovery in discoveries]


@router.get("/discoveries/all", response_model=List[DiscoverySchema])
async def get_all_discoveries(
    db: Session = Depends(get_session),
    limit: int = 100,
    offset: int = 0
):
    """Get all world-first discoveries (public endpoint for leaderboards)."""
    discoveries = db.exec(
        select(Discovery)
        .order_by(Discovery.discovered_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    
    return [DiscoverySchema.from_orm(discovery) for discovery in discoveries]


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Get reaction statistics for the current user."""
    total_reactions = db.exec(
        select(ReactionCache)
        .where(ReactionCache.user_id == current_user.id)
    ).all()
    
    total_discoveries = db.exec(
        select(Discovery)
        .where(Discovery.discovered_by == current_user.id)
    ).all()
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "total_reactions": len(total_reactions),
        "total_discoveries": len(total_discoveries),
        "unique_effects_discovered": [d.effect for d in total_discoveries]
    }