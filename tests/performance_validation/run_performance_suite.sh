#!/bin/bash
"""
Comprehensive performance validation suite runner.
Tests all optimization targets and generates performance report.
"""

echo "🚀 LinkedIn MCP Server - Performance Validation Suite"
echo "=" * 60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Performance targets
declare -A TARGETS=(
    ["ULTRA_FAST_NO_STEALTH"]=2
    ["NO_STEALTH"]=3
    ["MINIMAL_STEALTH"]=12
    ["MAXIMUM_STEALTH"]=35
)

# Test results storage
RESULTS_FILE="performance_results_$(date +%Y%m%d_%H%M%S).json"
echo "{\"test_run\": \"$(date)\", \"results\": [" > $RESULTS_FILE

echo "📊 Running performance validation tests..."
echo

# Function to run test and measure time
run_performance_test() {
    local profile=$1
    local script=$2
    local target=$3

    echo -n "Testing $profile (target: <${target}s)... "

    start_time=$(date +%s.%N)
    STEALTH_PROFILE=$profile python $script > /dev/null 2>&1
    exit_code=$?
    end_time=$(date +%s.%N)

    duration=$(echo "$end_time - $start_time" | bc)

    # Check if test passed and met timing target
    if [ $exit_code -eq 0 ] && (( $(echo "$duration < $target" | bc -l) )); then
        echo -e "${GREEN}✅ PASS${NC} (${duration}s)"
        status="PASS"
    elif [ $exit_code -eq 0 ]; then
        echo -e "${YELLOW}⚠️  SLOW${NC} (${duration}s > ${target}s)"
        status="SLOW"
    else
        echo -e "${RED}❌ FAIL${NC} (${duration}s)"
        status="FAIL"
    fi

    # Add result to JSON
    echo "    {\"profile\": \"$profile\", \"duration\": $duration, \"target\": $target, \"status\": \"$status\"}," >> $RESULTS_FILE

    return $exit_code
}

# Test each profile with appropriate script
echo "🎯 Phase 1: Core Performance Tests"
echo "-" * 40

run_performance_test "ULTRA_FAST_NO_STEALTH" "validate_fixes.py" 2
run_performance_test "NO_STEALTH" "test_timing_breakdown.py" 3
run_performance_test "MINIMAL_STEALTH" "test_improved_extraction.py" 12
run_performance_test "MAXIMUM_STEALTH" "validate_fixes.py" 35

echo
echo "🔍 Phase 2: Detailed Timing Analysis"
echo "-" * 40

# Run timing breakdown for bottleneck analysis
echo "Running detailed timing breakdown..."
for profile in NO_STEALTH MINIMAL_STEALTH MAXIMUM_STEALTH; do
    echo "  → $profile profile:"
    STEALTH_PROFILE=$profile python test_timing_breakdown.py 2>/dev/null | grep -E "(Browser init|scrape_page|TOTAL):" | sed 's/^/    /'
done

echo
echo "📋 Phase 3: Field Mapping Validation"
echo "-" * 40

# Test field mapping accuracy
echo "Validating extraction accuracy..."
STEALTH_PROFILE=NO_STEALTH python validate_fixes.py 2>/dev/null | grep -E "(✅|❌)" | head -10

# Finalize results JSON
echo "  ]}" >> $RESULTS_FILE

echo
echo "📊 Performance Summary:"
echo "-" * 40

# Generate summary
python3 << EOF
import json
import sys

try:
    with open('$RESULTS_FILE', 'r') as f:
        content = f.read().rstrip(',\n  ]}') + '\n  ]}'
        data = json.loads(content)

    results = data['results']
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['status'] == 'PASS')
    slow_tests = sum(1 for r in results if r['status'] == 'SLOW')
    failed_tests = sum(1 for r in results if r['status'] == 'FAIL')

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"⚠️  Slow: {slow_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")

    print("\nDetailed Results:")
    for result in results:
        status_emoji = {"PASS": "✅", "SLOW": "⚠️", "FAIL": "❌"}[result['status']]
        print(f"  {status_emoji} {result['profile']}: {result['duration']:.2f}s (target: <{result['target']}s)")

except Exception as e:
    print(f"Error generating summary: {e}")
    sys.exit(1)
EOF

echo
echo "📁 Results saved to: $RESULTS_FILE"
echo "🏁 Performance validation complete!"
