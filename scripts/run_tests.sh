#!/bin/bash

# Main test runner script for Chemezy API testing
# Usage: ./scripts/run_tests.sh [suite] [--verbose] [--skip-db-reset]
# 
# Features:
# - Automatically resets database with fresh migrations before tests
# - Ensures clean state for consistent test results
# - Supports test suite selection and verbose output
# - Option to skip database reset for faster iteration

set -e

# Configuration
BASE_URL="http://localhost:8000/api/v1"
TEST_DIR="tests"
VERBOSE=false
SUITE=""
SKIP_DB_RESET=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --skip-db-reset)
            SKIP_DB_RESET=true
            shift
            ;;
        api|services|integration)
            SUITE="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [api|services|integration] [--verbose] [--skip-db-reset]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test result tracking
run_test() {
    local test_name="$1"
    local test_file="$2"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_info "Running: $test_name"
    
    if [[ "$VERBOSE" == true ]]; then
        echo "  Command: bash $test_file"
    fi
    
    # Run the test and capture output
    if bash "$test_file" 2>&1; then
        log_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    
    echo ""
}

# Reset database with fresh migrations
reset_database() {
    log_info "Resetting database with fresh migrations..."
    
    # Remove existing database
    if [[ -f "chemezy.db" ]]; then
        rm -f chemezy.db
        log_success "Removed existing database"
    fi
    
    # Check if alembic is available
    if ! command -v alembic &> /dev/null; then
        log_error "Alembic not found. Please install it or activate your virtual environment."
        return 1
    fi
    
    # Run migrations
    log_info "Running database migrations..."
    if alembic upgrade head > /dev/null 2>&1; then
        log_success "Database migrations completed"
        return 0
    else
        log_error "Database migrations failed"
        log_warning "Please check your alembic configuration and try again"
        return 1
    fi
}

# Check if server is running
check_server() {
    log_info "Checking if server is running at $BASE_URL..."
    
    if curl -s -f "$BASE_URL/health" > /dev/null 2>&1; then
        log_success "Server is running"
        return 0
    else
        log_error "Server is not running at $BASE_URL"
        log_warning "Please start the server with: uvicorn app.main:app --reload"
        return 1
    fi
}

# Run tests in a specific directory
run_test_suite() {
    local suite_dir="$1"
    local suite_name="$2"
    
    if [[ ! -d "$suite_dir" ]]; then
        log_warning "Test suite directory not found: $suite_dir"
        return
    fi
    
    log_info "Running $suite_name tests..."
    
    # Find all .sh files in the suite directory
    local test_files=$(find "$suite_dir" -name "*.sh" | sort)
    
    if [[ -z "$test_files" ]]; then
        log_warning "No test files found in $suite_dir"
        return
    fi
    
    for test_file in $test_files; do
        local test_name=$(basename "$test_file" .sh)
        run_test "$test_name" "$test_file"
    done
}

# Main execution
main() {
    echo "=========================================="
    echo "  Chemezy API Test Suite"
    echo "=========================================="
    echo ""
    
    # Reset database with fresh migrations (unless skipped)
    if [[ "$SKIP_DB_RESET" != true ]]; then
        if ! reset_database; then
            exit 1
        fi
        echo ""
    else
        log_warning "Skipping database reset (--skip-db-reset flag)"
        echo ""
    fi
    
    # Check if server is running
    if ! check_server; then
        exit 1
    fi
    
    echo ""
    
    # Export BASE_URL for test scripts
    export BASE_URL
    export VERBOSE
    
    # Run specific suite or all suites
    if [[ -n "$SUITE" ]]; then
        run_test_suite "$TEST_DIR/$SUITE" "$SUITE"
    else
        run_test_suite "$TEST_DIR/api" "API"
        run_test_suite "$TEST_DIR/services" "Services"
        run_test_suite "$TEST_DIR/integration" "Integration"
    fi
    
    # Print summary
    echo "=========================================="
    echo "  Test Results Summary"
    echo "=========================================="
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
    echo ""
    
    if [[ $FAILED_TESTS -gt 0 ]]; then
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

# Run main function
main "$@"