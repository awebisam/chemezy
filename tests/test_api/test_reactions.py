import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.user import User


def test_predict_reaction_success(client: TestClient, auth_headers: dict):
    """Test successful reaction prediction."""
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O", "NaCl"],
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "request_id" in data
    assert "products" in data
    assert "effects" in data
    assert "description" in data
    assert "is_world_first" in data
    assert isinstance(data["products"], list)
    assert isinstance(data["effects"], list)


def test_predict_reaction_no_auth(client: TestClient):
    """Test reaction prediction without authentication."""
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O", "NaCl"],
            "environment": "Earth (Normal)"
        }
    )
    
    assert response.status_code == 401


def test_predict_reaction_empty_chemicals(client: TestClient, auth_headers: dict):
    """Test reaction prediction with empty chemicals list."""
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": [],
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "At least one chemical must be provided" in response.json()["detail"]


def test_get_reaction_cache(client: TestClient, auth_headers: dict):
    """Test getting reaction cache."""
    # First create a reaction
    client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O", "NaCl"],
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    # Then get cache
    response = client.get(
        "/api/v1/reactions/cache",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_user_stats(client: TestClient, auth_headers: dict):
    """Test getting user statistics."""
    response = client.get(
        "/api/v1/reactions/stats",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "user_id" in data
    assert "username" in data
    assert "total_reactions" in data
    assert "total_discoveries" in data
    assert "unique_effects_discovered" in data


def test_get_all_discoveries(client: TestClient):
    """Test getting all discoveries (public endpoint)."""
    response = client.get("/api/v1/reactions/discoveries/all")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)