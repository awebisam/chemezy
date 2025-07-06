from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api import deps
from app.models.user import User
from app.schemas.chemical import ChemicalCreate, ChemicalRead, PaginatedChemicalRead
from app.services.chemical_service import ChemicalService

router = APIRouter()


def get_chemical_service() -> ChemicalService:
    return ChemicalService()


@router.post("/", response_model=ChemicalRead, status_code=201)
async def create_chemical(
    *,
    db: Session = Depends(deps.get_db),
    chemical_in: ChemicalCreate,
    current_user: User = Depends(deps.get_current_active_user),
    service: ChemicalService = Depends(get_chemical_service)
) -> Any:
    """
    Create a new chemical from a molecular formula.
    This will trigger a call to an LLM to generate the chemical's properties.
    """
    try:
        chemical = await service.create(db=db, chemical_in=chemical_in)
        return chemical
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/", response_model=PaginatedChemicalRead)
async def read_chemicals(
    db: Session = Depends(deps.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    service: ChemicalService = Depends(get_chemical_service),
) -> Any:
    """
    Retrieve all chemicals with pagination.
    """
    chemicals, total = await service.get_all(db=db, skip=skip, limit=limit)
    return {"count": total, "results": chemicals}


@router.get("/{chemical_id}", response_model=ChemicalRead)
async def read_chemical(
    *,
    db: Session = Depends(deps.get_db),
    chemical_id: int,
    service: ChemicalService = Depends(get_chemical_service)
) -> Any:
    """
    Get a specific chemical by its ID.
    """
    chemical = await service.get(db=db, chemical_id=chemical_id)
    if not chemical:
        raise HTTPException(status_code=404, detail="Chemical not found")
    return chemical


@router.delete("/{chemical_id}", status_code=204)
async def delete_chemical(
    *,
    db: Session = Depends(deps.get_db),
    chemical_id: int,
    current_user: User = Depends(deps.get_current_active_user),
    service: ChemicalService = Depends(get_chemical_service)
) -> None:
    """
    Delete a chemical by its ID.
    """
    chemical = await service.delete(db=db, chemical_id=chemical_id)
    if not chemical:
        raise HTTPException(status_code=404, detail="Chemical not found")
    return None
