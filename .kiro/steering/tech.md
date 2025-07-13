# Technology Stack & Build System

## Core Framework
- **FastAPI**: Main web framework with automatic OpenAPI docs
- **SQLModel**: Database ORM with Pydantic integration
- **Pydantic**: Data validation and serialization
- **Alembic**: Database migrations

## Database
- **SQLite**: Development database (file-based: `chemezy.db`)
- **PostgreSQL**: Production database option
- Database URL configured via `DATABASE_URL` environment variable
- Development workflow: Delete and recreate database for fresh starts

## AI & External Services
- **DSPy**: LLM orchestration and structured reasoning
- **Azure OpenAI**: Primary LLM provider (GPT-4o-mini)
- **PubChem API**: Real chemical data source
- **RAG Pipeline**: Retrieval-Augmented Generation for scientific accuracy

## Security & Performance
- **JWT**: Authentication with python-jose
- **Passlib + bcrypt**: Password hashing
- **SlowAPI**: Rate limiting middleware
- **CORS**: Cross-origin resource sharing

## Development Tools
- **curl**: HTTP testing via bash scripts
- **uvicorn**: ASGI server with hot reload
- **Docker**: Containerization support

## Common Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database
alembic upgrade head

# Run development server
uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests (automatically resets database)
./scripts/run_tests.sh

# Run specific test suites
./scripts/run_tests.sh api
./scripts/run_tests.sh services
./scripts/run_tests.sh integration

# Run tests with verbose output
./scripts/run_tests.sh --verbose

# Skip database reset for faster iteration
./scripts/run_tests.sh --skip-db-reset

# Combine options
./scripts/run_tests.sh api --verbose --skip-db-reset
```

### Database Management
```bash
# Fresh start (delete and recreate database)
rm -f chemezy.db
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Note: Tests automatically reset database unless --skip-db-reset flag is used
```

### Docker
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

## Environment Configuration
Required environment variables in `.env`:
- `SECRET_KEY`: JWT signing key (required)
- `DATABASE_URL`: Database connection string
- `AZURE_OPENAI_KEY`: Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI endpoint
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Model deployment name