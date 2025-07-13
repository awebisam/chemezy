from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session

from app.db.session import get_session as get_db
from app.services.reaction_service import ReactionService
from app.services.chemical_service import ChemicalService
from app.services.debug_service import DebugService
from app.services.award_service import AwardService
from app.api.v1.endpoints.users import get_current_user
from app.models.user import User
from app.schemas.debug import (
    DebugClearResponseSchema,
    DebugDeletionRequestSchema,
    DebugDeletionResponseSchema
)

router = APIRouter()

@router.delete("/reactions/clear", status_code=200, response_model=DebugClearResponseSchema)
def clear_all_reactions(
    *, 
    db: Session = Depends(get_db)
):
    """
    Clear all reactions from the database.
    """
    reaction_service = ReactionService(db)
    result = reaction_service.clear_all_reactions()
    return DebugClearResponseSchema(**result)

@router.delete("/reactions/{reaction_id}", status_code=202, response_model=DebugDeletionResponseSchema)
async def request_delete_reaction(
    reaction_id: int,
    request: DebugDeletionRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request deletion of a specific reaction.
    """
    try:
        award_service = AwardService(db)
        debug_service = DebugService(db, award_service)
        deletion_request = await debug_service.create_deletion_request(
            item_type="reaction",
            item_id=reaction_id,
            reason=request.reason,
            user_id=current_user.id
        )
        return DebugDeletionResponseSchema(
            message="Deletion request submitted for review.",
            request_id=deletion_request.id
        )
    except Exception as e:
        # Fallback to basic debug service if award service fails
        debug_service = DebugService(db)
        deletion_request = await debug_service.create_deletion_request(
            item_type="reaction",
            item_id=reaction_id,
            reason=request.reason,
            user_id=current_user.id
        )
        return DebugDeletionResponseSchema(
            message="Deletion request submitted for review.",
            request_id=deletion_request.id
        )

@router.delete("/chemicals/clear", status_code=200, response_model=DebugClearResponseSchema)
def clear_all_chemicals(
    *, 
    db: Session = Depends(get_db)
):
    """
    Clear all chemicals from the database.
    """
    chemical_service = ChemicalService(db)
    result = chemical_service.clear_all_chemicals()
    return DebugClearResponseSchema(**result)

@router.delete("/chemicals/{chemical_id}", status_code=202, response_model=DebugDeletionResponseSchema)
async def request_delete_chemical(
    chemical_id: int,
    request: DebugDeletionRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Request deletion of a specific chemical.
    """
    try:
        award_service = AwardService(db)
        debug_service = DebugService(db, award_service)
        deletion_request = await debug_service.create_deletion_request(
            item_type="chemical",
            item_id=chemical_id,
            reason=request.reason,
            user_id=current_user.id
        )
        return DebugDeletionResponseSchema(
            message="Deletion request submitted for review.",
            request_id=deletion_request.id
        )
    except Exception as e:
        # Fallback to basic debug service if award service fails
        debug_service = DebugService(db)
        deletion_request = await debug_service.create_deletion_request(
            item_type="chemical",
            item_id=chemical_id,
            reason=request.reason,
            user_id=current_user.id
        )
        return DebugDeletionResponseSchema(
            message="Deletion request submitted for review.",
            request_id=deletion_request.id
        )
