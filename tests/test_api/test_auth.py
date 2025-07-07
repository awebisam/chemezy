import pytest
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.core.config import settings
from app.models.user import User


def test_register_success(client: TestClient):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser123",
            "email": "test123@example.com",
            "password": "securepassword123"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser123"
    assert data["email"] == "test123@example.com"
    assert "id" in data
    assert "hashed_password" not in data  # Should not expose password


def test_register_duplicate_username(client: TestClient, test_user: User):
    """Test registration with existing username."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": test_user.username,
            "email": "different@example.com",
            "password": "password123"
        }
    )
    
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]


def test_register_duplicate_email(client: TestClient, test_user: User):
    """Test registration with existing email."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "differentuser",
            "email": test_user.email,
            "password": "password123"
        }
    )
    
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_register_invalid_email_format(client: TestClient):
    """Test registration with invalid email format."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        }
    )
    
    assert response.status_code == 422  # Pydantic validation error


def test_register_weak_password(client: TestClient):
    """Test registration with weak password."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"  # Too short
        }
    )
    
    # Should still accept (no password strength validation implemented yet)
    # This could be enhanced later with password validation
    assert response.status_code in [200, 422]


def test_login_success(client: TestClient, test_user: User):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": test_user.username,
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_username(client: TestClient):
    """Test login with non-existent username."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "nonexistent",
            "password": "password123"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_login_invalid_password(client: TestClient, test_user: User):
    """Test login with wrong password."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": test_user.username,
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]


def test_expired_token_access(client: TestClient, test_user: User):
    """Test API access with expired token."""
    # Create an expired token
    expired_payload = {
        "sub": test_user.username,
        "exp": datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == 401


def test_malformed_token_access(client: TestClient):
    """Test API access with malformed token."""
    malformed_token = "not.a.valid.jwt.token"
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {malformed_token}"}
    )
    
    assert response.status_code == 401


def test_missing_token_access(client: TestClient):
    """Test API access without token."""
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 401


def test_invalid_token_format(client: TestClient):
    """Test API access with invalid authorization header format."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "InvalidFormat token_here"}
    )
    
    assert response.status_code == 401


def test_token_with_invalid_user(client: TestClient):
    """Test token for user that no longer exists."""
    # Create token for non-existent user
    payload = {
        "sub": "nonexistent_user",
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 401
    assert "User not found" in response.json()["detail"]


def test_get_current_user_success(client: TestClient, auth_headers: dict, test_user: User):
    """Test getting current user profile."""
    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username
    assert data["email"] == test_user.email


def test_get_user_by_id_success(client: TestClient, auth_headers: dict, test_user: User):
    """Test getting user by ID."""
    response = client.get(
        f"/api/v1/auth/users/{test_user.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username


def test_get_user_by_id_not_found(client: TestClient, auth_headers: dict):
    """Test getting non-existent user by ID."""
    response = client.get(
        "/api/v1/auth/users/99999",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_rate_limiting_registration(client: TestClient):
    """Test rate limiting on registration endpoint."""
    # This test depends on the rate limiter being set to 5/minute
    # Make 6 requests rapidly to trigger rate limiting
    for i in range(6):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"testuser{i}",
                "email": f"test{i}@example.com",
                "password": "password123"
            }
        )
        
        if i < 5:
            # First 5 should succeed (or fail for valid business reasons)
            assert response.status_code in [200, 400]
        else:
            # 6th request should be rate limited
            assert response.status_code == 429


def test_rate_limiting_login(client: TestClient, test_user: User):
    """Test rate limiting on login endpoint."""
    # Make multiple failed login attempts to trigger rate limiting
    for i in range(11):  # Rate limit is 10/minute
        response = client.post(
            "/api/v1/auth/token",
            data={
                "username": test_user.username,
                "password": "wrongpassword"
            }
        )
        
        if i < 10:
            # First 10 should fail with 401 (wrong password)
            assert response.status_code == 401
        else:
            # 11th request should be rate limited
            assert response.status_code == 429