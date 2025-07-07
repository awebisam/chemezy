from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(settings.database_url)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session