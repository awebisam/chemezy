#!/bin/bash

# Test performance optimizations and caching

source tests/helpers/test_helpers.sh

# Test variables
USERNAME="perf_user"
PASSWORD="perf_password"

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

time_request() {
    local endpoint="$1"
    local auth_header="$2"
    local response_file="$3"
    
    local start_time=$(date +%s%3N)
    make_request "GET" "$endpoint" "" "$auth_header" "$response_file"
    local end_time=$(date +%s%3N)
    
    local duration=$((end_time - start_time))
    echo "$duration"
}

echo "Testing Performance Optimizations"
echo "================================="

# Create test user and get token
log_test_info "Creating test user and getting auth token..."
TOKEN=$(setup_test_user "$USERNAME" "$PASSWORD")

if [[ -z "$TOKEN" ]]; then
    log_test_error "Failed to get auth token"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# Test 1: Basic leaderboard performance
log_test_info "Test 1: Basic leaderboard performance"
duration1=$(time_request "/awards/leaderboard/discovery" "$AUTH_HEADER" "/tmp/perf_test1.json")
run_test "Basic leaderboard request" "200" "/tmp/perf_test1.json"
echo "  First request duration: ${duration1}ms"

# Test 2: Cached leaderboard performance (should be faster)
log_test_info "Test 2: Cached leaderboard performance"
duration2=$(time_request "/awards/leaderboard/discovery" "$AUTH_HEADER" "/tmp/perf_test2.json")
run_test "Cached leaderboard request" "200" "/tmp/perf_test2.json"
echo "  Second request duration: ${duration2}ms"

# Test 3: Overall leaderboard performance
log_test_info "Test 3: Overall leaderboard performance"
duration3=$(time_request "/awards/leaderboard/overall" "$AUTH_HEADER" "/tmp/perf_test3.json")
run_test "Overall leaderboard request" "200" "/tmp/perf_test3.json"
echo "  Overall leaderboard duration: ${duration3}ms"

# Test 4: Dashboard stats performance
log_test_info "Test 4: Dashboard stats performance"
duration4=$(time_request "/awards/dashboard/stats" "$AUTH_HEADER" "/tmp/perf_test4.json")
run_test "Dashboard stats request" "200" "/tmp/perf_test4.json"
echo "  Dashboard stats duration: ${duration4}ms"

# Test 5: Award progress performance
log_test_info "Test 5: Award progress performance"
duration5=$(time_request "/awards/dashboard/progress" "$AUTH_HEADER" "/tmp/perf_test5.json")
run_test "Award progress request" "200" "/tmp/perf_test5.json"
echo "  Award progress duration: ${duration5}ms"

# Test 6: Recent awards performance
log_test_info "Test 6: Recent awards performance"
duration6=$(time_request "/awards/dashboard/recent" "$AUTH_HEADER" "/tmp/perf_test6.json")
run_test "Recent awards request" "200" "/tmp/perf_test6.json"
echo "  Recent awards duration: ${duration6}ms"

# Test 7: User rank performance
log_test_info "Test 7: User rank performance"
duration7=$(time_request "/awards/leaderboard/my-rank" "$AUTH_HEADER" "/tmp/perf_test7.json")
run_test "User rank request" "200" "/tmp/perf_test7.json"
echo "  User rank duration: ${duration7}ms"

# Test 8: Available awards performance
log_test_info "Test 8: Available awards performance"
duration8=$(time_request "/awards/available" "$AUTH_HEADER" "/tmp/perf_test8.json")
run_test "Available awards request" "200" "/tmp/perf_test8.json"
echo "  Available awards duration: ${duration8}ms"

# Test 9: Notifications performance
log_test_info "Test 9: Notifications performance"
duration9=$(time_request "/awards/notifications" "$AUTH_HEADER" "/tmp/perf_test9.json")
run_test "Notifications request" "200" "/tmp/perf_test9.json"
echo "  Notifications duration: ${duration9}ms"

# Test 10: Community statistics performance
log_test_info "Test 10: Community statistics performance"
duration10=$(time_request "/awards/community/statistics" "$AUTH_HEADER" "/tmp/perf_test10.json")
run_test "Community statistics request" "200" "/tmp/perf_test10.json"
echo "  Community statistics duration: ${duration10}ms"

# Performance analysis
echo ""
echo "Performance Analysis:"
echo "===================="
echo "Leaderboard first request: ${duration1}ms"
echo "Leaderboard second request (cached): ${duration2}ms"

if [[ $duration1 -gt 0 && $duration2 -gt 0 ]]; then
    if [[ $duration2 -lt $duration1 ]]; then
        improvement=$(( (duration1 - duration2) * 100 / duration1 ))
        echo "Cache improvement: ${improvement}%"
    fi
fi

echo "Overall leaderboard: ${duration3}ms"
echo "Dashboard stats: ${duration4}ms"
echo "Award progress: ${duration5}ms"
echo "Recent awards: ${duration6}ms"
echo "User rank: ${duration7}ms"
echo "Available awards: ${duration8}ms"
echo "Notifications: ${duration9}ms"
echo "Community statistics: ${duration10}ms"

# Check for response content
echo ""
echo "Response Content Checks:"
echo "======================"

# Check if leaderboard has proper structure
if [[ -f "/tmp/perf_test1.json" ]]; then
    if grep -q "rank" "/tmp/perf_test1.json"; then
        echo "✓ Leaderboard response has rank field"
    else
        echo "✗ Leaderboard response missing rank field"
    fi
fi

# Check if dashboard stats has proper structure
if [[ -f "/tmp/perf_test4.json" ]]; then
    if grep -q "dashboard_stats" "/tmp/perf_test4.json"; then
        echo "✓ Dashboard stats response has proper structure"
    else
        echo "✗ Dashboard stats response missing structure"
    fi
fi

# Cleanup
cleanup_test_files

echo ""
echo "================================="
echo "Performance Test Results"
echo "================================="
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