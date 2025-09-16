# Stealth Profile Configuration Guide

This guide explains how stealth profiles are configured and controlled throughout the LinkedIn MCP Server codebase.

## 🎯 Current Configuration Locations

### 1. MCP Tools (Hard-coded)
**Location**: `linkedin_mcp_server/tools/person.py`
```python
# Lines 49 & 143 - Currently HARD-CODED in both tools
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"
```

**Functions affected:**
- `get_person_profile_minimal()` - Fast basic profile extraction
- `get_person_profile()` - Comprehensive profile extraction

### 2. Test Scripts (Hard-coded)
**Location**: `tests/performance_validation/test_drihs_no_stealth.py`
```python
# Line 14 - Also HARD-CODED in test scripts
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"
```

**Other test files with hard-coded profiles:**
- `tests/performance_validation/validate_fixes.py`
- `tests/performance_validation/test_improved_extraction.py`
- `tests/performance_validation/test_fixes_with_cookie.py`
- `tests/performance_validation/test_timing_breakdown.py`

### 3. System Default Configuration (Environment-based)
**Location**: `linkedin_mcp_server/scraper/config.py`
```python
# Line 62 - System default when no environment variable is set
"stealth_profile": os.getenv("STEALTH_PROFILE", "MINIMAL_STEALTH")
```

**Other configuration options:**
```python
"use_new_stealth": os.getenv("USE_NEW_STEALTH", "false").lower() == "true"
"stealth_telemetry": os.getenv("STEALTH_TELEMETRY", "true").lower() == "true"
"stealth_config_path": os.getenv("STEALTH_CONFIG_PATH")
```

## 📊 Available Stealth Profiles

**Location**: `linkedin_mcp_server/scraper/stealth/profiles.py`

| Profile | Performance Target | Use Case | Description |
|---------|-------------------|----------|-------------|
| `NO_STEALTH` | 5-10 seconds | Development, Testing | Maximum speed, minimal stealth measures |
| `MINIMAL_STEALTH` | 60-90 seconds | Production | Balanced performance and stealth |
| `MODERATE_STEALTH` | 120-180 seconds | Moderate Risk | Enhanced stealth measures |
| `MAXIMUM_STEALTH` | 250-350 seconds | High Risk | Maximum stealth, all detection countermeasures |

### Profile Configuration Map
```python
profile_map = {
    "NO_STEALTH": StealthProfile.NO_STEALTH,
    "MINIMAL_STEALTH": StealthProfile.MINIMAL_STEALTH,
    "MODERATE_STEALTH": StealthProfile.MODERATE_STEALTH,
    "MAXIMUM_STEALTH": StealthProfile.MAXIMUM_STEALTH,
}
```

## 🔧 How to Change Stealth Profiles

### Option 1: Environment Variables (System-wide)
```bash
# Maximum performance (recommended for development)
export STEALTH_PROFILE=NO_STEALTH
export USE_NEW_STEALTH=true

# Balanced performance (recommended for production)
export STEALTH_PROFILE=MINIMAL_STEALTH
export USE_NEW_STEALTH=true

# Maximum stealth (high-risk environments)
export STEALTH_PROFILE=MAXIMUM_STEALTH
export USE_NEW_STEALTH=true
```

### Option 2: Docker Environment Variables
```bash
docker run -e STEALTH_PROFILE=MINIMAL_STEALTH \
           -e USE_NEW_STEALTH=true \
           linkedin-mcp-server
```

### Option 3: .env File
```bash
# Add to .env file in project root
STEALTH_PROFILE=MINIMAL_STEALTH
USE_NEW_STEALTH=true
```

## 🚨 Current Architecture Limitation

**Important**: Currently, both MCP tools (`get_person_profile` and `get_person_profile_minimal`) have **hard-coded** stealth profiles, which means they ignore environment variables and always use `NO_STEALTH`.

### Why MCP Tools and Test Scripts Behave Identically
Both use the same hard-coded configuration:
```python
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"
```

This explains why the MCP tools achieve the same ~8-10 second performance as test scripts.

## 🎯 Making MCP Tools Configurable (Future Enhancement)

To make MCP tools respect environment variables instead of being hard-coded:

### Step 1: Remove Hard-coded Configuration
**In `linkedin_mcp_server/tools/person.py`**, remove these lines:
```python
# REMOVE these hard-coded lines
os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
os.environ["USE_NEW_STEALTH"] = "true"
```

### Step 2: Let System Configuration Take Over
The system will automatically use:
1. Environment variable `STEALTH_PROFILE` if set
2. Default to `MINIMAL_STEALTH` if no environment variable exists
3. Respect `USE_NEW_STEALTH` environment variable

### Step 3: Configuration Examples After Enhancement
```bash
# Fast MCP tools (like current behavior)
STEALTH_PROFILE=NO_STEALTH uv run -m linkedin_mcp_server

# Balanced MCP tools
STEALTH_PROFILE=MINIMAL_STEALTH uv run -m linkedin_mcp_server

# Maximum stealth MCP tools
STEALTH_PROFILE=MAXIMUM_STEALTH uv run -m linkedin_mcp_server
```

## 🔍 Configuration Discovery

### Finding Current Profile
Check what profile is being used:
```python
import os
current_profile = os.getenv("STEALTH_PROFILE", "MINIMAL_STEALTH")
print(f"Current stealth profile: {current_profile}")
```

### Files That Read STEALTH_PROFILE
- `linkedin_mcp_server/scraper/config.py` - System configuration
- `linkedin_mcp_server/scraper/stealth/profiles.py` - Profile factory
- `linkedin_mcp_server/scraper/stealth/controller.py` - Stealth controller
- `linkedin_mcp_server/scraper/scrapers/person/get_person.py` - Legacy scraper
- Various test files in `tests/performance_validation/`

## 📈 Performance Implications

### Current MCP Tools Performance (NO_STEALTH)
- `get_person_profile_minimal`: ~8.3 seconds
- `get_person_profile`: ~9.7 seconds

### Expected Performance After Making Configurable
| Profile | Minimal Tool | Full Tool |
|---------|-------------|-----------|
| `NO_STEALTH` | ~8s | ~10s |
| `MINIMAL_STEALTH` | ~60s | ~90s |
| `MODERATE_STEALTH` | ~120s | ~180s |
| `MAXIMUM_STEALTH` | ~250s | ~350s |

## 🛠️ Troubleshooting

### Profile Not Taking Effect
1. Check if MCP tools have hard-coded profiles (current state)
2. Verify environment variable is set: `echo $STEALTH_PROFILE`
3. Ensure `USE_NEW_STEALTH=true` for v1.6.0 architecture
4. Check Docker environment variables if using containers

### Performance Issues
1. Verify you're using the intended profile
2. Check if timeouts are properly configured (1-2s selector timeouts)
3. Monitor performance telemetry with `STEALTH_TELEMETRY=true`

## 📚 Related Documentation
- `RELEASE_NOTES.md` - v1.6.0 centralized stealth architecture
- `PRPs/centralized_stealth_architecture_redesign_FINAL.md` - Technical implementation details
- `CLAUDE.md` - Development commands and performance optimization guides
