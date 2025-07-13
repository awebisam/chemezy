#!/bin/bash

# Integration test for complete reaction flow

# Source test helpers
source "tests/helpers/test_helpers.sh"

# Test setup
setup_test "Reaction Flow Integration Test"

# Test complete reaction flow: auth -> get chemicals -> perform reaction
test_complete_reaction_flow() {
    log_test_info "Testing complete reaction flow"
    
    local auth_response="/tmp/test_flow_auth_response.json"
    local chemicals_response="/tmp/test_flow_chemicals_response.json"
    local reaction_response="/tmp/test_flow_reaction_response.json"
    
    local username="flowtest_$(date +%s)"
    local password="flowpass123"
    
    # Step 1: Register user
    make_request "POST" "/auth/register" "{\"username\":\"$username\",\"password\":\"$password\"}" "Content-Type: application/json" "$auth_response"
    
    if ! assert_status_code "201" "$auth_response" "User registration successful"; then
        return 1
    fi
    
    # Step 2: Login and get token
    local token=$(get_auth_token "$username" "$password")
    
    if [[ -z "$token" ]]; then
        log_test_error "Failed to get authentication token"
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} Authentication successful"
    
    # Step 3: Get chemicals
    make_request "GET" "/chemicals/" "" "Authorization: Bearer $token" "$chemicals_response"
    
    if ! assert_status_code "200" "$chemicals_response" "Get chemicals successful"; then
        return 1
    fi
    
    # Step 4: Perform a simple reaction (if chemicals are available)
    local body=$(grep -v "^HTTP_STATUS:" "$chemicals_response")
    local chemical_count=$(echo "$body" | jq -r '.count' 2>/dev/null)
    
    if [[ "$chemical_count" != "null" && "$chemical_count" -gt 0 ]]; then
        echo -e "${GREEN}✓${NC} Chemicals retrieved (count: $chemical_count)"
        
        # Try a simple reaction with common chemicals
        local reaction_data='{
            "reactants": ["H2O", "NaCl"],
            "environment": "neutral",
            "catalyst_id": null
        }'
        
        make_request "POST" "/reactions/react" "$reaction_data" "Authorization: Bearer $token
Content-Type: application/json" "$reaction_response"
        
        if assert_status_code "200" "$reaction_response" "Reaction request successful"; then
            echo -e "${GREEN}✓${NC} Complete reaction flow successful"
        else
            log_test_error "Reaction failed"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠${NC} No chemicals available for reaction test"
    fi
}

# Test error handling in reaction flow
test_reaction_flow_error_handling() {
    log_test_info "Testing reaction flow error handling"
    
    local response_file="/tmp/test_flow_error_response.json"
    local token=$(setup_test_user "errortest" "errorpass")
    
    if [[ -z "$token" ]]; then
        log_test_error "Failed to get authentication token"
        return 1
    fi
    
    # Test with invalid reaction data
    local invalid_reaction_data='{
        "reactants": [],
        "environment": "invalid",
        "catalyst_id": null
    }'
    
    make_request "POST" "/reactions/react" "$invalid_reaction_data" "Authorization: Bearer $token
Content-Type: application/json" "$response_file"
    
    # Should return error status (400, 422, etc.)
    local status=$(grep "^HTTP_STATUS:" "$response_file" | cut -d: -f2 | tr -d ' ')
    
    if [[ "$status" -ge 400 && "$status" -lt 500 ]]; then
        echo -e "${GREEN}✓${NC} Error handling works correctly (HTTP $status)"
    else
        echo -e "${RED}✗${NC} Error handling failed (HTTP $status)"
        return 1
    fi
}

# Run tests
test_complete_reaction_flow
complete_flow_result=$?

test_reaction_flow_error_handling
error_handling_result=$?

# Cleanup
teardown_test "Reaction Flow Integration Test"

# Exit with failure if any test failed
if [[ $complete_flow_result -ne 0 || $error_handling_result -ne 0 ]]; then
    exit 1
fi

exit 0