import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlmodel import Session
from app.services.reaction_service import ReactionService
from app.models.user import User
from app.models.reaction import ReactionCache
from app.schemas.reaction import ReactionPrediction, ReactionRequest, ReactantInput, ProductOutputDSPy
from app.schemas.environment import Environment


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def reaction_engine_with_predictor():
    with patch("app.core.dspy_manager.is_dspy_configured", return_value=True),             patch("app.services.reaction_service.ReactionPredictionModule") as MockPredictor:

        mock_predictor_instance = MagicMock()
        MockPredictor.return_value = mock_predictor_instance

        service = ReactionService(db=MagicMock()) # Pass a mock db session
        yield service, mock_predictor_instance



@pytest.fixture
def reaction_engine_no_predictor():
    with patch("app.core.dspy_manager.is_dspy_configured", return_value=False):
        service = ReactionService(db=MagicMock())
        yield service, None


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = Mock(spec=User)
    user.id = 1
    user.username = "testuser"
    return user


def test_generate_cache_key():
    """Test cache key generation using a service instance that doesn't need a predictor."""
    service = ReactionService(db=MagicMock())
    chemicals = ["H2O", "NaCl"]
    environment = "Earth (Normal)"

    key1 = service._generate_cache_key(chemicals, environment)
    key2 = service._generate_cache_key(chemicals, environment)

    assert key1 == key2

    key3 = service._generate_cache_key(
        ["NaCl", "H2O"], environment)
    assert key1 == key3

    key4 = service._generate_cache_key(chemicals, "Vacuum")
    assert key1 != key4


@pytest.mark.asyncio
async def test_predict_reaction_cache_hit(mock_db, mock_user):
    """Test reaction prediction with a cache hit, no predictor needed."""
    service = ReactionService(db=mock_db)

    cached_reaction = Mock(spec=ReactionCache)
    cached_reaction.id = 1
    cached_reaction.effects = ["mixing", "temperature_change"]
    cached_reaction.products = [
        {"molecular_formula": "H2O", "quantity": 1.0}]
    cached_reaction.state_of_product = "liquid"
    cached_reaction.explanation = "Water formed."

    mock_db.exec.return_value.first.return_value = cached_reaction

    # Mock the internal _check_and_log_discoveries method
    with patch.object(service, '_check_and_log_discoveries', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False  # Not a world first

        request = ReactionRequest(reactants=[ReactantInput(chemical_id=1, quantity=1.0)], environment=Environment.NORMAL)
        result = await service.predict_reaction(request=request, user_id=mock_user.id)

    assert result.products[0].molecular_formula == "H2O"
    assert result.effects == ["mixing", "temperature_change"]
    assert result.state_of_product == "liquid"
    assert result.explanation == "Water formed."
    assert not result.is_world_first
    mock_check.assert_awaited_once_with(
        cached_reaction.effects, mock_user.id, cached_reaction.id, mock_db)


@pytest.mark.asyncio
async def test_predict_reaction_cache_miss_with_predictor(reaction_engine_with_predictor, mock_user, mock_db):
    """Test reaction prediction with a cache miss and a working DSPy predictor."""
    service, mock_predictor = reaction_engine_with_predictor
    mock_db.exec.return_value.first.return_value = None  # No cached result

    # Mock the internal _get_reactants_from_db and _serialize_reactants methods
    with patch.object(service, '_get_reactants_from_db', return_value=[Mock(molecular_formula="H2O", id=1)]), \
         patch.object(service, '_serialize_reactants', return_value='[{"molecular_formula": "H2O", "quantity": 1.0}]'):

        mock_prediction_output = ReactionPredictionDSPyOutput(
            products=[
                ProductOutputDSPy(molecular_formula="NaOH", quantity=1.0)],
            effects=["fizzing"],
            state_of_product="aqueous solution",
            explanation="Sodium hydroxide formed from reaction."
        )
        mock_prediction = MagicMock()
        mock_prediction.prediction = mock_prediction_output
        mock_predictor.return_value = mock_prediction

        # Mock the internal _check_and_log_discoveries method
        with patch.object(service, '_check_and_log_discoveries', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True  # Is a world first

            request = ReactionRequest(reactants=[ReactantInput(chemical_id=1, quantity=1.0)], environment=Environment.NORMAL)
            result = await service.predict_reaction(request=request, user_id=mock_user.id)

            assert result.products[0].molecular_formula == "NaOH"
            assert result.effects == ["fizzing"]
            assert result.state_of_product == "aqueous solution"
            assert result.explanation == "Sodium hydroxide formed from reaction."
            assert result.is_world_first

            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

            # Check that the discovery was logged with the effects from the prediction
            mock_check.assert_awaited_once()


@pytest.mark.asyncio
async def test_predict_reaction_cache_miss_no_predictor(mock_user, mock_db):
    """Test reaction prediction with a cache miss and NO DSPy predictor (fallback case)."""
    service = ReactionService(db=mock_db)
    mock_db.exec.return_value.first.return_value = None  # No cached result

    # Mock the internal _get_reactants_from_db and _serialize_reactants methods
    with patch.object(service, '_get_reactants_from_db', return_value=[Mock(molecular_formula="H2O", id=1)]), \
         patch.object(service, '_serialize_reactants', return_value='[{"molecular_formula": "H2O", "quantity": 1.0}]'):

        request = ReactionRequest(reactants=[ReactantInput(chemical_id=1, quantity=1.0)], environment=Environment.NORMAL)
        result = await service.predict_reaction(request=request, user_id=mock_user.id)

        # Check that it returned the physics-based fallback
        assert result.explanation == "Fallback prediction."
        assert not result.is_world_first

        # Verify cache entry was NOT created for fallback
        mock_db.add.assert_not_called()



@pytest.mark.asyncio
async def test_check_and_log_discoveries_new(mock_db):
    """Test world-first effect discovery logging."""
    service = ReactionService(db=mock_db)
    mock_db.exec.return_value.first.return_value = None  # No existing discovery

    effects = ["new_effect", "another_new_effect"]
    user_id = 1
    reaction_cache_id = 1

    result = await service._check_and_log_discoveries(
        effects, user_id, reaction_cache_id, mock_db
    )

    assert result  # It is a world first
    assert mock_db.add.call_count == 2
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_and_log_discoveries_existing(mock_db):
    """Test effect that's already been discovered."""
    service = ReactionService(db=mock_db)

    # Mock existing discovery
    existing_discovery = Mock()
    mock_db.exec.return_value.first.return_value = existing_discovery

    effects = ["existing_effect"]
    user_id = 1
    reaction_cache_id = 1

    result = await service._check_and_log_discoveries(
        effects, user_id, reaction_cache_id, mock_db
    )

    assert not result  # Not a world first
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
