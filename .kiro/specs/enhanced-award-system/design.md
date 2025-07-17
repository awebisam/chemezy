# Enhanced Award System Design

## Overview

The Enhanced Award System extends Chemezy's discovery mechanics by implementing a comprehensive achievement and recognition framework. The system rewards players for chemical discoveries, database contributions through debug endpoints, and community participation. It features both predefined awards and a dynamic meta-award system for administrative flexibility.

## Architecture

### Core Components

1. **Award Engine**: Central service managing award logic and evaluation
2. **Award Templates**: Configurable award definitions with criteria and metadata
3. **Award Instances**: Individual awards granted to users
4. **Leaderboard Service**: Rankings and community features
5. **Integration Layer**: Hooks into existing reaction and debug systems

### Data Flow

```
User Action → Event Detection → Award Evaluation → Award Granting → Notification
     ↓              ↓                ↓               ↓             ↓
Reaction/Debug → Service Layer → Award Engine → Database → User Dashboard
```

## Components and Interfaces

### Database Models

#### AwardTemplate
```python
class AwardTemplate(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    name: str = Field(max_length=100, unique=True)
    description: str = Field(max_length=500)
    category: AwardCategory
    criteria: Dict[str, Any] = Field(sa_column=Column(JSON))
    metadata: Dict[str, Any] = Field(sa_column=Column(JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(foreign_key="user.id")
```

#### UserAward
```python
class UserAward(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    template_id: int = Field(foreign_key="awardtemplate.id")
    tier: int = Field(default=1)
    progress: Dict[str, Any] = Field(sa_column=Column(JSON))
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    related_entity_type: Optional[str] = Field(max_length=50)
    related_entity_id: Optional[int]
```

#### AwardCategory
```python
class AwardCategory(str, enum.Enum):
    DISCOVERY = "discovery"
    DATABASE_CONTRIBUTION = "database_contribution"
    COMMUNITY = "community"
    SPECIAL = "special"
    ACHIEVEMENT = "achievement"
```

### Service Layer

#### AwardService
```python
class AwardService:
    def __init__(self, db: Session):
        self.db = db
        self.evaluator = AwardEvaluator(db)
    
    async def evaluate_discovery_awards(self, user_id: int, reaction_cache_id: int)
    async def evaluate_debug_contribution_awards(self, user_id: int, contribution_type: str)
    async def grant_award(self, user_id: int, template_id: int, context: Dict)
    async def get_user_awards(self, user_id: int) -> List[UserAward]
    async def get_leaderboard(self, category: AwardCategory) -> List[Dict]
```

#### AwardEvaluator
```python
class AwardEvaluator:
    def __init__(self, db: Session):
        self.db = db
    
    async def check_criteria(self, template: AwardTemplate, user_id: int, context: Dict) -> bool
    async def calculate_progress(self, template: AwardTemplate, user_id: int) -> Dict
    async def determine_tier(self, template: AwardTemplate, user_stats: Dict) -> int
```

### API Endpoints

#### Awards Management
- `GET /api/v1/awards/me` - Get current user's awards
- `GET /api/v1/awards/available` - Get available awards with progress
- `GET /api/v1/awards/leaderboard/{category}` - Get category leaderboard
- `GET /api/v1/awards/user/{user_id}` - Get public user awards (if enabled)

#### Admin Endpoints
- `POST /api/v1/admin/awards/templates` - Create award template
- `PUT /api/v1/admin/awards/templates/{id}` - Update award template
- `DELETE /api/v1/admin/awards/templates/{id}` - Deactivate award template
- `POST /api/v1/admin/awards/grant` - Manually grant award
- `DELETE /api/v1/admin/awards/{award_id}` - Revoke award

## Data Models

### Award Template Structure
```json
{
  "name": "First Discovery",
  "description": "Awarded for your first chemical discovery",
  "category": "discovery",
  "criteria": {
    "type": "discovery_count",
    "threshold": 1,
    "conditions": []
  },
  "metadata": {
    "icon": "🔬",
    "rarity": "common",
    "points": 10,
    "tiers": [
      {"name": "Bronze", "threshold": 1, "points": 10},
      {"name": "Silver", "threshold": 5, "points": 50},
      {"name": "Gold", "threshold": 25, "points": 250}
    ]
  }
}
```

### Award Criteria Types
1. **Discovery Awards**
   - `discovery_count`: Number of world-first reactions
   - `unique_effects`: Number of unique effects discovered
   - `reaction_complexity`: Based on number of reactants/products

2. **Database Contribution Awards**
   - `debug_submissions`: Number of debug endpoint uses
   - `correction_accuracy`: Percentage of valid corrections
   - `data_quality_impact`: Measured improvement in data quality

3. **Community Awards**
   - `profile_completeness`: User profile information filled
   - `consecutive_days`: Daily activity streaks
   - `help_others`: Community interaction metrics

### Integration Points

#### Reaction Service Integration
```python
# In ReactionService.predict_reaction()
async def predict_reaction(self, request: ReactionRequest, user_id: int):
    # ... existing logic ...
    
    # Check for world-first discovery
    if result.is_world_first:
        await self.award_service.evaluate_discovery_awards(
            user_id=user_id,
            reaction_cache_id=cached_reaction.id
        )
    
    return result
```

#### Debug Service Integration
```python
# In DebugService
async def create_deletion_request(self, item_type: str, item_id: int, reason: str, user_id: int):
    # ... existing logic ...
    
    # Evaluate debug contribution awards
    await self.award_service.evaluate_debug_contribution_awards(
        user_id=user_id,
        contribution_type=f"{item_type}_correction"
    )
    
    return deletion_request
```

## Error Handling

### Award System Failures
- **Graceful Degradation**: Core functionality continues if award system fails
- **Retry Mechanism**: Failed award evaluations are queued for retry
- **Audit Logging**: All award actions are logged for debugging and disputes
- **Rollback Support**: Awards can be revoked if granted in error

### Data Integrity
- **Foreign Key Constraints**: Ensure referential integrity
- **Duplicate Prevention**: Prevent duplicate awards for same achievement
- **Validation**: Strict validation of award criteria and metadata

## Testing Framework
All tasks use the curl-based testing framework with automatic database reset:
- Database is automatically deleted and recreated with fresh migrations before each test run
- Use `./scripts/run_tests.sh` for robust testing with clean state
- Use `./scripts/run_tests.sh --skip-db-reset` for faster iteration during development
- No manual database reset steps required in individual tasks


### Test Data
```python
# Example test scenarios
test_scenarios = [
    {
        "name": "First Discovery Award",
        "setup": "User with no previous discoveries",
        "action": "Trigger world-first reaction",
        "expected": "Grant 'First Discovery' award"
    },
    {
        "name": "Debug Contribution Tier Upgrade",
        "setup": "User with 4 valid debug submissions",
        "action": "Submit 5th valid correction",
        "expected": "Upgrade to Silver tier"
    },
    {
        "name": "Meta Award Creation",
        "setup": "Admin creates new award template",
        "action": "User meets new criteria",
        "expected": "Automatically grant new award type"
    }
]
```

### Monitoring and Analytics
- **Award Distribution Metrics**: Track award frequency and balance
- **User Engagement**: Monitor how awards affect user behavior
- **System Performance**: Track impact on response times
- **Abuse Detection**: Monitor for award farming or exploitation