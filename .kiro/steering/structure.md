# Project Structure & Organization

## Root Level
- `app/`: Main application package
- `tests/`: Test suite with parallel structure to app
- `alembic/`: Database migration files
- `scripts/`: Utility scripts
- `.env`: Environment configuration (copy from `.env.example`)
- `requirements.txt`: Python dependencies
- `chemezy.db`: SQLite database file (auto-generated)

## Application Structure (`app/`)

### Core Components
- `main.py`: FastAPI application entry point with middleware setup
- `core/`: Application configuration and shared utilities
  - `config.py`: Settings management with Pydantic
  - `security.py`: Authentication utilities
  - `dspy_manager.py`: AI/LLM configuration

### API Layer (`api/`)
- `api/v1/`: Versioned API endpoints
  - `api.py`: Router aggregation
  - `endpoints/`: Individual endpoint modules
    - `users.py`: Authentication endpoints
    - `reactions.py`: Core reaction processing
    - `chemicals.py`: Chemical management
    - `debug.py`: Development utilities

### Data Layer
- `models/`: SQLModel database models
- `schemas/`: Pydantic request/response schemas
- `db/`: Database configuration and session management

### Business Logic (`services/`)
- `chemical_service.py`: Chemical data management
- `reaction_service.py`: Reaction processing logic
- `pubchem_service.py`: External API integration
- `dspy_*.py`: AI reasoning modules

## Testing Structure (`tests/`)
- `helpers/`: Shared test utilities and authentication helpers
- `api/`: API endpoint tests using curl
- `services/`: Service layer tests via API calls
- `integration/`: End-to-end integration tests
- Mirrors the `app/` structure for easy navigation

## Naming Conventions
- **Files**: Snake_case (e.g., `chemical_service.py`)
- **Classes**: PascalCase (e.g., `ChemicalService`)
- **Functions/Variables**: Snake_case (e.g., `get_chemical`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `SECRET_KEY`)
- **Database tables**: Lowercase plural (e.g., `chemicals`)

## Import Patterns
- Absolute imports from app root: `from app.models.chemical import Chemical`
- Group imports: stdlib, third-party, local
- Use `from typing import` for type hints

## File Organization Rules
- One main class per file in services and models
- Group related schemas in single files
- Keep endpoint files focused on single resource
- Separate business logic from API handlers