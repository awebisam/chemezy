from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.services.reaction_service import ReactionService
from app.schemas.reaction import ReactionRequest, ReactionPrediction, UserReactionStatsSchema
from app.api.v1.endpoints.users import get_current_user

router = APIRouter()

@router.post("/react", response_model=ReactionPrediction)
async def predict_reaction(
    request: ReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Process a chemical reaction prediction request.

    This endpoint takes a list of reactant chemical IDs and their quantities,
    predicts the resulting products and effects, and returns a structured
    prediction.
    """
    if not request.reactants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one reactant must be provided."
        )

    try:
        reaction_service = ReactionService(db)
        result = await reaction_service.predict_reaction(request, user_id=current_user.id)
        db.commit()
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing reaction: {str(e)}"
        )

@router.get("/cache", response_model=list[ReactionPrediction])
async def get_reaction_cache(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve the user's reaction cache.
    """
    reaction_service = ReactionService(db)
    return reaction_service.get_user_reaction_cache(user_id=current_user.id)

@router.get("/stats", response_model=UserReactionStatsSchema)
async def get_user_reaction_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve statistics about the user's reactions and discoveries.
    """
    reaction_service = ReactionService(db)
    stats = reaction_service.get_user_reaction_stats(user_id=current_user.id)
    return UserReactionStatsSchema(**stats)