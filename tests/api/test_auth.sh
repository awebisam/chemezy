#!/bin/bash

# Test authentication endpoints

# Source test helpers
source "tests/helpers/test_helpers.sh"

# Test setup
setup_test "Authentication Tests"

# Test user registration
test_user_registration() {
    log_test_info "Testing user registration"
    
    local response_file="/tmp/test_register_response.json"
    local username="testuser_$(date +%s)"
    local password="testpass123"
    
    make_request "POST" "/auth/register" "{\"username\":\"$username\",\"password\":\"$password\",\"email\":\"$username@example.com\"}" "Content-Type: application/json" "$response_file"
    
    assert_status_code "201" "$response_file" "User registration returns 201"
    
    # Check if response contains user info
    if grep -q "HTTP_STATUS:201" "$response_file"; then
        echo -e "${GREEN}✓${NC} User registration successful"
    else
        echo -e "${RED}✗${NC} User registration failed"
        return 1
    fi
}

# Test user login
test_user_login() {
    log_test_info "Testing user login"
    
    local response_file="/tmp/test_login_response.json"
    local username="testuser_$(date +%s)"
    local password="testpass123"
    
    # First register a user
    make_request "POST" "/auth/register" "{\"username\":\"$username\",\"password\":\"$password\",\"email\":\"$username@example.com\"}" "Content-Type: application/json" "/tmp/register_temp.json"
    
    # Then try to login
    make_request "POST" "/auth/token" "username=$username&password=$password" "Content-Type: application/x-www-form-urlencoded" "$response_file"
    
    assert_status_code "200" "$response_file" "User login returns 200"
    
    # Check if response contains access token
    local token=$(grep -v "^HTTP_STATUS:" "$response_file" | jq -r '.access_token' 2>/dev/null)
    
    if [[ "$token" != "null" && -n "$token" ]]; then
        echo -e "${GREEN}✓${NC} Login successful, token received"
    else
        echo -e "${RED}✗${NC} Login failed, no token received"
        return 1
    fi
}

# Test invalid login
test_invalid_login() {
    log_test_info "Testing invalid login"
    
    local response_file="/tmp/test_invalid_login_response.json"
    
    make_request "POST" "/auth/token" "username=invalid&password=invalid" "Content-Type: application/x-www-form-urlencoded" "$response_file"
    
    assert_status_code "401" "$response_file" "Invalid login returns 401"
}

# Run tests
test_user_registration
registration_result=$?

test_user_login
login_result=$?

test_invalid_login
invalid_login_result=$?

# Cleanup
teardown_test "Authentication Tests"

# Exit with failure if any test failed
if [[ $registration_result -ne 0 || $login_result -ne 0 || $invalid_login_result -ne 0 ]]; then
    exit 1
fi

exit 0