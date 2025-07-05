from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Schema for token data payload."""
    username: Optional[str] = None