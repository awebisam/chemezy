#!/bin/bash

# Test chemicals endpoint

# Source test helpers
source "tests/helpers/test_helpers.sh"

# Test setup
setup_test "Chemicals API Tests"

# Test get chemicals endpoint
test_get_chemicals() {
    log_test_info "Testing get chemicals endpoint"
    
    local response_file="/tmp/test_chemicals_response.json"
    local token=$(setup_test_user "chemtest" "chempass")
    
    if [[ -z "$token" ]]; then
        log_test_error "Failed to get authentication token"
        return 1
    fi
    
    make_request "GET" "/chemicals/" "" "Authorization: Bearer $token" "$response_file"
    
    assert_status_code "200" "$response_file" "Get chemicals returns 200"
    
    # Check if response contains chemicals data
    local body=$(grep -v "^HTTP_STATUS:" "$response_file")
    local count=$(echo "$body" | jq -r '.count' 2>/dev/null)
    
    if [[ "$count" != "null" && "$count" -ge 0 ]]; then
        echo -e "${GREEN}✓${NC} Chemicals endpoint returns valid data (count: $count)"
    else
        echo -e "${RED}✗${NC} Chemicals endpoint response invalid"
        return 1
    fi
}

# Test get chemicals without authentication
test_get_chemicals_no_auth() {
    log_test_info "Testing get chemicals without authentication"
    
    local response_file="/tmp/test_chemicals_no_auth_response.json"
    
    make_request "GET" "/chemicals/" "" "" "$response_file"
    
    assert_status_code "401" "$response_file" "Get chemicals without auth returns 401"
}

# Test get chemicals with pagination
test_get_chemicals_pagination() {
    log_test_info "Testing get chemicals with pagination"
    
    local response_file="/tmp/test_chemicals_pagination_response.json"
    local token=$(setup_test_user "chemtest2" "chempass2")
    
    if [[ -z "$token" ]]; then
        log_test_error "Failed to get authentication token"
        return 1
    fi
    
    make_request "GET" "/chemicals/?limit=5&offset=0" "" "Authorization: Bearer $token" "$response_file"
    
    assert_status_code "200" "$response_file" "Get chemicals with pagination returns 200"
    
    # Check if response contains results array
    local body=$(grep -v "^HTTP_STATUS:" "$response_file")
    local results_length=$(echo "$body" | jq -r '.results | length' 2>/dev/null)
    
    if [[ "$results_length" != "null" && "$results_length" -ge 0 ]]; then
        echo -e "${GREEN}✓${NC} Chemicals pagination works (results: $results_length)"
    else
        echo -e "${RED}✗${NC} Chemicals pagination failed"
        return 1
    fi
}

# Run tests
test_get_chemicals
get_chemicals_result=$?

test_get_chemicals_no_auth
no_auth_result=$?

test_get_chemicals_pagination
pagination_result=$?

# Cleanup
teardown_test "Chemicals API Tests"

# Exit with failure if any test failed
if [[ $get_chemicals_result -ne 0 || $no_auth_result -ne 0 || $pagination_result -ne 0 ]]; then
    exit 1
fi

exit 0