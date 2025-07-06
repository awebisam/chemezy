import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session
from app.models.chemical import Chemical, StateOfMatter
from app.schemas.chemical import ChemicalCreate
from app.services.chemical_service import ChemicalService


@pytest.fixture
def mock_db():
    """Provides a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def chemical_service_with_generator():
    """
    Provides an instance of ChemicalService with a mocked generator.
    Patches `is_dspy_configured` to return True.
    """
    with patch("app.services.chemical_service.is_dspy_configured", return_value=True), \
            patch("app.services.chemical_service.ChemicalPropertyGenerator") as MockGenerator:

        mock_generator_instance = MagicMock()
        MockGenerator.return_value = mock_generator_instance

        service = ChemicalService()
        yield service, mock_generator_instance


@pytest.mark.asyncio
async def test_create_chemical_success(chemical_service_with_generator, mock_db):
    """Test successful creation of a new chemical."""
    service, mock_generator = chemical_service_with_generator

    # Arrange
    molecular_formula = "H2O"
    chemical_in = ChemicalCreate(molecular_formula=molecular_formula)

    mock_db.exec.return_value.first.return_value = None  # No existing chemical

    # Mock the return value of the generator call
    mock_prediction = MagicMock()
    mock_prediction.common_name = "Water"
    mock_prediction.state_of_matter = StateOfMatter.LIQUID
    mock_prediction.color = "Transparent"
    mock_prediction.density = 1.0
    mock_prediction.properties = {"melting_point": 0, "boiling_point": 100}
    mock_generator.return_value = mock_prediction

    # Act
    created_chemical = await service.create(db=mock_db, chemical_in=chemical_in)

    # Assert
    assert created_chemical.molecular_formula == molecular_formula
    assert created_chemical.common_name == "Water"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(created_chemical)


@pytest.mark.asyncio
async def test_create_chemical_already_exists(mock_db):
    """Test creating a chemical that already exists."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()
        existing_chemical = Chemical(molecular_formula="H2O", common_name="Water",
                                     state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0)
        mock_db.exec.return_value.first.return_value = existing_chemical

        with pytest.raises(ValueError, match="Chemical with formula H2O already exists."):
            await service.create(db=mock_db, chemical_in=ChemicalCreate(molecular_formula="H2O"))


@pytest.mark.asyncio
async def test_create_chemical_llm_fails(chemical_service_with_generator, mock_db):
    """Test error handling when the LLM property generation fails."""
    service, mock_generator = chemical_service_with_generator
    mock_db.exec.return_value.first.return_value = None
    mock_generator.side_effect = Exception("LLM is down")

    with pytest.raises(RuntimeError, match="Failed to generate properties from LLM."):
        await service.create(db=mock_db, chemical_in=ChemicalCreate(molecular_formula="H2O"))


@pytest.mark.asyncio
async def test_create_chemical_dspy_not_configured(mock_db):
    """Test that creating a chemical fails if DSPy is not configured."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()
        mock_db.exec.return_value.first.return_value = None

        with pytest.raises(RuntimeError, match="Chemical property generator is not configured."):
            await service.create(db=mock_db, chemical_in=ChemicalCreate(molecular_formula="H2O"))


@pytest.mark.asyncio
async def test_get_chemical(mock_db):
    """Test retrieving a single chemical by ID."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()
        expected_chemical = Chemical(id=1, molecular_formula="NaCl", common_name="Salt",
                                     state_of_matter=StateOfMatter.SOLID, color="White", density=2.17)
        mock_db.get.return_value = expected_chemical

        chemical = await service.get(db=mock_db, chemical_id=1)

        assert chemical == expected_chemical
        mock_db.get.assert_called_once_with(Chemical, 1)


@pytest.mark.asyncio
async def test_get_all_chemicals(mock_db):
    """Test retrieving a paginated list of all chemicals."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()
        chemicals_list = [
            Chemical(id=1, molecular_formula="H2O", common_name="Water",
                     state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0),
            Chemical(id=2, molecular_formula="NaCl", common_name="Salt",
                     state_of_matter=StateOfMatter.SOLID, color="White", density=2.17)
        ]

        # Mock the two separate exec calls
        mock_db.exec.side_effect = [
            # For the main query
            MagicMock(all=MagicMock(return_value=chemicals_list)),
            MagicMock(one=MagicMock(return_value=2))  # For the count query
        ]

        results, total = await service.get_all(db=mock_db, skip=0, limit=100)

        assert total == 2
        assert len(results) == 2
        assert results[0].common_name == "Water"


@pytest.mark.asyncio
async def test_delete_chemical(mock_db):
    """Test successfully deleting a chemical."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()
        chemical_to_delete = Chemical(id=1, molecular_formula="H2O", common_name="Water",
                                      state_of_matter=StateOfMatter.LIQUID, color="Transparent", density=1.0)

        # We need to mock the async get method within the service
        with patch.object(service, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = chemical_to_delete

            deleted_chemical = await service.delete(db=mock_db, chemical_id=1)

            mock_get.assert_awaited_once_with(mock_db, 1)
            mock_db.delete.assert_called_once_with(chemical_to_delete)
            mock_db.commit.assert_called_once()
            assert deleted_chemical == chemical_to_delete


@pytest.mark.asyncio
async def test_delete_chemical_not_found(mock_db):
    """Test attempting to delete a chemical that does not exist."""
    with patch("app.services.chemical_service.is_dspy_configured", return_value=False):
        service = ChemicalService()

        with patch.object(service, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            result = await service.delete(db=mock_db, chemical_id=999)

            mock_get.assert_awaited_once_with(mock_db, 999)
            mock_db.delete.assert_not_called()
            mock_db.commit.assert_not_called()
            assert result is None
