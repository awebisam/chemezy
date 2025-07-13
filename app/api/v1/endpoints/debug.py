from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session

from app.db.session import get_session as get_db
from app.services.reaction_service import ReactionService
from app.services.chemical_service import ChemicalService
from app.services.debug_service import DebugService

router = APIRouter()

@router.delete("/reactions/clear", status_code=200)
def clear_all_reactions(
    *, 
    db: Session = Depends(get_db)
):
    """
    Clear all reactions from the database.
    """
    reaction_service = ReactionService(db)
    result = reaction_service.clear_all_reactions()
    return result

@router.delete("/reactions/{reaction_id}", status_code=202)
def request_delete_reaction(
    reaction_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Request deletion of a specific reaction.
    """
    debug_service = DebugService(db)
    deletion_request = debug_service.create_deletion_request(
        item_type="reaction",
        item_id=reaction_id,
        reason=reason
    )
    return {"message": "Deletion request submitted for review.", "request_id": deletion_request.id}

@router.delete("/chemicals/clear", status_code=200)
def clear_all_chemicals(
    *, 
    db: Session = Depends(get_db)
):
    """
    Clear all chemicals from the database.
    """
    chemical_service = ChemicalService(db)
    result = chemical_service.clear_all_chemicals()
    return result

@router.delete("/chemicals/{chemical_id}", status_code=202)
def request_delete_chemical(
    chemical_id: int,
    reason: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Request deletion of a specific chemical.
    """
    debug_service = DebugService(db)
    deletion_request = debug_service.create_deletion_request(
        item_type="chemical",
        item_id=chemical_id,
        reason=reason
    )
    return {"message": "Deletion request submitted for review.", "request_id": deletion_request.id}
