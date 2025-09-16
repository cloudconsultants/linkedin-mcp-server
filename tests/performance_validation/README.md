# Performance Validation Test Suite

This directory contains comprehensive performance tests for validating aggressive optimization targets in the LinkedIn MCP Server.

## Test Scripts Overview

### Core Performance Tests

#### `validate_fixes.py`
**Purpose**: Comprehensive validation script for testing extraction improvements
**Target**: Real LinkedIn profile (drihs) with field mapping accuracy validation
**Usage**:
```bash
cd tests/performance_validation
STEALTH_PROFILE=NO_STEALTH python validate_fixes.py
STEALTH_PROFILE=ULTRA_FAST_NO_STEALTH python validate_fixes.py
```
**Output**: Detailed timing breakdown + JSON results file

#### `test_timing_breakdown.py`
**Purpose**: Detailed timing analysis isolating performance bottlenecks
**Phases Measured**: Browser init → Cookie setup → Scraper creation → scrape_page() → Cleanup
**Usage**:
```bash
cd tests/performance_validation
STEALTH_PROFILE=NO_STEALTH python test_timing_breakdown.py
```
**Output**: Phase-by-phase timing breakdown with bottleneck identification

#### `test_improved_extraction.py`
**Purpose**: End-to-end extraction using official get_person_profile API
**Features**: Production authentication flow + complete pipeline testing
**Usage**:
```bash
cd tests/performance_validation
STEALTH_PROFILE=MINIMAL_STEALTH python test_improved_extraction.py
```
**Output**: Complete workflow timing with accuracy validation

#### `test_fixes_with_cookie.py`
**Purpose**: Authentication-focused timing test following production patterns
**Features**: Manual cookie authentication + detailed phase timing
**Usage**:
```bash
cd tests/performance_validation
python test_fixes_with_cookie.py
```
**Output**: Authentication → Browser → Navigation → Extraction timing

#### `test_drihs_no_stealth.py`
**Purpose**: Baseline NO_STEALTH profile performance measurement
**Features**: Direct browser control + cookie authentication
**Usage**:
```bash
cd tests/performance_validation
python test_drihs_no_stealth.py
```
**Output**: NO_STEALTH profile timing baseline

## Performance Targets

| Profile | Target Time | Test Script | Success Criteria |
|---------|-------------|-------------|------------------|
| ULTRA_FAST_NO_STEALTH | <2s | `validate_fixes.py` | Extraction + accuracy |
| NO_STEALTH | <3s | `test_timing_breakdown.py` | Phase breakdown |
| MINIMAL_STEALTH | <12s | `test_improved_extraction.py` | End-to-end pipeline |
| MAXIMUM_STEALTH | <35s | `validate_fixes.py` | Full stealth + accuracy |

## Running the Complete Test Suite

### Quick Performance Check
```bash
cd tests/performance_validation
./run_performance_suite.sh
```

### Individual Profile Testing
```bash
# Test specific profile optimization
STEALTH_PROFILE=ULTRA_FAST_NO_STEALTH python validate_fixes.py

# Compare before/after optimization
STEALTH_PROFILE=NO_STEALTH python test_timing_breakdown.py
STEALTH_PROFILE=ULTRA_FAST_NO_STEALTH python test_timing_breakdown.py
```

### Continuous Performance Monitoring
```bash
# Daily performance validation
./daily_performance_check.sh

# Generate performance report
python performance_report.py
```

## Expected Results

### Successful Optimization Indicators
- ✅ Extraction times meet or beat targets
- ✅ Field mapping accuracy maintained (>95%)
- ✅ No increase in LinkedIn detection/challenges
- ✅ Graceful degradation when optimizations fail

### Failure Patterns to Watch
- ❌ Extraction times exceed targets by >20%
- ❌ Field mapping accuracy drops below 90%
- ❌ Increased challenge/captcha rates
- ❌ Browser timeout failures

## Integration with Main Test Suite

These performance validation tests complement the main test suite in `tests/`:
- `tests/performance_validation/` - Performance-focused validation
- `tests/integration/` - Integration tests with timing fixes
- `tests/unit/` - Unit tests for individual components

Run all tests together:
```bash
# From project root
uv run pytest tests/ -v --durations=10
```
