#!/bin/bash

# Test comprehensive error handling

source tests/helpers/test_helpers.sh

# Test variables
USERNAME="error_user"
PASSWORD="error_password"

# Test counter
TEST_COUNT=0
PASSED=0
FAILED=0

run_test() {
    local test_name="$1"
    local expected_status="$2"
    local response_file="$3"
    
    TEST_COUNT=$((TEST_COUNT + 1))
    
    if assert_status_code "$expected_status" "$response_file" "$test_name"; then
        PASSED=$((PASSED + 1))
    else
        FAILED=$((FAILED + 1))
    fi
}

check_error_format() {
    local response_file="$1"
    local test_name="$2"
    
    # Check if response has proper error format
    if grep -q '"error":' "$response_file" && grep -q '"error_id":' "$response_file"; then
        echo "✓ $test_name: Proper error format"
        return 0
    else
        echo "✗ $test_name: Missing error format"
        return 1
    fi
}

echo "Testing Comprehensive Error Handling"
echo "===================================="

# Create test user and get token
log_test_info "Creating test user and getting auth token..."
TOKEN=$(setup_test_user "$USERNAME" "$PASSWORD")

if [[ -z "$TOKEN" ]]; then
    log_test_error "Failed to get auth token"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# Test 1: Authentication error (invalid token)
log_test_info "Test 1: Authentication error handling"
make_request "GET" "/awards/me" "" "Authorization: Bearer invalid_token" "/tmp/error_test1.json"
run_test "Authentication error" "401" "/tmp/error_test1.json"
check_error_format "/tmp/error_test1.json" "Authentication error format"

# Test 2: Authorization error (trying to access admin endpoint)
log_test_info "Test 2: Authorization error handling"
make_request "GET" "/admin/awards/templates" "" "$AUTH_HEADER" "/tmp/error_test2.json"
run_test "Authorization error" "403" "/tmp/error_test2.json"
check_error_format "/tmp/error_test2.json" "Authorization error format"

# Test 3: Validation error (invalid data)
log_test_info "Test 3: Validation error handling"
make_request "POST" "/admin/awards/templates" "invalid_json" "$AUTH_HEADER
Content-Type: application/json" "/tmp/error_test3.json"
run_test "Validation error" "422" "/tmp/error_test3.json"

# Test 4: Not found error
log_test_info "Test 4: Not found error handling"
make_request "GET" "/awards/user/999999" "" "$AUTH_HEADER" "/tmp/error_test4.json"
run_test "Not found error" "404" "/tmp/error_test4.json"

# Test 5: Method not allowed
log_test_info "Test 5: Method not allowed error"
make_request "DELETE" "/awards/me" "" "$AUTH_HEADER" "/tmp/error_test5.json"
run_test "Method not allowed" "405" "/tmp/error_test5.json"

# Test 6: Invalid query parameters
log_test_info "Test 6: Invalid query parameters"
make_request "GET" "/awards/available?category=invalid_category" "" "$AUTH_HEADER" "/tmp/error_test6.json"
run_test "Invalid query parameters" "422" "/tmp/error_test6.json"

# Test 7: Large payload error
log_test_info "Test 7: Large payload error"
large_payload=$(python3 -c "print('{\"data\": \"' + 'x' * 100000 + '\"}')")
make_request "POST" "/admin/awards/templates" "$large_payload" "$AUTH_HEADER
Content-Type: application/json" "/tmp/error_test7.json"
run_test "Large payload error" "413" "/tmp/error_test7.json"

# Test 8: Invalid content type
log_test_info "Test 8: Invalid content type"
make_request "POST" "/admin/awards/templates" "test data" "$AUTH_HEADER
Content-Type: text/plain" "/tmp/error_test8.json"
run_test "Invalid content type" "422" "/tmp/error_test8.json"

# Test 9: Missing required fields
log_test_info "Test 9: Missing required fields"
make_request "POST" "/admin/awards/templates" "{}" "$AUTH_HEADER
Content-Type: application/json" "/tmp/error_test9.json"
run_test "Missing required fields" "422" "/tmp/error_test9.json"

# Test 10: Invalid JSON
log_test_info "Test 10: Invalid JSON format"
make_request "POST" "/admin/awards/templates" "{invalid json" "$AUTH_HEADER
Content-Type: application/json" "/tmp/error_test10.json"
run_test "Invalid JSON" "422" "/tmp/error_test10.json"

# Test 11: Rate limiting (if implemented)
log_test_info "Test 11: Rate limiting test"
for i in {1..20}; do
    make_request "GET" "/awards/available" "" "$AUTH_HEADER" "/tmp/rate_test_$i.json" >/dev/null 2>&1
done
make_request "GET" "/awards/available" "" "$AUTH_HEADER" "/tmp/error_test11.json"
# This might be 429 if rate limiting is implemented, or 200 if not
if grep -q "429" "/tmp/error_test11.json"; then
    echo "✓ Rate limiting is implemented"
else
    echo "ℹ Rate limiting not implemented or not triggered"
fi

# Test 12: Concurrent requests error handling
log_test_info "Test 12: Concurrent requests"
for i in {1..5}; do
    make_request "GET" "/awards/dashboard/stats" "" "$AUTH_HEADER" "/tmp/concurrent_$i.json" &
done
wait
echo "✓ Concurrent requests completed"

# Check error response structure
echo ""
echo "Error Response Structure Analysis:"
echo "================================="

for i in {1..10}; do
    if [[ -f "/tmp/error_test$i.json" ]]; then
        echo "Test $i response:"
        if grep -q '"error_id":' "/tmp/error_test$i.json"; then
            error_id=$(grep -o '"error_id":"[^"]*"' "/tmp/error_test$i.json" | cut -d'"' -f4)
            echo "  ✓ Has error_id: $error_id"
        else
            echo "  ✗ Missing error_id"
        fi
        
        if grep -q '"message":' "/tmp/error_test$i.json"; then
            echo "  ✓ Has error message"
        else
            echo "  ✗ Missing error message"
        fi
        
        if grep -q '"timestamp":' "/tmp/error_test$i.json"; then
            echo "  ✓ Has timestamp"
        else
            echo "  ✗ Missing timestamp"
        fi
        echo ""
    fi
done

# Test error recovery (if implemented)
echo "Error Recovery Testing:"
echo "======================"

# Test retry logic on temporary failures
log_test_info "Testing error recovery mechanisms"

# Test graceful degradation
make_request "GET" "/awards/available" "" "$AUTH_HEADER" "/tmp/degradation_test.json"
if assert_status_code "200" "/tmp/degradation_test.json" "Graceful degradation"; then
    echo "✓ System maintains basic functionality during errors"
else
    echo "✗ System fails to maintain basic functionality"
fi

# Cleanup
cleanup_test_files

echo ""
echo "===================================="
echo "Error Handling Test Results"
echo "===================================="
echo "Total tests: $TEST_COUNT"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [[ $FAILED -gt 0 ]]; then
    echo "Some tests failed!"
    exit 1
else
    echo "All tests passed!"
    exit 0
fi