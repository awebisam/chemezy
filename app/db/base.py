from sqlmodel import SQLModel

# Import all models here to ensure they are registered with SQLModel
from app.models.user import User  # noqa
from app.models.reaction import ReactionCache, Discovery  # noqa
from app.models.chemical import Chemical  # noqa
from app.models.debug import DeletionRequest  # noqa
from app.models.award import AwardTemplate, UserAward  # noqa

__all__ = ["SQLModel"]
