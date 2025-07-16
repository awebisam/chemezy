# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context and Architecture

Chemezy is a gamified chemistry simulation platform that serves as "the source code of reality" for chemistry education. The backend combines AI-powered reaction prediction with real scientific data from PubChem and a comprehensive gamification system.

### Core Architecture Pattern
The project follows a **layered service architecture** with strict separation of concerns:
- **API Layer**: FastAPI endpoints with request/response handling (`app/api/v1/endpoints/`)
- **Service Layer**: Business logic and orchestration (`app/services/`)
- **Model Layer**: Database entities and schemas (`app/models/`, `app/schemas/`)
- **Core Layer**: Configuration, security, and shared utilities (`app/core/`)

### Key Design Principles
- **Deterministic Chemistry**: Same inputs always produce same outputs via intelligent caching
- **Scientific Accuracy**: All reactions grounded in PubChem data using RAG (Retrieval-Augmented Generation)
- **Structured AI**: DSPy framework for reliable, typed LLM interactions (not raw prompting)
- **Gamification Engine**: Multi-tier award system with discovery tracking and leaderboards

## Development Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Database setup with migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Reset database for development
rm chemezy.db && alembic upgrade head
```

### Testing
```bash
# Run all tests with fresh database
./scripts/run_tests.sh

# Run specific test suite
./scripts/run_tests.sh api        # API endpoint tests
./scripts/run_tests.sh services   # Service layer tests
./scripts/run_tests.sh integration # End-to-end tests

# Skip database reset for faster iteration
./scripts/run_tests.sh --skip-db-reset

# Verbose output for debugging
./scripts/run_tests.sh --verbose
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d
```

## Critical Technical Details

### Environment Configuration
All configuration via `.env` file (copy from `.env.example`):
- `SECRET_KEY`: **Required** for JWT tokens (no default for security)
- `AZURE_OPENAI_*`: AI service configuration for DSPy
- `DATABASE_URL`: Database connection string
- `PUBCHEM_*`: PubChem API configuration
- `DEBUG`: Development mode toggle

### Chemistry Engine Architecture
The core chemistry engine follows a strict **two-layer architecture**:

1. **Cache Layer**: Check `ReactionCache` table first for deterministic responses
2. **Reasoning Core**: DSPy-powered RAG system that:
   - **Retrieves** real chemical data from PubChem API
   - **Augments** LLM context with factual scientific data
   - **Generates** structured JSON responses with products and effects

### AI/LLM Integration (DSPy)
- **Never use raw LLM prompting** - all AI interactions must go through DSPy modules
- Core module: `ChemistryReasoningModule` in `app/services/dspy_extended.py`
- Signatures defined in `app/services/dspy_signatures.py`
- Structured output with type safety and retry logic

### Award System Architecture
Multi-service gamification system:
- **Award Templates**: Configurable criteria and tiers (Bronze/Silver/Gold)
- **Real-time Evaluation**: Automatic award checking on user actions
- **Discovery Tracking**: World-first reaction detection in `Discovery` table
- **Leaderboards**: Cached rankings across multiple categories
- **Progress Tracking**: User progress toward unearned awards

## Code Organization Patterns

### Service Layer Structure
```python
class ServiceName:
    def __init__(self, db: Session):
        self.db = db
        # Initialize dependencies
    
    async def method_name(self, param: Type) -> ReturnType:
        # Business logic here
```

### API Endpoint Structure
```python
@router.get("/endpoint", response_model=ResponseSchema)
async def endpoint_function(
    param: Type = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    # Call service layer, return response
```

### Database Models
- Use SQLModel for type-safe ORM with Pydantic integration
- Singular names: `User`, `Award`, `ReactionCache`
- Clear relationships: `UserAward` for junction tables
- All models inherit from `SQLModel` base class

## Testing Strategy

### Test Organization
- **API Tests**: Bash/curl scripts in `tests/api/` for HTTP endpoint validation
- **Service Tests**: Python unit tests in `tests/services/` (when present)
- **Integration Tests**: End-to-end workflows in `tests/integration/`

### Test Runner Features
- Automatic database reset with fresh migrations
- Color-coded output and detailed logging
- Suite selection and verbose modes
- Server health checking before test execution

## Common Patterns and Conventions

### Import Conventions
- **Absolute imports** from app root: `from app.services.service_name import ServiceName`
- **Group imports**: Standard library, third-party, local imports
- **Type hints**: All functions must include complete type annotations

### Error Handling
- Custom service exceptions with HTTP status mapping
- Global exception handler in `app/main.py`
- Structured error responses with consistent format

### Security Requirements
- JWT authentication for all reaction endpoints
- Rate limiting via SlowAPI (configurable)
- CORS configuration for frontend integration
- No hardcoded secrets - all via environment variables

## Frontend Integration

### API Structure
- **Versioned endpoints**: All routes prefixed with `/api/v1/`
- **OpenAPI documentation**: Auto-generated at `/docs` and `/redoc`
- **Structured responses**: Consistent JSON format with proper HTTP status codes

### Key Endpoints
- `POST /api/v1/reactions/react`: Core chemistry simulation
- `GET /api/v1/chemicals/`: Chemical database browsing
- `GET /api/v1/awards/me`: User's earned awards
- `GET /api/v1/awards/leaderboard/{category}`: Category rankings

### Frontend Assets
- `index.html`: SvelteKit frontend served at root `/`
- `openapi.json`: API specification for frontend integration
- Environment-aware beaker visualization and effects system

## Development Workflow

### Adding New Features
1. Create/update database models if needed
2. Add Alembic migration for schema changes
3. Implement business logic in service layer
4. Add API endpoints with proper validation
5. Create bash tests for new endpoints
6. Update OpenAPI documentation

### Code Quality Standards
- **Type safety**: All code must be fully type-hinted
- **Async by default**: Use async/await for I/O operations
- **Service isolation**: Keep business logic in service layer
- **Deterministic behavior**: Same inputs must produce same outputs
- **Scientific accuracy**: All chemistry must be grounded in PubChem data