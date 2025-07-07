import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlmodel import Session
from app.services.reaction_engine import ReactionEngineService
from app.models.user import User
from app.models.reaction import ReactionCache


@pytest.fixture
def reaction_engine():
    """Create a reaction engine service instance."""
    return ReactionEngineService()


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = Mock(spec=User)
    user.id = 1
    user.username = "testuser"
    return user


def test_generate_cache_key(reaction_engine):
    """Test cache key generation."""
    chemicals = ["H2O", "NaCl"]
    environment = "Earth (Normal)"
    
    key1 = reaction_engine._generate_cache_key(chemicals, environment)
    key2 = reaction_engine._generate_cache_key(chemicals, environment)
    
    # Same inputs should generate same key
    assert key1 == key2
    
    # Different order should generate same key (deterministic)
    key3 = reaction_engine._generate_cache_key(["NaCl", "H2O"], environment)
    assert key1 == key3
    
    # Different environment should generate different key
    key4 = reaction_engine._generate_cache_key(chemicals, "Vacuum")
    assert key1 != key4


def test_fallback_prediction(reaction_engine):
    """Test fallback prediction when DSPy is not available."""
    chemicals = ["H2O", "NaCl"]
    environment = "Earth (Normal)"
    
    result = reaction_engine._get_fallback_prediction(chemicals, environment)
    
    assert "products" in result
    assert "effects" in result
    assert "state_change" in result
    assert "description" in result
    
    assert isinstance(result["products"], list)
    assert isinstance(result["effects"], list)
    assert len(result["products"]) > 0


@pytest.mark.asyncio
async def test_predict_reaction_cache_hit(reaction_engine, mock_user):
    """Test reaction prediction with cache hit."""
    # Mock database session
    mock_db = Mock(spec=Session)
    
    # Mock cached result
    cached_reaction = Mock(spec=ReactionCache)
    cached_reaction.id = 1
    cached_reaction.effects = ["mixing", "temperature_change"]
    cached_reaction.products = [{"formula": "H2O", "name": "Water", "state": "liquid"}]
    cached_reaction.state_change = None
    cached_reaction.description = "Test reaction"
    
    mock_db.exec.return_value.first.return_value = cached_reaction
    
    # Mock world-first check
    with patch.object(reaction_engine, '_check_world_first_effects', return_value=False):
        result = await reaction_engine.predict_reaction(
            chemicals=["H2O", "NaCl"],
            environment="Earth (Normal)",
            user_id=mock_user.id,
            db=mock_db
        )
    
    assert result.products[0].formula == "H2O"
    assert result.effects == ["mixing", "temperature_change"]
    assert result.is_world_first == False


@pytest.mark.asyncio
async def test_predict_reaction_cache_miss(reaction_engine, mock_user):
    """Test reaction prediction with cache miss."""
    # Mock database session
    mock_db = Mock(spec=Session)
    mock_db.exec.return_value.first.return_value = None  # No cached result
    
    # Mock the prediction generation
    mock_prediction = {
        "products": [{"formula": "H2O", "name": "Water", "state": "liquid"}],
        "effects": ["mixing"],
        "state_change": None,
        "description": "Test reaction"
    }
    
    with patch.object(reaction_engine, '_generate_prediction', return_value=mock_prediction), \
         patch.object(reaction_engine, '_check_world_first_effects', return_value=True):
        
        result = await reaction_engine.predict_reaction(
            chemicals=["H2O", "NaCl"],
            environment="Earth (Normal)",
            user_id=mock_user.id,
            db=mock_db
        )
    
    assert result.products[0].formula == "H2O"
    assert result.effects == ["mixing"]
    assert result.is_world_first == True
    
    # Verify cache entry was created
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_check_world_first_effects_new_discovery(reaction_engine):
    """Test world-first effect discovery."""
    mock_db = Mock(spec=Session)
    mock_db.exec.return_value.first.return_value = None  # No existing discovery
    
    effects = ["new_effect", "another_new_effect"]
    user_id = 1
    reaction_cache_id = 1
    
    result = await reaction_engine._check_world_first_effects(
        effects, user_id, reaction_cache_id, mock_db
    )
    
    assert result == True
    assert mock_db.add.call_count == 2  # Two new discoveries
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_check_world_first_effects_existing_discovery(reaction_engine):
    """Test effect that's already been discovered."""
    mock_db = Mock(spec=Session)
    
    # Mock existing discovery
    existing_discovery = Mock()
    mock_db.exec.return_value.first.return_value = existing_discovery
    
    effects = ["existing_effect"]
    user_id = 1
    reaction_cache_id = 1
    
    result = await reaction_engine._check_world_first_effects(
        effects, user_id, reaction_cache_id, mock_db
    )
    
    assert result == False
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_called()