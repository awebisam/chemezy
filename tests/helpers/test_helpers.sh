#!/bin/bash

# Test helper functions for Chemezy API testing
# Note: Database is automatically reset before tests unless --skip-db-reset flag is used

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-}"
    
    if [[ "$expected" == "$actual" ]]; then
        echo -e "${GREEN}✓${NC} $message"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  Expected: $expected"
        echo "  Actual: $actual"
        return 1
    fi
}

assert_contains() {
    local substring="$1"
    local string="$2"
    local message="${3:-}"
    
    if [[ "$string" == *"$substring"* ]]; then
        echo -e "${GREEN}✓${NC} $message"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  String does not contain: $substring"
        echo "  Actual string: $string"
        return 1
    fi
}

assert_status_code() {
    local expected_code="$1"
    local response_file="$2"
    local message="${3:-}"
    
    local actual_code=$(grep "^HTTP_STATUS:" "$response_file" | cut -d: -f2 | tr -d ' ')
    
    if [[ "$expected_code" == "$actual_code" ]]; then
        echo -e "${GREEN}✓${NC} $message (HTTP $actual_code)"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  Expected HTTP: $expected_code"
        echo "  Actual HTTP: $actual_code"
        return 1
    fi
}

assert_json_key_exists() {
    local key="$1"
    local json_file="$2"
    local message="${3:-}"
    
    if jq -e ".$key" "$json_file" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $message"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  JSON key not found: $key"
        return 1
    fi
}

assert_json_value() {
    local key="$1"
    local expected_value="$2"
    local json_file="$3"
    local message="${4:-}"
    
    local actual_value=$(jq -r ".$key" "$json_file" 2>/dev/null)
    
    if [[ "$expected_value" == "$actual_value" ]]; then
        echo -e "${GREEN}✓${NC} $message"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        echo "  Expected $key: $expected_value"
        echo "  Actual $key: $actual_value"
        return 1
    fi
}

# HTTP request wrapper with response capture
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    local headers="$4"
    local response_file="$5"
    
    local curl_args=(-s -w "HTTP_STATUS:%{http_code}\n" -X "$method")
    
    if [[ -n "$headers" ]]; then
        while IFS= read -r header; do
            curl_args+=(-H "$header")
        done <<< "$headers"
    fi
    
    if [[ -n "$data" ]]; then
        curl_args+=(-d "$data")
    fi
    
    curl "${curl_args[@]}" "$BASE_URL$endpoint" > "$response_file" 2>&1
}

# Authentication helper
get_auth_token() {
    local username="$1"
    local password="$2"
    local response_file="/tmp/auth_response.json"
    
    make_request "POST" "/auth/token" "username=$username&password=$password" "Content-Type: application/x-www-form-urlencoded" "$response_file"
    
    local token=$(grep -v "^HTTP_STATUS:" "$response_file" | jq -r '.access_token' 2>/dev/null)
    
    if [[ "$token" != "null" && -n "$token" ]]; then
        echo "$token"
    else
        echo ""
    fi
}

# Setup test user (helper for tests that need authentication)
setup_test_user() {
    local username="${1:-testuser}"
    local password="${2:-testpass}"
    local response_file="/tmp/setup_user_response.json"
    
    # Try to create user (might fail if already exists)
    make_request "POST" "/auth/register" "{\"username\":\"$username\",\"password\":\"$password\"}" "Content-Type: application/json" "$response_file"
    
    # Return the auth token
    get_auth_token "$username" "$password"
}

# Cleanup function
cleanup_test_files() {
    rm -f /tmp/test_*.json /tmp/auth_*.json /tmp/setup_*.json
}

# Test framework setup
setup_test() {
    local test_name="$1"
    echo "Setting up test: $test_name"
    cleanup_test_files
}

teardown_test() {
    local test_name="$1"
    echo "Tearing down test: $test_name"
    cleanup_test_files
}

# Utility functions
log_test_info() {
    echo -e "${BLUE}[TEST INFO]${NC} $1"
}

log_test_error() {
    echo -e "${RED}[TEST ERROR]${NC} $1"
}

# JSON response parsing helpers
get_json_value() {
    local key="$1"
    local json_file="$2"
    
    jq -r ".$key" "$json_file" 2>/dev/null
}

get_json_array_length() {
    local array_key="$1"
    local json_file="$2"
    
    jq -r ".$array_key | length" "$json_file" 2>/dev/null
}

# Export functions for use in test scripts
export -f assert_equals
export -f assert_contains
export -f assert_status_code
export -f assert_json_key_exists
export -f assert_json_value
export -f make_request
export -f get_auth_token
export -f setup_test_user
export -f cleanup_test_files
export -f setup_test
export -f teardown_test
export -f log_test_info
export -f log_test_error
export -f get_json_value
export -f get_json_array_length