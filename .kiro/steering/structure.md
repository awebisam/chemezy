# Chemezy Backend Project Structure

## Architecture Pattern
The project follows a **layered service architecture** with clear separation of concerns:
- **API Layer**: FastAPI endpoints with request/response handling
- **Service Layer**: Business logic and orchestration
- **Model Layer**: Database entities and schemas
- **Core Layer**: Configuration, security, and shared utilities

## Directory Organization

### `/app` - Main Application Code
```
app/
├── main.py                 # FastAPI application entry point
├── api/v1/                 # API endpoints (versioned)
│   ├── api.py             # Router aggregation
│   └── endpoints/         # Individual endpoint modules
├── core/                  # Core configuration and utilities
│   ├── config.py          # Settings and environment variables
│   ├── security.py        # Authentication utilities
│   └── dspy_manager.py    # AI/LLM configuration
├── models/                # SQLModel database entities
├── schemas/               # Pydantic request/response schemas
├── services/              # Business logic layer
└── db/                    # Database configuration
```

### `/tests` - Testing Suite
```
tests/
├── api/                   # API endpoint tests (bash/curl)
├── services/              # Service layer tests
├── integration/           # End-to-end tests
└── helpers/               # Test utilities and fixtures
```

### `/alembic` - Database Migrations
```
alembic/
├── versions/              # Migration files
├── env.py                # Migration environment
└── script.py.mako       # Migration template
```

## Naming Conventions

### Files and Modules
- **Snake_case** for Python files: `award_service.py`
- **Descriptive names** indicating purpose: `leaderboard_service.py`
- **Plural for collections**: `endpoints/`, `models/`, `services/`

### API Endpoints
- **RESTful patterns**: `/api/v1/awards/me`, `/api/v1/reactions/react`
- **Versioned URLs**: Always include `/v1/` for future compatibility
- **Resource-based**: Group by domain entity (awards, reactions, users)

### Database Models
- **Singular names**: `User`, `Award`, `AwardTemplate`
- **Clear relationships**: `UserAward` for junction tables
- **Descriptive fields**: `granted_at`, `template_id`, `is_active`

### Services
- **Domain-focused**: `AwardService`, `ReactionService`, `LeaderboardService`
- **Single responsibility**: Each service handles one domain area
- **Dependency injection**: Services receive database session in constructor

## Code Organization Patterns

### Service Layer Structure
```python
class AwardService:
    def __init__(self, db: Session):
        self.db = db
        self.evaluator = AwardEvaluator(db)
    
    async def evaluate_discovery_awards(self, user_id: int, context: Dict) -> List[UserAward]:
        # Business logic here
        pass
```

### API Endpoint Structure
```python
@router.get("/endpoint", response_model=ResponseSchema)
async def endpoint_function(
    query_param: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    # Endpoint logic here
    pass
```

### Error Handling
- **Custom exceptions** per service: `AwardServiceError`, `ReactionServiceError`
- **HTTP exception mapping** in API layer
- **Structured error responses** with consistent format

## Import Conventions
- **Absolute imports** from app root: `from app.services.award_service import AwardService`
- **Group imports**: Standard library, third-party, local imports
- **Specific imports**: Import only what's needed, avoid `import *`

## Configuration Management
- **Environment-based**: All config via `.env` file and `Settings` class
- **Type-safe**: Use Pydantic for configuration validation
- **Defaults for development**: Sensible defaults where security allows
- **Required for production**: No defaults for sensitive values like `SECRET_KEY`