#!/bin/bash
"""
Daily performance monitoring script for continuous validation.
Runs lightweight performance checks and alerts on regressions.
"""

echo "📅 Daily Performance Check - $(date)"
echo "=" * 50

# Quick performance check for each profile
declare -A TARGETS=(
    ["NO_STEALTH"]=3
    ["MINIMAL_STEALTH"]=12
    ["MAXIMUM_STEALTH"]=35
)

# Results storage
DATE=$(date +%Y%m%d)
LOG_FILE="daily_performance_${DATE}.log"

{
    echo "Daily Performance Check - $(date)"
    echo "=================================="
    echo
} > $LOG_FILE

# Function for quick timing test
quick_test() {
    local profile=$1
    local target=$2

    echo -n "Quick test $profile... "

    start_time=$(date +%s.%N)
    timeout 60s bash -c "STEALTH_PROFILE=$profile python validate_fixes.py" > /dev/null 2>&1
    exit_code=$?
    end_time=$(date +%s.%N)

    if [ $exit_code -eq 124 ]; then
        duration="TIMEOUT"
        status="❌ TIMEOUT"
    else
        duration=$(echo "$end_time - $start_time" | bc)
        if (( $(echo "$duration < $target" | bc -l) )); then
            status="✅ OK"
        else
            status="⚠️ SLOW"
        fi
    fi

    echo "$status (${duration}s)"
    echo "$profile: $status (${duration}s)" >> $LOG_FILE
}

# Run quick tests
for profile in "${!TARGETS[@]}"; do
    quick_test "$profile" "${TARGETS[$profile]}"
done

echo
echo "📊 System Health Check:"
echo "-" * 30

# Check for common issues
echo -n "Browser availability... "
if command -v google-chrome >/dev/null 2>&1; then
    echo "✅ Chrome found"
    echo "Chrome: ✅ Available" >> $LOG_FILE
else
    echo "❌ Chrome missing"
    echo "Chrome: ❌ Missing" >> $LOG_FILE
fi

echo -n "LinkedIn cookie... "
if [ -n "$LINKEDIN_COOKIE" ]; then
    echo "✅ Available"
    echo "Cookie: ✅ Available" >> $LOG_FILE
else
    echo "⚠️ Not set"
    echo "Cookie: ⚠️ Not set" >> $LOG_FILE
fi

echo -n "Python dependencies... "
if python -c "import patchright, linkedin_mcp_server" 2>/dev/null; then
    echo "✅ OK"
    echo "Dependencies: ✅ OK" >> $LOG_FILE
else
    echo "❌ Issues detected"
    echo "Dependencies: ❌ Issues" >> $LOG_FILE
fi

echo
echo "📁 Log saved to: $LOG_FILE"

# Alert on performance regressions (if previous log exists)
YESTERDAY=$(date -d "yesterday" +%Y%m%d)
YESTERDAY_LOG="daily_performance_${YESTERDAY}.log"

if [ -f "$YESTERDAY_LOG" ]; then
    echo
    echo "📈 Performance Trend Analysis:"
    echo "-" * 30

    # Simple regression detection
    python3 << EOF
import re
import sys

try:
    # Read today's results
    with open('$LOG_FILE', 'r') as f:
        today_data = f.read()

    # Read yesterday's results
    with open('$YESTERDAY_LOG', 'r') as f:
        yesterday_data = f.read()

    # Extract timings
    today_times = {}
    yesterday_times = {}

    for line in today_data.split('\n'):
        if ':' in line and ('OK' in line or 'SLOW' in line):
            parts = line.split(':')
            profile = parts[0].strip()
            time_match = re.search(r'\(([\d.]+)s\)', line)
            if time_match:
                today_times[profile] = float(time_match.group(1))

    for line in yesterday_data.split('\n'):
        if ':' in line and ('OK' in line or 'SLOW' in line):
            parts = line.split(':')
            profile = parts[0].strip()
            time_match = re.search(r'\(([\d.]+)s\)', line)
            if time_match:
                yesterday_times[profile] = float(time_match.group(1))

    # Compare and detect regressions
    regressions = []
    improvements = []

    for profile in today_times:
        if profile in yesterday_times:
            today_time = today_times[profile]
            yesterday_time = yesterday_times[profile]

            change_pct = ((today_time - yesterday_time) / yesterday_time) * 100

            if change_pct > 20:  # 20% slower
                regressions.append(f"{profile}: +{change_pct:.1f}% ({yesterday_time:.1f}s → {today_time:.1f}s)")
            elif change_pct < -10:  # 10% faster
                improvements.append(f"{profile}: {change_pct:.1f}% ({yesterday_time:.1f}s → {today_time:.1f}s)")

    if regressions:
        print("⚠️ Performance Regressions Detected:")
        for regression in regressions:
            print(f"   {regression}")

    if improvements:
        print("🚀 Performance Improvements:")
        for improvement in improvements:
            print(f"   {improvement}")

    if not regressions and not improvements:
        print("📊 Performance stable (no significant changes)")

except Exception as e:
    print(f"Unable to compare with yesterday: {e}")
EOF

fi

echo
echo "🏁 Daily check complete!"
