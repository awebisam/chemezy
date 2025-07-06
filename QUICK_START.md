# Quick Start Guide - Chemezy Backend Engine

## 🚀 Get Running in 5 Minutes

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### 1. Clone and Setup Environment

```bash
# Copy environment file
cp .env.example .env

# Edit .env file - REQUIRED SETTINGS:
# SECRET_KEY=your-secure-secret-key-here  (generate with: openssl rand -hex 32)
# AZURE_OPENAI_KEY=your-azure-openai-api-key-here (required)
# AZURE_OPENAI_ENDPOINT=your-azure-openai-endpoint-here (required)
# AZURE_OPENAI_API_VERSION=your-azure-openai-api-version-here (required)
# AZURE_OPENAI_DEPLOYMENT_NAME=your-azure-openai-deployment-name-here (required)
# AZURE_OPENAI_MODEL_NAME=your-azure-openai-model-name-here (required)
# ALLOWED_ORIGINS=your-allowed-origins-here (required)
```

### 2. Start Database

```bash
# Start PostgreSQL container
docker-compose up postgres -d

# Wait a moment for PostgreSQL to start
sleep 10
```

### 3. Install Dependencies & Setup Database

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create database tables
python scripts/init_db.py

# Or use Alembic for migrations
alembic upgrade head
```

### 4. Run the Application

```bash
# Start the FastAPI server
uvicorn app.main:app --reload
```

The API will be available at:
- **Application**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 5. Test the API

#### Register a User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "username": "chemist",
       "email": "chemist@example.com", 
       "password": "password123"
     }'
```

#### Login and Get Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=chemist&password=password123"
```

Save the `access_token` from the response.

#### Predict a Chemical Reaction
```bash
curl -X POST "http://localhost:8000/api/v1/reactions/react" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
     -H "Content-Type: application/json" \
     -d '{
       "chemicals": ["H2O", "NaCl"],
       "environment": "Earth (Normal)"
     }'
```

### 6. Run Tests

```bash
# Run all tests with coverage
pytest

# Run specific test files
pytest tests/test_api/test_reactions.py
pytest tests/test_services/test_reaction_engine.py
```

## 🐳 Docker Alternative

If you prefer to run everything in Docker:

```bash
# Build and start all services
docker-compose up --build

# The API will be available at http://localhost:8000
```

## 🔧 Configuration Options

Edit `.env` file for:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://chemezy:chemezy@localhost/chemezy` |
| `SECRET_KEY` | JWT signing secret | Generate with `openssl rand -hex 32` |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key for DSPy | Required |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_API_VERSION` | Azure OpenAI API version | Required |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI deployment name | Required |
| `AZURE_OPENAI_MODEL_NAME` | Azure OpenAI model name | Required |
| `ALLOWED_ORIGINS` | Allowed origins for CORS | Required |
| `DEBUG` | Debug mode | `false` |

## 📊 Example API Response

```json
{
  "request_id": "c4a2b-11e8-a8d5-f2801f1b9fd1",
  "products": [
    {
      "formula": "NaCl",
      "name": "Sodium Chloride",
      "state": "dissolved"
    },
    {
      "formula": "H2O",
      "name": "Water",
      "state": "liquid"
    }
  ],
  "effects": [
    "dissolving",
    "ionic_dissociation",
    "temperature_change"
  ],
  "state_change": null,
  "description": "Sodium chloride dissolves in water, dissociating into Na+ and Cl- ions in an endothermic process.",
  "is_world_first": true
}
```

## 🚨 Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart database
docker-compose restart postgres
```

### Import Errors
```bash
# Ensure you're in the project root directory
# Install dependencies
pip install -r requirements.txt
```

### Test Failures
```bash
# Check test database setup
pytest tests/conftest.py -v

# Run with more verbose output
pytest -v -s
```

## 🔍 Development Tools

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Database Admin**: Use tools like pgAdmin with connection details from `.env`
- **Test Coverage**: Run `pytest --cov=app --cov-report=html` then open `htmlcov/index.html`

## 🎯 Next Steps

1. **Explore the API** using the interactive docs at `/docs`
2. **Configure OpenAI API key** for full DSPy functionality
3. **Create more complex reactions** and discover world-first effects
4. **View your discoveries** at `/api/v1/reactions/discoveries`
5. **Check the leaderboard** at `/api/v1/reactions/discoveries/all`

For detailed architecture and implementation details, see `PROJECT_SUMMARY.md`.

---

**Need Help?** 
- Check the FastAPI logs for detailed error messages
- Ensure all environment variables are set correctly
- Verify PostgreSQL is running and accessible
- Make sure you're using the correct Bearer token in requests