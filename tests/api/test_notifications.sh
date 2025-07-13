#!/bin/bash

# Test award notification and dashboard endpoints

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

echo "Testing Award Notification and Dashboard Endpoints"
echo "================================================="

# Create test user and get token
log_test_info "Creating test user and getting auth token..."
TOKEN=$(setup_test_user "$USERNAME" "$PASSWORD")

if [[ -z "$TOKEN" ]]; then
    log_test_error "Failed to get auth token"
    exit 1
fi

# Test 1: Get dashboard stats
log_test_info "Test 1: Get dashboard stats"
make_request "GET" "/awards/dashboard/stats" "" "Authorization: Bearer $TOKEN" "/tmp/dashboard_stats.json"
run_test "Get dashboard stats" "200" "/tmp/dashboard_stats.json"

# Test 2: Get recent awards
log_test_info "Test 2: Get recent awards"
make_request "GET" "/awards/dashboard/recent" "" "Authorization: Bearer $TOKEN" "/tmp/recent_awards.json"
run_test "Get recent awards" "200" "/tmp/recent_awards.json"

# Test 3: Get recent awards with custom parameters
log_test_info "Test 3: Get recent awards with custom parameters"
make_request "GET" "/awards/dashboard/recent?days_back=14&limit=5" "" "Authorization: Bearer $TOKEN" "/tmp/recent_awards_custom.json"
run_test "Get recent awards with custom params" "200" "/tmp/recent_awards_custom.json"

# Test 4: Get award progress
log_test_info "Test 4: Get award progress"
make_request "GET" "/awards/dashboard/progress" "" "Authorization: Bearer $TOKEN" "/tmp/award_progress.json"
run_test "Get award progress" "200" "/tmp/award_progress.json"

# Test 5: Get award notifications
log_test_info "Test 5: Get award notifications"
make_request "GET" "/awards/notifications" "" "Authorization: Bearer $TOKEN" "/tmp/notifications.json"
run_test "Get award notifications" "200" "/tmp/notifications.json"

# Test 6: Get all notifications (including read)
log_test_info "Test 6: Get all notifications"
make_request "GET" "/awards/notifications?unread_only=false" "" "Authorization: Bearer $TOKEN" "/tmp/all_notifications.json"
run_test "Get all notifications" "200" "/tmp/all_notifications.json"

# Test 7: Mark notifications as read
log_test_info "Test 7: Mark notifications as read"
make_request "POST" "/awards/notifications/read" "[\"award_1\", \"award_2\"]" "Authorization: Bearer $TOKEN
Content-Type: application/json" "/tmp/mark_read.json"
run_test "Mark notifications as read" "200" "/tmp/mark_read.json"

# Test 8: Dashboard stats without authentication
log_test_info "Test 8: Dashboard stats without authentication"
make_request "GET" "/awards/dashboard/stats" "" "" "/tmp/unauth_dashboard.json"
run_test "Dashboard stats without auth" "401" "/tmp/unauth_dashboard.json"

# Test 9: Invalid days_back parameter
log_test_info "Test 9: Invalid days_back parameter"
make_request "GET" "/awards/dashboard/recent?days_back=50" "" "Authorization: Bearer $TOKEN" "/tmp/invalid_days.json"
run_test "Invalid days_back parameter" "422" "/tmp/invalid_days.json"

# Test 10: Invalid limit parameter
log_test_info "Test 10: Invalid limit parameter"
make_request "GET" "/awards/dashboard/recent?limit=100" "" "Authorization: Bearer $TOKEN" "/tmp/invalid_limit.json"
run_test "Invalid limit parameter" "422" "/tmp/invalid_limit.json"

# Cleanup
cleanup_test_files

echo ""
echo "================================================="
echo "Notification and Dashboard Test Results"
echo "================================================="
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