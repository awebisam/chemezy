from sqlmodel import SQLModel

# Import all models here to ensure they are registered with SQLModel
from app.models.user import User  # noqa
from app.models.reaction import ReactionCache, Discovery  # noqa

__all__ = ["SQLModel"]