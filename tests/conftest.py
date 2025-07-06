import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.db.session import get_session
from app.models.user import User
from app.core.security import get_password_hash


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with database session dependency override."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    settings.testing = True # Enable testing mode
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    settings.testing = False # Disable testing mode


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(client: TestClient, test_user: User):
    """Get authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200, f"Failed to get access token: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}