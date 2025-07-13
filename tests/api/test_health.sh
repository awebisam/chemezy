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
    
    make_request "GET" "/health" "" "" "$response_file"
    
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