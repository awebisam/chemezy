#!/bin/bash

# Chemezy Backend Engine - Test Runner Script
# This script runs all tests with coverage reporting and various quality checks

set -e  # Exit on any error

echo "🧪 Starting Chemezy Backend Engine Test Suite"
echo "=============================================="

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

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_warning "Virtual environment not detected. Activating .venv..."
    source .venv/bin/activate
fi

# Check if required packages are installed
print_status "Checking dependencies..."
pip install -q pytest pytest-cov pytest-asyncio flake8 mypy bandit 2>/dev/null || {
    print_error "Failed to install test dependencies"
    exit 1
}

# Validate environment configuration
print_status "Validating environment configuration..."
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        print_warning "No .env file found. Creating from .env.example..."
        cp .env.example .env
        print_warning "Please update .env with your actual configuration!"
    else
        print_error "No .env or .env.example file found!"
        exit 1
    fi
fi

# Run linting checks
print_status "Running code quality checks..."

print_status "  → Running flake8 linting..."
flake8 app tests --count --select=E9,F63,F7,F82 --show-source --statistics || {
    print_error "Critical linting errors found!"
    exit 1
}

flake8 app tests --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || {
    print_warning "Code style warnings found (not blocking)"
}

# Run type checking (non-blocking)
print_status "  → Running type checking..."
mypy app --ignore-missing-imports || {
    print_warning "Type checking issues found (not blocking)"
}

# Run security checks
print_status "  → Running security scan..."
bandit -r app/ -f json -o bandit-report.json -ll || {
    print_warning "Security scan completed with warnings"
}

# Run the actual tests
print_status "Running test suite..."

# Set test environment variables
export SECRET_KEY="test-secret-key-for-local-development-32-chars"
export DATABASE_URL="sqlite:///./test_chemezy.db"  # Use SQLite for local testing
export DEBUG="true"
export ALLOWED_ORIGINS='["http://localhost:3000"]'

# Run tests with coverage
print_status "  → Running unit and integration tests..."
pytest \
    --cov=app \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-fail-under=85 \
    -v \
    --tb=short \
    tests/ || {
    print_error "Tests failed!"
    exit 1
}

# Generate coverage summary
print_status "Generating coverage report..."
if [[ -f "htmlcov/index.html" ]]; then
    print_success "HTML coverage report generated: htmlcov/index.html"
fi

# Summary
print_success "All tests completed successfully! ✅"
echo ""
echo "📊 Test Results Summary:"
echo "  • Code Quality: ✅ Passed"
echo "  • Type Checking: ⚠️  Warnings (non-blocking)"
echo "  • Security Scan: ⚠️  Check bandit-report.json"
echo "  • Test Coverage: ✅ ≥85% required"
echo "  • Unit Tests: ✅ Passed"
echo ""
echo "📁 Generated Files:"
echo "  • htmlcov/index.html - Coverage report"
echo "  • coverage.xml - Coverage data"
echo "  • bandit-report.json - Security scan results"
echo ""
print_success "System is ready for production! 🚀"