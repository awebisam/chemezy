import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.v1.endpoints.chemicals import get_chemical_service
from app.main import app
from app.models.chemical import Chemical, StateOfMatter
from app.services.chemical_service import ChemicalService


@pytest.fixture
def mock_chemical_service():
    """Provides a mock of the ChemicalService."""
    return MagicMock(spec=ChemicalService)


def override_get_chemical_service(mock_service):
    """Factory for creating a dependency override for the chemical service."""
    def _override():
        return mock_service
    return _override


@pytest.mark.asyncio
async def test_create_chemical_success(client: TestClient, auth_headers: dict, mock_chemical_service: MagicMock):
    """Test successful creation of a chemical."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)

    mock_chemical_service.create = AsyncMock(return_value=Chemical(
        id=1, molecular_formula="H2O", common_name="Water", state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0
    ))

    response = client.post(
        "/api/v1/chemicals/", headers=auth_headers, json={"molecular_formula": "H2O"})

    assert response.status_code == 201
    data = response.json()
    assert data["molecular_formula"] == "H2O"
    assert data["common_name"] == "Water"
    assert data["id"] == 1

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_chemical_conflict(client: TestClient, auth_headers: dict, mock_chemical_service: MagicMock):
    """Test creating a chemical that already exists, resulting in a 409 Conflict."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)
    mock_chemical_service.create = AsyncMock(
        side_effect=ValueError("Chemical already exists"))

    response = client.post(
        "/api/v1/chemicals/", headers=auth_headers, json={"molecular_formula": "H2O"})

    assert response.status_code == 409
    assert "Chemical already exists" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_read_chemical(client: TestClient, mock_chemical_service: MagicMock):
    """Test retrieving a single chemical by ID."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)
    mock_chemical_service.get = AsyncMock(return_value=Chemical(
        id=1, molecular_formula="H2O", common_name="Water", state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0
    ))

    response = client.get("/api/v1/chemicals/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_read_chemicals(client: TestClient, mock_chemical_service: MagicMock):
    """Test retrieving a list of all chemicals."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)
    chemicals_list = [
        Chemical(id=1, molecular_formula="H2O", common_name="Water",
                 state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0)
    ]
    mock_chemical_service.get_all = AsyncMock(return_value=(chemicals_list, 1))

    response = client.get("/api/v1/chemicals/")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["results"]) == 1
    assert data["results"][0]["common_name"] == "Water"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_chemical(client: TestClient, auth_headers: dict, mock_chemical_service: MagicMock):
    """Test deleting a chemical successfully."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)
    mock_chemical_service.delete = AsyncMock(return_value=Chemical(
        id=1, molecular_formula="H2O", common_name="Water", state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0))

    response = client.delete("/api/v1/chemicals/1", headers=auth_headers)

    assert response.status_code == 204
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_chemical_not_found(client: TestClient, auth_headers: dict, mock_chemical_service: MagicMock):
    """Test deleting a chemical that is not found."""
    app.dependency_overrides[get_chemical_service] = override_get_chemical_service(
        mock_chemical_service)
    mock_chemical_service.delete = AsyncMock(return_value=None)

    response = client.delete("/api/v1/chemicals/999", headers=auth_headers)

    assert response.status_code == 404
    app.dependency_overrides.clear()
