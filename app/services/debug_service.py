from sqlmodel import Session
from app.models.debug import DeletionRequest

class DebugService:
    def __init__(self, db: Session):
        self.db = db

    def create_deletion_request(self, item_type: str, item_id: int, reason: str) -> DeletionRequest:
        """Creates a new deletion request."""
        deletion_request = DeletionRequest(
            item_type=item_type,
            item_id=item_id,
            reason=reason
        )
        self.db.add(deletion_request)
        self.db.commit()
        self.db.refresh(deletion_request)
        return deletion_request
