# Chemezy Backend Technology Stack

## Core Framework
- **FastAPI**: Modern Python web framework with automatic OpenAPI documentation
- **SQLModel**: Type-safe ORM built on SQLAlchemy with Pydantic integration
- **SQLite**: Lightweight database for development (production-ready with proper scaling)
- **Alembic**: Database migration management

## AI & External Services
- **DSPy**: Structured LLM programming framework for reliable AI reasoning
- **Azure OpenAI**: GPT-4o-mini for chemistry reasoning (configurable)
- **PubChem API**: Real chemical data source with retry logic
- **RAG Architecture**: Retrieval-Augmented Generation for grounded chemistry responses

## Authentication & Security
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Passlib + bcrypt**: Secure password hashing
- **Rate Limiting**: SlowAPI integration for API protection
- **CORS**: Configurable cross-origin resource sharing

## Development Tools
- **Uvicorn**: ASGI server with hot reload for development
- **Docker**: Containerization with Alpine Linux base
- **Shell Testing**: Comprehensive bash-based API testing suite
- **Alembic**: Database schema versioning and migrations

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Database setup
alembic upgrade head

# Start development server
uvicorn app.main:app --reload

# Run tests
./scripts/run_tests.sh
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Reset database (development)
rm chemezy.db && alembic upgrade head
```

### Testing
```bash
# Run all tests with fresh database
./scripts/run_tests.sh

# Run specific test suite
./scripts/run_tests.sh api

# Skip database reset for faster iteration
./scripts/run_tests.sh --skip-db-reset
```

### Docker Operations
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run in background
docker-compose up -d
```

## Environment Configuration
All configuration via `.env` file (copy from `.env.example`):
- `SECRET_KEY`: Required for JWT tokens (no default for security)
- `AZURE_OPENAI_*`: AI service configuration
- `DATABASE_URL`: Database connection string
- `DEBUG`: Development mode toggle