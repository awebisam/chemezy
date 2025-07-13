#!/bin/bash

# Test health endpoint

# Source test helpers
source "tests/helpers/test_helpers.sh"

# Test setup
setup_test "Health Check"

# Test health endpoint
test_health_endpoint() {
    log_test_info "Testing health endpoint"
    
    local response_file="/tmp/test_health_response.json"
    
    # Health endpoint is at root level, not under /api/v1
    curl -s -w "HTTP_STATUS:%{http_code}\n" -X GET "http://localhost:8000/health" > "$response_file" 2>&1
    
    assert_status_code "200" "$response_file" "Health endpoint returns 200"
    
    # Check if response contains status (if your health endpoint returns JSON)
    if grep -q "HTTP_STATUS:200" "$response_file"; then
        echo -e "${GREEN}✓${NC} Health endpoint is working"
    else
        echo -e "${RED}✗${NC} Health endpoint failed"
        return 1
    fi
}

# Run test
test_health_endpoint
test_result=$?

# Cleanup
teardown_test "Health Check"

exit $test_result