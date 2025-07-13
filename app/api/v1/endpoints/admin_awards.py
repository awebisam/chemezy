"""
Admin award management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import Optional, List

from app.api.v1.endpoints.users import get_current_admin_user
from app.db.session import get_session
from app.models.user import User
from app.models.award import AwardCategory, AwardTemplate, UserAward
from app.services.award_service import AwardService, AwardServiceError
from app.services.award_template_service import AwardTemplateService, AwardTemplateValidationError
from app.schemas.award import (
    AwardTemplateSchema,
    CreateAwardTemplateSchema,
    UpdateAwardTemplateSchema,
    ManualAwardGrantSchema,
    AwardRevocationSchema,
    UserAwardSchema
)

router = APIRouter()


@router.post("/templates", response_model=AwardTemplateSchema)
async def create_award_template(
    template_data: CreateAwardTemplateSchema,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Create a new award template.
    
    Only admin users can create award templates.
    """
    try:
        template_service = AwardTemplateService(db)
        template = await template_service.create_template(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            criteria=template_data.criteria,
            metadata=template_data.metadata,
            created_by=admin_user.id
        )
        
        return AwardTemplateSchema.from_orm(template)
        
    except AwardTemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create award template: {str(e)}"
        )


@router.get("/templates", response_model=List[AwardTemplateSchema])
async def get_award_templates(
    category: Optional[AwardCategory] = Query(None, description="Filter by category"),
    active_only: bool = Query(True, description="Show only active templates"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get all award templates with optional filtering.
    
    Only admin users can view all award templates.
    """
    try:
        template_service = AwardTemplateService(db)
        templates = await template_service.get_templates(
            category=category,
            active_only=active_only,
            skip=skip,
            limit=limit
        )
        
        return [AwardTemplateSchema.from_orm(template) for template in templates]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve award templates: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=AwardTemplateSchema)
async def get_award_template(
    template_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Get a specific award template by ID.
    
    Only admin users can view award template details.
    """
    try:
        template_service = AwardTemplateService(db)
        template = await template_service.get_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Award template not found"
            )
        
        return AwardTemplateSchema.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve award template: {str(e)}"
        )


@router.put("/templates/{template_id}", response_model=AwardTemplateSchema)
async def update_award_template(
    template_id: int,
    template_data: UpdateAwardTemplateSchema,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing award template.
    
    Only admin users can update award templates.
    """
    try:
        template_service = AwardTemplateService(db)
        template = await template_service.update_template(
            template_id=template_id,
            name=template_data.name,
            description=template_data.description,
            criteria=template_data.criteria,
            metadata=template_data.metadata
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Award template not found"
            )
        
        return AwardTemplateSchema.from_orm(template)
        
    except HTTPException:
        raise
    except AwardTemplateValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update award template: {str(e)}"
        )


@router.post("/templates/{template_id}/activate", response_model=AwardTemplateSchema)
async def activate_award_template(
    template_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Activate an award template.
    
    Only admin users can activate award templates.
    """
    try:
        template_service = AwardTemplateService(db)
        template = await template_service.activate_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Award template not found"
            )
        
        return AwardTemplateSchema.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate award template: {str(e)}"
        )


@router.post("/templates/{template_id}/deactivate", response_model=AwardTemplateSchema)
async def deactivate_award_template(
    template_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Deactivate an award template.
    
    Only admin users can deactivate award templates.
    """
    try:
        template_service = AwardTemplateService(db)
        template = await template_service.deactivate_template(template_id)
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Award template not found"
            )
        
        return AwardTemplateSchema.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate award template: {str(e)}"
        )


@router.post("/awards/grant", response_model=UserAwardSchema)
async def grant_manual_award(
    award_data: ManualAwardGrantSchema,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Manually grant an award to a user.
    
    Only admin users can manually grant awards.
    """
    try:
        award_service = AwardService(db)
        award = await award_service.grant_manual_award(
            user_id=award_data.user_id,
            template_id=award_data.template_id,
            tier=award_data.tier,
            reason=award_data.reason,
            granted_by=admin_user.id,
            related_entity_type=award_data.related_entity_type,
            related_entity_id=award_data.related_entity_id
        )
        
        # Get full award data for response
        award_data_full = await award_service.get_user_awards(
            user_id=award_data.user_id,
            skip=0,
            limit=1
        )
        
        if not award_data_full:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Award granted but could not retrieve full data"
            )
        
        # Convert to response schema
        award_info = award_data_full[0]
        template_schema = {
            "id": award_info["template_id"],
            "name": award_info["template"]["name"],
            "description": award_info["template"]["description"],
            "category": award_info["template"]["category"],
            "metadata": award_info["template"]["metadata"]
        }
        
        award_schema = UserAwardSchema(
            id=award_info["id"],
            user_id=award_info["user_id"],
            template_id=award_info["template_id"],
            tier=award_info["tier"],
            progress=award_info["progress"],
            granted_at=award_info["granted_at"],
            related_entity_type=award_info["related_entity_type"],
            related_entity_id=award_info["related_entity_id"],
            template=template_schema
        )
        
        return award_schema
        
    except AwardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant manual award: {str(e)}"
        )


@router.post("/awards/revoke")
async def revoke_award(
    revocation_data: AwardRevocationSchema,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_session)
):
    """
    Revoke an award from a user.
    
    Only admin users can revoke awards.
    """
    try:
        award_service = AwardService(db)
        success = await award_service.revoke_award(
            award_id=revocation_data.award_id,
            reason=revocation_data.reason,
            revoked_by=admin_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Award not found"
            )
        
        return {
            "message": "Award revoked successfully",
            "award_id": revocation_data.award_id,
            "reason": revocation_data.reason,
            "revoked_by": admin_user.id
        }
        
    except HTTPException:
        raise
    except AwardServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke award: {str(e)}"
        )