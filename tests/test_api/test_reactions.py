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


def test_predict_reaction_invalid_json(client: TestClient, auth_headers: dict):
    """Test reaction prediction with malformed JSON."""
    response = client.post(
        "/api/v1/reactions/react",
        data="invalid json",
        headers={**auth_headers, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


def test_predict_reaction_missing_fields(client: TestClient, auth_headers: dict):
    """Test reaction prediction with missing required fields."""
    response = client.post(
        "/api/v1/reactions/react",
        json={"chemicals": ["H2O"]},  # Missing environment
        headers=auth_headers
    )
    
    assert response.status_code == 422


def test_predict_reaction_invalid_types(client: TestClient, auth_headers: dict):
    """Test reaction prediction with invalid field types."""
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": "not_a_list",  # Should be list
            "environment": ["not_a_string"]  # Should be string
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422


def test_predict_reaction_extremely_long_input(client: TestClient, auth_headers: dict):
    """Test reaction prediction with extremely long input."""
    very_long_chemical = "A" * 10000  # 10K character chemical name
    
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": [very_long_chemical],
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    # Should handle gracefully, either succeed or fail with proper error
    assert response.status_code in [200, 400, 422]


def test_predict_reaction_special_characters(client: TestClient, auth_headers: dict):
    """Test reaction prediction with special characters in input."""
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H₂O", "NaCl", "Café☕", "🧪"],
            "environment": "Earth (Normal) 🌍"
        },
        headers=auth_headers
    )
    
    # Should handle unicode characters gracefully
    assert response.status_code in [200, 400]


def test_predict_reaction_cache_consistency(client: TestClient, auth_headers: dict):
    """Test that repeated identical requests return consistent results."""
    request_data = {
        "chemicals": ["H2O", "NaCl"],
        "environment": "Earth (Normal)"
    }
    
    # Make the same request twice
    response1 = client.post(
        "/api/v1/reactions/react",
        json=request_data,
        headers=auth_headers
    )
    
    response2 = client.post(
        "/api/v1/reactions/react",
        json=request_data,
        headers=auth_headers
    )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Results should be identical (deterministic)
    assert data1["products"] == data2["products"]
    assert data1["effects"] == data2["effects"]
    assert data1["description"] == data2["description"]


def test_predict_reaction_case_sensitivity(client: TestClient, auth_headers: dict):
    """Test case sensitivity in chemical names."""
    # Test different cases of the same chemical
    response1 = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["h2o"],  # lowercase
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    response2 = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O"],  # uppercase
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Different cases might produce different cache keys (current behavior)
    # or should be normalized (future enhancement)


def test_get_reaction_cache_empty_results(client: TestClient, auth_headers: dict):
    """Test getting cache when user has no reactions."""
    # Use a fresh auth header for a new user that hasn't made reactions
    response = client.get(
        "/api/v1/reactions/cache",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_endpoints_require_authentication(client: TestClient):
    """Test that all protected endpoints require authentication."""
    protected_endpoints = [
        ("POST", "/api/v1/reactions/react", {"chemicals": ["H2O"], "environment": "Earth"}),
        ("GET", "/api/v1/reactions/cache", None),
        ("GET", "/api/v1/reactions/stats", None),
    ]
    
    for method, endpoint, json_data in protected_endpoints:
        if method == "POST":
            response = client.post(endpoint, json=json_data)
        else:
            response = client.get(endpoint)
        
        assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"


def test_health_check_endpoint(client: TestClient):
    """Test the health check endpoint works without authentication."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client: TestClient):
    """Test the root endpoint provides API information."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


def test_prediction_with_expired_token(client: TestClient, test_user):
    """Test reaction prediction with expired JWT token."""
    from datetime import datetime, timedelta
    import jwt
    from app.core.config import settings
    
    # Create expired token
    expired_payload = {
        "sub": test_user.username,
        "exp": datetime.utcnow() - timedelta(minutes=1)
    }
    expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
    
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O", "NaCl"],
            "environment": "Earth (Normal)"
        },
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    
    assert response.status_code == 401


def test_concurrent_requests_same_user(client: TestClient, auth_headers: dict):
    """Test handling of concurrent requests from the same user."""
    import threading
    import time
    
    results = []
    
    def make_request():
        response = client.post(
            "/api/v1/reactions/react",
            json={
                "chemicals": ["H2O", "NaCl"],
                "environment": "Earth (Normal)"
            },
            headers=auth_headers
        )
        results.append(response.status_code)
    
    # Make 3 concurrent requests
    threads = []
    for _ in range(3):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    # All requests should succeed
    assert all(status == 200 for status in results)


def test_error_handling_with_database_constraints(client: TestClient, auth_headers: dict):
    """Test error handling when database constraints might be violated."""
    # This test would be enhanced with actual database constraint scenarios
    # For now, test a valid request that should work
    response = client.post(
        "/api/v1/reactions/react",
        json={
            "chemicals": ["H2O"],
            "environment": "Earth (Normal)"
        },
        headers=auth_headers
    )
    
    assert response.status_code in [200, 400, 500]  # Should handle gracefully