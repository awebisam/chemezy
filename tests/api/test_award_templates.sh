#!/bin/bash

# Test award template seeding and retrieval

source tests/helpers/test_helpers.sh

# Test variables
USERNAME="test_user"
PASSWORD="test_password"

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

echo "Testing Award Template Seeding and Retrieval"
echo "==========================================="

# Create test user and get token
log_test_info "Creating test user and getting auth token..."
TOKEN=$(setup_test_user "$USERNAME" "$PASSWORD")

if [[ -z "$TOKEN" ]]; then
    log_test_error "Failed to get auth token"
    exit 1
fi

# Test 1: Get available awards (should work even without templates)
log_test_info "Test 1: Get available awards"
make_request "GET" "/awards/available" "" "Authorization: Bearer $TOKEN" "/tmp/available_awards.json"
run_test "Get available awards" "200" "/tmp/available_awards.json"

# Test 2: Get available awards with category filter
log_test_info "Test 2: Get available awards filtered by discovery category"
make_request "GET" "/awards/available?category=discovery" "" "Authorization: Bearer $TOKEN" "/tmp/available_discovery.json"
run_test "Get discovery awards" "200" "/tmp/available_discovery.json"

# Test 3: Get available awards with community category
log_test_info "Test 3: Get available awards filtered by community category"
make_request "GET" "/awards/available?category=community" "" "Authorization: Bearer $TOKEN" "/tmp/available_community.json"
run_test "Get community awards" "200" "/tmp/available_community.json"

# Test 4: Test template validation (should fail without admin privileges)
log_test_info "Test 4: Try to create template without admin privileges"
template_data='{
    "name": "Test Template",
    "description": "Test description",
    "category": "discovery",
    "criteria": {"type": "discovery_count", "threshold": 1},
    "metadata": {"points": 10}
}'
make_request "POST" "/admin/awards/templates" "$template_data" "Authorization: Bearer $TOKEN
Content-Type: application/json" "/tmp/create_template.json"
run_test "Create template without admin privileges" "403" "/tmp/create_template.json"

# Test 5: Check if seeded templates exist by checking available awards
log_test_info "Test 5: Check if seeded templates are available"
make_request "GET" "/awards/available" "" "Authorization: Bearer $TOKEN" "/tmp/check_seeded.json"
run_test "Check seeded templates" "200" "/tmp/check_seeded.json"

# Test 6: Test category-specific template retrieval
log_test_info "Test 6: Test database_contribution category"
make_request "GET" "/awards/available?category=database_contribution" "" "Authorization: Bearer $TOKEN" "/tmp/database_contrib.json"
run_test "Get database contribution awards" "200" "/tmp/database_contrib.json"

# Test 7: Test special category
log_test_info "Test 7: Test special category"
make_request "GET" "/awards/available?category=special" "" "Authorization: Bearer $TOKEN" "/tmp/special_awards.json"
run_test "Get special awards" "200" "/tmp/special_awards.json"

# Test 8: Test achievement category
log_test_info "Test 8: Test achievement category"
make_request "GET" "/awards/available?category=achievement" "" "Authorization: Bearer $TOKEN" "/tmp/achievement_awards.json"
run_test "Get achievement awards" "200" "/tmp/achievement_awards.json"

# Test 9: Test with invalid category
log_test_info "Test 9: Test invalid category"
make_request "GET" "/awards/available?category=invalid_category" "" "Authorization: Bearer $TOKEN" "/tmp/invalid_category.json"
run_test "Invalid category" "422" "/tmp/invalid_category.json"

# Test 10: Test award progress (should work even without earned awards)
log_test_info "Test 10: Test award progress"
make_request "GET" "/awards/dashboard/progress" "" "Authorization: Bearer $TOKEN" "/tmp/progress.json"
run_test "Get award progress" "200" "/tmp/progress.json"

# Cleanup
cleanup_test_files

echo ""
echo "==========================================="
echo "Award Template Test Results"
echo "==========================================="
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