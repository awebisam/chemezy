import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlmodel import Session
from app.services.reaction_engine import ReactionEngineService
from app.models.user import User
from app.models.reaction import ReactionCache
from app.schemas.reaction import ReactionPredictionOutput


@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)


@pytest.fixture
def reaction_engine_with_predictor():
    with patch("app.services.reaction_engine.is_dspy_configured", return_value=True), \
            patch("app.services.reaction_engine.RAGReactionPredictor") as MockPredictor, \
            patch("app.services.reaction_engine.PubChemService"):

        mock_predictor_instance = MagicMock()
        MockPredictor.return_value = mock_predictor_instance

        service = ReactionEngineService()
        yield service, mock_predictor_instance


@pytest.fixture
def reaction_engine_no_predictor():
    with patch("app.services.reaction_engine.is_dspy_configured", return_value=False), \
            patch("app.services.reaction_engine.PubChemService"):
        service = ReactionEngineService()
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
    with patch("app.services.reaction_engine.is_dspy_configured", return_value=False), \
            patch("app.services.reaction_engine.PubChemService"):
        reaction_engine = ReactionEngineService()
        chemicals = ["H2O", "NaCl"]
        environment = "Earth (Normal)"

        key1 = reaction_engine._generate_cache_key(chemicals, environment)
        key2 = reaction_engine._generate_cache_key(chemicals, environment)

        assert key1 == key2

        key3 = reaction_engine._generate_cache_key(
            ["NaCl", "H2O"], environment)
        assert key1 == key3

        key4 = reaction_engine._generate_cache_key(chemicals, "Vacuum")
        assert key1 != key4


@pytest.mark.asyncio
async def test_predict_reaction_cache_hit(reaction_engine_no_predictor, mock_user, mock_db):
    """Test reaction prediction with a cache hit, no predictor needed."""
    reaction_engine, _ = reaction_engine_no_predictor

    cached_reaction = Mock(spec=ReactionCache)
    cached_reaction.id = 1
    cached_reaction.effects = ["mixing", "temperature_change"]
    cached_reaction.products = [
        {"formula": "H2O", "name": "Water", "state": "liquid"}]
    cached_reaction.state_change = None
    cached_reaction.description = "Test reaction"

    mock_db.exec.return_value.first.return_value = cached_reaction

    # Mock world-first check, which is now _check_and_log_discoveries
    with patch.object(reaction_engine, '_check_and_log_discoveries', new_callable=AsyncMock) as mock_check:
        mock_check.return_value = False  # Not a world first
        result = await reaction_engine.predict_reaction(
            chemicals=["H2O", "NaCl"],
            environment="Earth (Normal)",
            user_id=mock_user.id,
            db=mock_db
        )

    assert result.products[0].formula == "H2O"
    assert result.effects == ["mixing", "temperature_change"]
    assert not result.is_world_first
    mock_check.assert_awaited_once_with(
        cached_reaction.effects, mock_user.id, cached_reaction.id, mock_db)


@pytest.mark.asyncio
async def test_predict_reaction_cache_miss_with_predictor(reaction_engine_with_predictor, mock_user, mock_db):
    """Test reaction prediction with a cache miss and a working DSPy predictor."""
    reaction_engine, mock_predictor = reaction_engine_with_predictor
    mock_db.exec.return_value.first.return_value = None  # No cached result

    # Mock the context fetching and prediction generation
    with patch.object(reaction_engine, '_get_chemical_context_with_retries', new_callable=AsyncMock) as mock_get_context:
        mock_get_context.return_value = {"H2O": {}, "NaCl": {}}

        mock_prediction_output = ReactionPredictionOutput(
            products=[
                {"formula": "NaOH", "name": "Sodium Hydroxide", "state": "aqueous"}],
            effects=["fizzing"],
            state_change=None,
            description="A predicted reaction."
        )
        mock_prediction = MagicMock()
        mock_prediction.reaction_prediction = mock_prediction_output
        mock_predictor.return_value = mock_prediction

        with patch.object(reaction_engine, '_check_and_log_discoveries', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = True  # Is a world first

            result = await reaction_engine.predict_reaction(
                chemicals=["H2O", "NaCl"],
                environment="Earth (Normal)",
                user_id=mock_user.id,
                db=mock_db
            )

            assert result.products[0].formula == "NaOH"
            assert result.effects == ["fizzing"]
            assert result.is_world_first

            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()

            # Check that the discovery was logged with the effects from the prediction
            mock_check.assert_awaited_once_with(
                mock_prediction_output.effects, mock_user.id, mock_db.add.call_args[0][0].id, mock_db)


@pytest.mark.asyncio
async def test_predict_reaction_cache_miss_no_predictor(reaction_engine_no_predictor, mock_user, mock_db):
    """Test reaction prediction with a cache miss and NO DSPy predictor (fallback case)."""
    reaction_engine, _ = reaction_engine_no_predictor
    mock_db.exec.return_value.first.return_value = None  # No cached result

    with patch.object(reaction_engine, '_get_chemical_context_with_retries', new_callable=AsyncMock) as mock_get_context:
        mock_get_context.return_value = {"H2O": {}, "NaCl": {}}

        result = await reaction_engine.predict_reaction(
            chemicals=["H2O", "NaCl"],
            environment="Earth (Normal)",
            user_id=mock_user.id,
            db=mock_db
        )

        # Check that it returned the physics-based fallback
        assert result.description.startswith(
            "A fallback prediction was generated")
        assert not result.is_world_first

        # Verify cache entry was NOT created for fallback
        mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_check_and_log_discoveries_new(reaction_engine_no_predictor, mock_db):
    """Test world-first effect discovery logging."""
    reaction_engine, _ = reaction_engine_no_predictor
    mock_db.exec.return_value.first.return_value = None  # No existing discovery

    effects = ["new_effect", "another_new_effect"]
    user_id = 1
    reaction_cache_id = 1

    result = await reaction_engine._check_and_log_discoveries(
        effects, user_id, reaction_cache_id, mock_db
    )

    assert result  # It is a world first
    assert mock_db.add.call_count == 2
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_and_log_discoveries_existing(reaction_engine_no_predictor, mock_db):
    """Test effect that's already been discovered."""
    reaction_engine, _ = reaction_engine_no_predictor

    # Mock existing discovery
    existing_discovery = Mock()
    mock_db.exec.return_value.first.return_value = existing_discovery

    effects = ["existing_effect"]
    user_id = 1
    reaction_cache_id = 1

    result = await reaction_engine._check_and_log_discoveries(
        effects, user_id, reaction_cache_id, mock_db
    )

    assert not result  # Not a world first
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()
