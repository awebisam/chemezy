from sqlmodel import Session
from typing import Optional, TYPE_CHECKING
import logging
from app.models.debug import DeletionRequest

if TYPE_CHECKING:
    from app.services.award_service import AwardService

logger = logging.getLogger(__name__)

class DebugService:
    def __init__(self, db: Session, award_service: Optional["AwardService"] = None):
        self.db = db
        self.award_service = award_service

    async def create_deletion_request(
        self, 
        item_type: str, 
        item_id: int, 
        reason: str, 
        user_id: Optional[int] = None
    ) -> DeletionRequest:
        """Creates a new deletion request and evaluates debug contribution awards."""
        deletion_request = DeletionRequest(
            item_type=item_type,
            item_id=item_id,
            reason=reason,
            user_id=user_id
        )
        self.db.add(deletion_request)
        self.db.commit()
        self.db.refresh(deletion_request)
        
        # Evaluate debug contribution awards if user_id is provided and award service is available
        if user_id and self.award_service:
            try:
                contribution_type = f"{item_type}_correction"
                context = {
                    "deletion_request_id": deletion_request.id,
                    "item_type": item_type,
                    "item_id": item_id
                }
                
                await self.award_service.evaluate_debug_contribution_awards(
                    user_id=user_id,
                    contribution_type=contribution_type,
                    context=context
                )
                logger.info(f"Debug contribution awards evaluated for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to evaluate debug contribution awards for user {user_id}: {e}")
                # Don't fail the deletion request if award evaluation fails
        
        return deletion_request

    def mark_deletion_request_completed(self, request_id: int, user_id: Optional[int] = None) -> Optional[DeletionRequest]:
        """Mark a deletion request as completed and evaluate awards for accuracy tracking."""
        deletion_request = self.db.get(DeletionRequest, request_id)
        if not deletion_request:
            return None
            
        deletion_request.status = "completed"
        self.db.add(deletion_request)
        self.db.commit()
        self.db.refresh(deletion_request)
        
        # Re-evaluate awards when request is completed (for accuracy tracking)
        if user_id and self.award_service:
            try:
                contribution_type = f"{deletion_request.item_type}_correction_completed"
                context = {
                    "deletion_request_id": deletion_request.id,
                    "item_type": deletion_request.item_type,
                    "item_id": deletion_request.item_id,
                    "status": "completed"
                }
                
                # Use asyncio to run the async method
                import asyncio
                asyncio.create_task(
                    self.award_service.evaluate_debug_contribution_awards(
                        user_id=user_id,
                        contribution_type=contribution_type,
                        context=context
                    )
                )
                logger.info(f"Debug contribution completion awards evaluated for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to evaluate debug contribution completion awards for user {user_id}: {e}")
        
        return deletion_request

    def mark_deletion_request_rejected(self, request_id: int, user_id: Optional[int] = None) -> Optional[DeletionRequest]:
        """Mark a deletion request as rejected (for accuracy tracking)."""
        deletion_request = self.db.get(DeletionRequest, request_id)
        if not deletion_request:
            return None
            
        deletion_request.status = "rejected"
        self.db.add(deletion_request)
        self.db.commit()
        self.db.refresh(deletion_request)
        
        return deletion_request
