#!/bin/bash

# Chemezy Backend Engine - Development Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

echo "🚀 Setting up Chemezy Backend Engine Development Environment"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
print_status "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    print_error "Python 3.11+ is required. Found: $python_version"
    print_error "Please install Python 3.11 or higher and try again."
    exit 1
fi

print_success "Python version: $(python3 --version)"

# Create virtual environment
print_status "Setting up virtual environment..."
if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install system dependencies info
print_status "Checking system dependencies..."
print_warning "Make sure you have the following system packages installed:"
echo "  • PostgreSQL development headers (libpq-dev on Ubuntu/Debian)"
echo "  • Python development headers (python3-dev)"
echo "  • Build essentials (build-essential)"
echo ""
echo "On Ubuntu/Debian, install with:"
echo "  sudo apt-get update"
echo "  sudo apt-get install -y libpq-dev python3-dev build-essential"
echo ""
echo "On macOS with Homebrew:"
echo "  brew install postgresql"
echo ""

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt || {
    print_error "Failed to install dependencies. Check the system dependencies above."
    exit 1
}

print_success "Dependencies installed successfully"

# Set up environment file
print_status "Setting up environment configuration..."
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        print_success "Environment file created from template"
        print_warning "Please update .env with your actual configuration:"
        echo "  • Set a secure SECRET_KEY"
        echo "  • Configure DATABASE_URL for your PostgreSQL instance"
        echo "  • Add your OPENAI_API_KEY for DSPy functionality"
        echo "  • Update ALLOWED_ORIGINS for your frontend domain"
    else
        print_error ".env.example not found!"
        exit 1
    fi
else
    print_warning ".env file already exists"
fi

# Database setup instructions
print_status "Database setup instructions..."
print_warning "Please ensure PostgreSQL is running and configured:"
echo ""
echo "1. Install PostgreSQL if not already installed"
echo "2. Create database and user:"
echo "   sudo -u postgres psql"
echo "   CREATE DATABASE chemezy;"
echo "   CREATE USER chemezy WITH PASSWORD 'chemezy';"
echo "   GRANT ALL PRIVILEGES ON DATABASE chemezy TO chemezy;"
echo "   \q"
echo ""
echo "3. Update DATABASE_URL in .env if using different credentials"
echo ""

# Check if we can connect to database
print_status "Testing database connection..."
if python3 -c "
import os
from sqlalchemy import create_engine
from app.core.config import settings
try:
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        result = conn.execute('SELECT 1')
    print('✅ Database connection successful')
except Exception as e:
    print(f'⚠️ Database connection failed: {e}')
    print('Please set up PostgreSQL and update .env configuration')
" 2>/dev/null; then
    # Run migrations if database is available
    print_status "Running database migrations..."
    alembic upgrade head || {
        print_warning "Migrations failed. You may need to create the initial migration:"
        echo "  alembic revision --autogenerate -m 'Initial models'"
        echo "  alembic upgrade head"
    }
fi

# Install development tools
print_status "Installing development tools..."
pip install -q flake8 mypy bandit black isort pre-commit 2>/dev/null || {
    print_warning "Some development tools failed to install (non-critical)"
}

# Set up pre-commit hooks (if available)
if command -v pre-commit &> /dev/null; then
    print_status "Setting up pre-commit hooks..."
    cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127]
EOF
    pre-commit install || print_warning "Pre-commit setup failed (non-critical)"
fi

# Create useful development aliases
print_status "Creating development shortcuts..."
cat > scripts/dev_aliases.sh << 'EOF'
#!/bin/bash
# Development aliases for Chemezy Backend Engine
# Source this file to get useful shortcuts: source scripts/dev_aliases.sh

alias chemezy-test="./scripts/run_tests.sh"
alias chemezy-dev="uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
alias chemezy-shell="python3 -c 'from app.db.session import SessionLocal; from app.models.user import User; from app.models.reaction import *; print(\"Chemezy shell ready. Available: SessionLocal, User, ReactionCache, Discovery\")'"
alias chemezy-migrate="alembic revision --autogenerate"
alias chemezy-upgrade="alembic upgrade head"
alias chemezy-coverage="pytest --cov=app --cov-report=html && open htmlcov/index.html"
EOF

chmod +x scripts/dev_aliases.sh
print_success "Development shortcuts created in scripts/dev_aliases.sh"

# Final instructions
print_success "Development environment setup complete! ✅"
echo ""
echo "🎯 Next Steps:"
echo "1. Update .env with your actual configuration"
echo "2. Ensure PostgreSQL is running and accessible"
echo "3. Run initial tests: ./scripts/run_tests.sh"
echo "4. Start development server: uvicorn app.main:app --reload"
echo ""
echo "📖 Useful Commands:"
echo "  • Run tests: ./scripts/run_tests.sh"
echo "  • Start server: uvicorn app.main:app --reload"
echo "  • Create migration: alembic revision --autogenerate -m 'description'"
echo "  • Apply migrations: alembic upgrade head"
echo "  • Load dev aliases: source scripts/dev_aliases.sh"
echo ""
echo "📁 Important Files:"
echo "  • .env - Environment configuration"
echo "  • app/main.py - FastAPI application entry point"
echo "  • alembic/ - Database migration files"
echo "  • tests/ - Test suite"
echo ""
print_success "Happy coding! 🧪⚗️"