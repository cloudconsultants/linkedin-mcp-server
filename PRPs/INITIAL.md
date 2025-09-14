# Feature: Remove Playwright Dependency in Favor of Patchright

## Feature Description

This feature removes the redundant Playwright dependency from the LinkedIn MCP Server and uses only Patchright, which provides full Playwright API compatibility while offering superior stealth capabilities for web scraping.

## Background

Currently, the project has both `playwright>=1.53.0` and `patchright>=1.55.0` as dependencies, creating unnecessary duplication. Patchright is a fork of Playwright specifically designed for web scraping with enhanced anti-detection features, and it provides the complete Playwright API through its own implementation.

## Technical Analysis

### Current State
- **Dual Dependencies**: Both playwright and patchright installed (~600MB combined)
- **15 files** importing from `playwright.async_api`
- **1 file** importing from `playwright._impl._errors` for error handling
- Configuration already defaults to `use_patchright: bool = True`

### Dependency Usage Breakdown
```python
# Most common imports (15 files)
from playwright.async_api import Page, BrowserContext, Browser, Locator

# Error handling (1 file)
from playwright._impl._errors import Error, TimeoutError

# Actual runtime usage (stealth_manager.py)
from patchright.async_api import async_playwright  # Already using patchright
```

## Benefits

### 1. **Docker Image Size Reduction**
- **Current**: 1.68GB (runtime image)
- **Expected**: ~1.4GB (17% reduction)
- **Savings**: ~300MB from removing duplicate browser automation library

### 2. **Improved Stealth Capabilities**
- Patchright includes built-in stealth patches
- Better anti-detection for LinkedIn scraping
- Native support for Chrome channel (not just Chromium)

### 3. **Simplified Dependency Management**
- Single browser automation library
- Reduced attack surface
- Cleaner dependency tree
- Faster installation times

### 4. **Maintained Compatibility**
- Patchright provides full Playwright API
- No breaking changes to existing code
- Type hints remain compatible

## Implementation Approach

### Phase 1: Dependency Removal
- Remove `playwright>=1.53.0` from pyproject.toml
- Update all Docker build configurations
- Verify patchright provides all required APIs

### Phase 2: Import Updates
- No changes needed for `playwright.async_api` imports (Patchright provides these)
- Update error handling to use patchright error types
- Clean up fallback code paths

### Phase 3: Testing & Validation
- Verify all LinkedIn scraping tools work
- Test error handling scenarios
- Validate Docker image size reduction
- Run comprehensive integration tests

## Risk Assessment

### Low Risk Areas
- **API Compatibility**: Patchright is designed as drop-in replacement
- **Existing Usage**: Code already uses patchright by default
- **Type Compatibility**: Same type definitions available

### Medium Risk Areas
- **Error Types**: Internal error imports may need adjustment
- **Edge Cases**: Some Playwright-specific features might differ

### Mitigation Strategy
- Comprehensive testing before deployment
- Easy rollback by re-adding playwright dependency
- Gradual rollout with feature flag if needed

## Success Criteria

1. **Size Reduction**: Docker image reduced to ~1.4GB
2. **Functionality**: All LinkedIn scraping tools continue working
3. **Performance**: No degradation in scraping speed
4. **Reliability**: Error handling remains robust
5. **Stealth**: Improved anti-detection capabilities

## Files Affected

### Core Dependencies
- `pyproject.toml` - Remove playwright dependency
- `pyproject.*.toml` - Update all variant configurations
- `uv.lock` - Regenerate without playwright

### Code Files (15 total)
- `linkedin_mcp_server/error_handler.py` - Update error imports
- `linkedin_mcp_server/scraper/config.py` - No changes needed
- `linkedin_mcp_server/scraper/session.py` - No changes needed
- `linkedin_mcp_server/scraper/browser/stealth_manager.py` - Optional cleanup
- All scraper implementation files - No changes needed

### Docker & Build
- `Dockerfile.*` - Update all variants
- `validate_runtime.py` - Remove playwright validation

## Timeline Estimate

- **Analysis & Planning**: ✅ Complete
- **Implementation**: 2-3 hours
- **Testing**: 2-3 hours
- **Documentation**: 1 hour
- **Total**: ~6-8 hours

## Conclusion

Removing Playwright in favor of Patchright is a low-risk, high-reward optimization that will:
- Reduce Docker image size by ~300MB (17%)
- Improve stealth capabilities for LinkedIn scraping
- Simplify dependency management
- Maintain full API compatibility

The change aligns with the project's goal of creating optimized Docker images while improving the core scraping functionality through better anti-detection capabilities.
