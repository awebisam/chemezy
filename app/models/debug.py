from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class DeletionRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    item_type: str
    item_id: int
    reason: str
    status: str = Field(default="pending")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
