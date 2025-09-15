# LinkedIn MCP Server - Centralized Stealth Architecture Redesign PRP

## Goal

Transform the current scattered, slow LinkedIn stealth system into a high-performance, centralized architecture that:
- **Achieves 75-85% speed improvement** (300s → 50-75s for profile scraping)
- **Centralizes stealth control** into a single configurable system
- **Enables multi-content support** for profiles, jobs, companies, and feeds
- **Provides intelligent content detection** replacing hardcoded waits
- **Maintains backward compatibility** during migration

## Why

### Business Value and User Impact
- **Production Viability**: Current 5-minute scraping times make the system unusable for real applications
- **Cost Efficiency**: 85% speed improvement = 85% reduction in computational resources
- **Scalability**: Enables support for jobs, companies, feeds beyond just profiles
- **Developer Experience**: Single configuration point for easy speed vs stealth tuning
- **Competitive Advantage**: Fast, reliable LinkedIn data extraction for AI applications

### Integration with Existing Features
- **MCP Tool Compatibility**: All existing `get_person_profile` functionality preserved
- **Data Model Consistency**: Maintains exact output format compatibility
- **Session Management**: Integrates with existing Patchright session infrastructure
- **Authentication Flow**: No changes to LinkedIn cookie/keychain authentication

### Problems This Solves
- **Performance Crisis**: 300-second scraping times are unacceptable for production use
- **Scattered Architecture**: 150+ stealth calls across 13 files with no central control
- **Section-Based Inefficiency**: Same DOM parsed multiple times with redundant stealth operations
- **Fixed Waits**: Hardcoded delays instead of intelligent content detection
- **Limited Scalability**: Profile-only system cannot extend to other LinkedIn content types

## What

### User-Visible Behavior
```python
# NO CHANGES to existing MCP tool interfaces
result = await get_person_profile("username")  # Same API, 75% faster

# NEW: Configurable speed vs stealth via environment variables
export STEALTH_PROFILE=NO_STEALTH        # 50s, maximum speed
export STEALTH_PROFILE=MINIMAL_STEALTH   # 75s, good balance  
export STEALTH_PROFILE=MAXIMUM_STEALTH   # 295s, current system

# NEW: Support for additional LinkedIn content (future)
await get_job_details("123456789")       # Jobs support
await get_company_profile("company")     # Company support
```

### Technical Requirements
1. **Central StealthController**: Single point of control for all LinkedIn automation
2. **Page-Based Architecture**: One stealth operation per page, not per section
3. **Intelligent Content Loading**: Smart detection replacing hardcoded waits
4. **Multi-Content Framework**: Extensible to jobs, companies, feeds
5. **Performance Telemetry**: Built-in monitoring and optimization feedback
6. **Backward Compatibility**: Zero breaking changes during migration

### Success Criteria
- [ ] **75% speed improvement** with MINIMAL_STEALTH profile (300s → 75s)
- [ ] **85% speed improvement** with NO_STEALTH profile (300s → 50s) 
- [ ] **Zero data quality regression** (>95% field completeness maintained)
- [ ] **Single configuration point** for all stealth behavior
- [ ] **Multi-content support** framework ready for jobs/companies
- [ ] **Full backward compatibility** with existing MCP tools

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Critical for implementation
- url: https://github.com/kaliiiiiiiiii-vinyzu/patchright-python
  why: Advanced Patchright stealth features and isolated execution contexts
  critical: Runtime.enable leak prevention, proper fingerprint masking
  
- url: https://github.com/vinyzu/botright  
  why: Configuration-based stealth levels and performance optimization patterns
  critical: mask_fingerprint settings, headless stealth configuration
  
- url: https://github.com/rebrowser/rebrowser-patches
  why: Environment variable configuration patterns for stealth systems
  critical: REBROWSER_PATCHES_* environment variable approaches

- file: linkedin_mcp_server/scraper/browser/behavioral.py
  why: Current stealth implementation - contains core functions to centralize
  critical: navigate_to_profile_stealthily, simulate_comprehensive_scrolling patterns

- file: linkedin_mcp_server/scraper/scrapers/person/get_person.py  
  why: Main orchestration logic showing scattered stealth calls
  critical: Current performance bottlenecks and redundant operations

- file: linkedin_mcp_server/scraper/config.py
  why: Current StealthConfig and PersonScrapingFields - foundation to build on
  critical: Existing delay ranges and rate limiting configuration

- file: linkedin_mcp_server/session/manager.py
  why: Patchright session management - integration point for new stealth system
  critical: PlaywrightSessionManager.get_or_create_session() integration
```

### Current Codebase Structure

```bash
linkedin-mcp-server/
├── linkedin_mcp_server/
│   ├── tools/                          # MCP tool interfaces
│   │   ├── person.py                   # get_person_profile* tools
│   │   ├── company.py                  # Future company tools
│   │   └── job.py                      # Future job tools
│   ├── scraper/
│   │   ├── browser/
│   │   │   ├── behavioral.py           # CORE STEALTH FUNCTIONS (38 calls)
│   │   │   ├── stealth_manager.py      # Browser fingerprint protection
│   │   │   └── context.py              # Session management
│   │   ├── scrapers/
│   │   │   └── person/
│   │   │       ├── get_person.py       # MAIN ORCHESTRATOR (24 calls)
│   │   │       ├── experience.py       # Section scraper (stealth calls)
│   │   │       ├── education.py        # Section scraper (stealth calls)
│   │   │       ├── contacts.py         # Section scraper (stealth calls)
│   │   │       ├── interests.py        # Section scraper (stealth calls)
│   │   │       └── accomplishments.py  # Section scraper (stealth calls)
│   │   ├── config.py                   # Current StealthConfig
│   │   └── session.py                  # Session configuration
│   ├── session/
│   │   └── manager.py                  # Patchright session manager
│   └── server.py                       # FastMCP server
```

### Desired Codebase Structure

```bash
linkedin-mcp-server/
├── linkedin_mcp_server/
│   ├── scraper/
│   │   ├── stealth/                    # NEW: Centralized stealth module
│   │   │   ├── __init__.py
│   │   │   ├── controller.py           # StealthController main class
│   │   │   ├── profiles.py             # StealthProfile configurations
│   │   │   ├── lazy_loading.py         # LazyLoadDetector - intelligent content loading
│   │   │   ├── navigation.py           # NavigationStrategy - smart navigation
│   │   │   ├── simulation.py           # InteractionSimulator - behavior patterns
│   │   │   ├── telemetry.py            # PerformanceTelemetry - monitoring
│   │   │   └── hooks.py                # Decorator system for clean integration
│   │   ├── pages/                      # NEW: Page-based scrapers
│   │   │   ├── __init__.py
│   │   │   ├── profile_page.py         # Unified profile scraper (replaces 6 section files)
│   │   │   ├── job_page.py             # Future job page scraper
│   │   │   ├── company_page.py         # Future company page scraper
│   │   │   └── base.py                 # LinkedInPageScraper base class
│   │   ├── extractors/                 # NEW: Shared extraction utilities
│   │   │   ├── profile_extractors.py   # Profile field extraction
│   │   │   ├── job_extractors.py       # Job field extraction
│   │   │   └── common_extractors.py    # Shared patterns
│   │   └── browser/                    # MODIFIED: Stealth functions moved to stealth/
│   │       ├── behavioral.py           # LEGACY: Wrapper functions for compatibility
│   │       ├── stealth_manager.py      # Browser fingerprint (unchanged)
│   │       └── context.py              # Session management (unchanged)
```

### Known Gotchas & Library Quirks

```python
# CRITICAL: Patchright anti-detection requirements
# - MUST use channel="chrome" for maximum stealth
# - MUST avoid custom user agents (breaks fingerprinting)
# - MUST use isolated_context=True for evaluate() calls
playwright.chromium.launch_persistent_context(
    channel="chrome",          # REQUIRED for stealth
    headless=True,             # Production requirement
    no_viewport=True,          # Natural viewport behavior
    # do NOT add custom browser headers or user_agent
)

# CRITICAL: LinkedIn lazy loading detection
# - Content appears dynamically based on scroll position
# - DOM mutation observers needed, not just timeout waits
# - section.scroll_into_view_if_needed() triggers loading
# - Multiple scroll patterns needed for different content types

# CRITICAL: Current system bottlenecks
# - navigate_to_profile_stealthily: 45s (search-first pattern)
# - simulate_comprehensive_scrolling: 15s x 3 calls = 45s total
# - Section-based approach: Same DOM, multiple stealth operations
# - Fixed waits: page.wait_for_timeout(2000) throughout codebase

# GOTCHA: LinkedIn detection patterns
# - Rate limiting: Max 1 profile per minute in current config
# - Challenge detection: URL patterns, element selectors change
# - Session invalidation: After ~5 profiles (current threshold)
# - Navigation patterns: Direct URLs more detectable than search-first

# GOTCHA: Pydantic model integration
# - Person model expects specific field formats
# - Experience.institution_name maps to company in tool output
# - Date parsing must handle LinkedIn's various formats
# - Skills lists need proper extraction from text content
```

## Implementation Blueprint

### Data Models and Structure

```python
# NEW: Stealth configuration system
@dataclass
class StealthProfile:
    """Configurable stealth behavior profiles"""
    name: str
    navigation: NavigationMode  # DIRECT, SEARCH_FIRST
    delays: DelayConfig        # Timing configurations
    simulation: SimulationLevel # NONE, BASIC, MODERATE, COMPREHENSIVE
    lazy_loading: bool = True  # Always use intelligent loading
    telemetry: bool = True     # Performance monitoring

class NavigationMode(Enum):
    DIRECT = "direct"           # Fast: Direct URL navigation
    SEARCH_FIRST = "search"     # Slow: Search-first navigation (current)

class SimulationLevel(Enum):
    NONE = "none"              # No behavior simulation
    BASIC = "basic"            # Minimal scrolling
    MODERATE = "moderate"       # Some interaction patterns
    COMPREHENSIVE = "comprehensive"  # Full behavior simulation (current)

@dataclass  
class DelayConfig:
    """Centralized delay configurations"""
    base: Tuple[float, float]      # Random base delays
    reading: Tuple[float, float]   # Content reading delays
    navigation: Tuple[float, float] # Navigation delays

# NEW: Content loading system
class ContentTarget(Enum):
    """Content sections with intelligent loading"""
    # Profile targets
    BASIC_INFO = "basic_info"
    EXPERIENCE = "experience" 
    EDUCATION = "education"
    SKILLS = "skills"
    ACCOMPLISHMENTS = "accomplishments"
    CONTACTS = "contacts"
    
    # Future: Job targets
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    
    # Future: Company targets  
    COMPANY_OVERVIEW = "company_overview"
    EMPLOYEES = "employees"

class PageType(Enum):
    """LinkedIn page types with specific behaviors"""
    PROFILE = "profile"
    JOB_LISTING = "job"
    COMPANY_PAGE = "company"
    FEED = "feed"
```

### Task List (Implementation Order)

```yaml
Task 1: CREATE stealth module foundation
  - CREATE linkedin_mcp_server/scraper/stealth/__init__.py
  - CREATE linkedin_mcp_server/scraper/stealth/profiles.py
    - IMPLEMENT StealthProfile with predefined configurations
    - IMPLEMENT NO_STEALTH, MINIMAL_STEALTH, MODERATE_STEALTH, MAXIMUM_STEALTH
  - CREATE linkedin_mcp_server/scraper/stealth/controller.py
    - IMPLEMENT StealthController main class skeleton
    - IMPLEMENT configuration loading from environment variables

Task 2: IMPLEMENT intelligent content loading
  - CREATE linkedin_mcp_server/scraper/stealth/lazy_loading.py
    - IMPLEMENT LazyLoadDetector class
    - IMPLEMENT ensure_content_loaded() with DOM mutation detection
    - IMPLEMENT content-specific selectors mapping
    - REPLACE hardcoded page.wait_for_timeout() calls

Task 3: IMPLEMENT navigation strategies  
  - CREATE linkedin_mcp_server/scraper/stealth/navigation.py
    - IMPLEMENT NavigationStrategy class
    - IMPLEMENT direct navigation (fast path)
    - IMPLEMENT search-first navigation (current approach)
    - INTEGRATE with StealthController

Task 4: IMPLEMENT interaction simulation
  - CREATE linkedin_mcp_server/scraper/stealth/simulation.py
    - IMPLEMENT InteractionSimulator class
    - MIGRATE simulation logic from behavioral.py
    - IMPLEMENT configurable simulation levels
    - OPTIMIZE comprehensive scrolling patterns

Task 5: CREATE unified page scrapers
  - CREATE linkedin_mcp_server/scraper/pages/base.py
    - IMPLEMENT LinkedInPageScraper abstract base class
    - IMPLEMENT common page preparation patterns
  - CREATE linkedin_mcp_server/scraper/pages/profile_page.py
    - IMPLEMENT ProfilePageScraper using centralized stealth
    - CONSOLIDATE all section extraction logic
    - IMPLEMENT single stealth pass + parallel extraction
    - REPLACE section-based approach

Task 6: IMPLEMENT performance telemetry
  - CREATE linkedin_mcp_server/scraper/stealth/telemetry.py
    - IMPLEMENT PerformanceTelemetry class
    - IMPLEMENT timing and success rate tracking
    - IMPLEMENT stealth profile optimization suggestions
    - INTEGRATE with StealthController

Task 7: IMPLEMENT decorator system
  - CREATE linkedin_mcp_server/scraper/stealth/hooks.py
    - IMPLEMENT @stealth_controlled decorator
    - IMPLEMENT @lazy_load_aware decorator
    - ENABLE clean integration without code duplication

Task 8: MIGRATE PersonScraper integration
  - MODIFY linkedin_mcp_server/scraper/scrapers/person/get_person.py
    - REPLACE scattered stealth calls with StealthController
    - IMPLEMENT feature flag for A/B testing (USE_NEW_STEALTH env var)
    - MAINTAIN backward compatibility
    - INTEGRATE with ProfilePageScraper

Task 9: UPDATE configuration system
  - MODIFY linkedin_mcp_server/scraper/config.py
    - EXTEND StealthConfig with new profile system
    - IMPLEMENT environment variable loading
    - MAINTAIN compatibility with existing settings
  - CREATE stealth_config.json for profile definitions

Task 10: IMPLEMENT MCP tool updates
  - MODIFY linkedin_mcp_server/tools/person.py
    - INTEGRATE new stealth system
    - MAINTAIN exact output format compatibility
    - ADD performance logging and telemetry
    - IMPLEMENT graceful fallback to legacy system

Task 11: CREATE validation and testing
  - CREATE tests/unit/stealth/
    - IMPLEMENT unit tests for all stealth components
    - IMPLEMENT performance benchmark tests
    - IMPLEMENT A/B comparison tests
  - CREATE benchmark_stealth_performance.py
    - IMPLEMENT side-by-side performance testing
    - IMPLEMENT data completeness validation
    - IMPLEMENT detection rate monitoring

Task 12: IMPLEMENT legacy compatibility layer
  - MODIFY linkedin_mcp_server/scraper/browser/behavioral.py
    - IMPLEMENT wrapper functions for legacy compatibility
    - ROUTE calls to new StealthController
    - ENABLE gradual migration
    - PRESERVE exact function signatures
```

### Pseudocode for Critical Components

```python
# Task 5: ProfilePageScraper - Core architectural change
class ProfilePageScraper(LinkedInPageScraper):
    """Unified LinkedIn profile page extraction with single stealth pass"""
    
    async def scrape_profile_page(
        self, 
        page: Page, 
        url: str, 
        fields: PersonScrapingFields
    ) -> Person:
        """Extract all profile data with single stealth operation"""
        
        # Phase 1: Single stealth navigation and behavior simulation
        await self.stealth_controller.navigate_and_prepare_page(page, url)
        
        # Phase 2: Comprehensive content loading (once for entire page)  
        await self.stealth_controller.ensure_all_content_loaded(page, self._get_targets(fields))
        
        # Phase 3: Parallel section extraction (no additional stealth needed)
        extraction_tasks = []
        if PersonScrapingFields.BASIC_INFO in fields:
            extraction_tasks.append(self._extract_basic_info(page))
        if PersonScrapingFields.EXPERIENCE in fields:
            extraction_tasks.append(self._extract_experiences(page))
        # ... other sections
        
        # Execute all extractions in parallel (DOM is already loaded)
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)
        
        # Phase 4: Combine results into Person model
        return self._build_person_model(results)

# Task 2: LazyLoadDetector - Intelligent content loading
class LazyLoadDetector:
    """Smart content loading detection replacing hardcoded waits"""
    
    async def ensure_content_loaded(
        self,
        page: Page,
        targets: List[ContentTarget],
        max_wait_time: int = 30
    ) -> ContentLoadResult:
        """Intelligently load content instead of blind waiting"""
        
        start_time = time.time()
        loaded_targets = set()
        
        # Phase 1: Check what's already loaded
        for target in targets:
            if await self._is_content_loaded(page, target):
                loaded_targets.add(target)
        
        if len(loaded_targets) == len(targets):
            return ContentLoadResult(success=True, load_time=0)
        
        # Phase 2: Smart scrolling to trigger lazy loading
        missing_targets = [t for t in targets if t not in loaded_targets]
        scroll_strategy = self._get_scroll_strategy(missing_targets)
        
        await self._execute_scroll_strategy(page, scroll_strategy)
        
        # Phase 3: Monitor for content appearance with DOM mutation detection
        while (time.time() - start_time) < max_wait_time:
            newly_loaded = []
            for target in missing_targets:
                if await self._is_content_loaded(page, target):
                    newly_loaded.append(target)
                    loaded_targets.add(target)
            
            for target in newly_loaded:
                missing_targets.remove(target)
            
            if not missing_targets:
                break
                
            await asyncio.sleep(0.5)  # Brief check interval
        
        return ContentLoadResult(
            success=len(loaded_targets) == len(targets),
            loaded_targets=list(loaded_targets),
            missing_targets=missing_targets,
            load_time=time.time() - start_time
        )

# Task 1: StealthController - Central control system
class StealthController:
    """Central control system for all LinkedIn scraping stealth operations"""
    
    def __init__(self, profile: StealthProfile, telemetry: bool = True):
        self.profile = profile
        self.lazy_detector = LazyLoadDetector()
        self.navigator = NavigationStrategy(profile.navigation)
        self.simulator = InteractionSimulator(profile.simulation)
        self.telemetry = PerformanceTelemetry() if telemetry else None
    
    async def scrape_linkedin_page(
        self,
        page: Page,
        url: str,
        page_type: PageType,
        content_targets: List[ContentTarget]
    ) -> ScrapingResult:
        """Universal LinkedIn page scraping with centralized stealth control"""
        
        start_time = time.time()
        
        try:
            # Phase 1: Navigation (context-aware)
            await self.navigator.navigate_to_page(page, url, page_type)
            
            # Phase 2: Content Loading (intelligent)
            load_result = await self.lazy_detector.ensure_content_loaded(page, content_targets)
            if not load_result.success:
                logger.warning(f"Content loading incomplete: {load_result.missing_targets}")
            
            # Phase 3: Interaction Simulation (configurable)
            await self.simulator.simulate_page_interaction(page, page_type)
            
            # Phase 4: Data Extraction (delegated to specific scrapers)
            result = await self._extract_page_data(page, page_type, content_targets)
            
            # Phase 5: Performance tracking
            if self.telemetry:
                duration = time.time() - start_time
                await self.telemetry.record_success(url, duration, self.profile.name)
            
            return result
            
        except LinkedInDetectionError as e:
            if self.telemetry:
                await self.telemetry.record_detection(url, str(e))
            raise
```

### Integration Points

```yaml
CONFIGURATION:
  - add to: linkedin_mcp_server/scraper/config.py
  - pattern: "STEALTH_PROFILE = os.getenv('STEALTH_PROFILE', 'MINIMAL_STEALTH')"
  - integrate: StealthController.from_config() factory method

SESSION_MANAGEMENT:
  - modify: linkedin_mcp_server/session/manager.py
  - integrate: StealthController with PlaywrightSessionManager
  - pattern: "await session.set_stealth_controller(controller)"

MCP_TOOLS:
  - modify: linkedin_mcp_server/tools/person.py
  - integrate: New stealth system with existing tool interfaces
  - preserve: Exact output format compatibility
  - add: Performance telemetry logging

ENVIRONMENT_VARIABLES:
  - add: STEALTH_PROFILE (NO_STEALTH, MINIMAL_STEALTH, MODERATE_STEALTH, MAXIMUM_STEALTH)
  - add: USE_NEW_STEALTH (true/false for A/B testing)
  - add: STEALTH_TELEMETRY (true/false for performance monitoring)
  - add: STEALTH_CONFIG_PATH (custom config file location)
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check linkedin_mcp_server/scraper/stealth/ --fix
uv run ruff format linkedin_mcp_server/scraper/stealth/
uv run ty check linkedin_mcp_server/scraper/stealth/

# Expected: No errors. If errors, READ the error message and fix.
# CRITICAL: All type hints must be correct for Pydantic integration
```

### Level 2: Unit Tests

```python
# CREATE tests/unit/stealth/ with these test patterns:

def test_stealth_controller_no_stealth_mode():
    """NO_STEALTH profile achieves target performance"""
    controller = StealthController(StealthProfile.NO_STEALTH())
    start_time = time.time()
    
    result = await controller.scrape_linkedin_page(
        page, profile_url, PageType.PROFILE, [ContentTarget.BASIC_INFO]
    )
    
    duration = time.time() - start_time
    assert duration < 10  # Target: <10s for basic info
    assert result.success
    assert result.data_completeness > 0.95

def test_lazy_load_detector_content_detection():
    """LazyLoadDetector properly detects loaded content"""
    detector = LazyLoadDetector()
    
    # Mock page with content already loaded
    result = await detector.ensure_content_loaded(
        mock_page, [ContentTarget.EXPERIENCE], max_wait_time=5
    )
    
    assert result.success
    assert ContentTarget.EXPERIENCE in result.loaded_targets
    assert result.load_time < 1  # Should detect immediately

def test_performance_regression_prevention():
    """New system maintains data quality vs legacy"""
    legacy_result = await legacy_person_scraper.scrape_profile(url)
    new_result = await new_profile_page_scraper.scrape_profile_page(url, fields)
    
    # Data completeness comparison
    assert len(new_result.experiences) >= len(legacy_result.experiences) * 0.95
    assert len(new_result.educations) >= len(legacy_result.educations) * 0.95
    
    # Critical fields preservation
    assert new_result.name == legacy_result.name
    assert new_result.headline == legacy_result.headline

def test_stealth_profile_switching():
    """Environment variable profile switching works"""
    os.environ["STEALTH_PROFILE"] = "NO_STEALTH"
    controller = StealthController.from_config()
    assert controller.profile.name == "NO_STEALTH"
    assert controller.profile.simulation == SimulationLevel.NONE
```

```bash
# Run and iterate until passing:
uv run pytest tests/unit/stealth/ -v
uv run pytest tests/integration/test_stealth_performance.py -v

# If failing: Read error, understand root cause, fix code, re-run
# NEVER mock to make tests pass - fix the actual implementation
```

### Level 3: Performance Benchmarks

```bash
# Performance comparison testing
uv run python benchmark_stealth_performance.py \
  --profiles NO_STEALTH,MINIMAL_STEALTH,MAXIMUM_STEALTH \
  --urls "linkedin.com/in/testuser1,linkedin.com/in/testuser2" \
  --iterations 3

# Expected output:
# NO_STEALTH:      50s avg (83% improvement)
# MINIMAL_STEALTH: 75s avg (75% improvement) 
# MAXIMUM_STEALTH: 295s avg (baseline)

# Data completeness validation
uv run python validate_data_completeness.py \
  --compare-with-legacy \
  --target-completeness 0.95

# Expected: >95% field completeness vs legacy system
```

### Level 4: Integration Testing

```bash
# Start server with new stealth system
export STEALTH_PROFILE=MINIMAL_STEALTH
export USE_NEW_STEALTH=true
uv run -m linkedin_mcp_server --no-headless

# Test MCP tool compatibility
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_person_profile",
      "arguments": {"linkedin_username": "testuser"}
    }
  }'

# Expected: Same output format, 75% faster execution
# Monitor logs for performance telemetry data
```

## Final Validation Checklist

- [ ] **Performance targets achieved**: 75% speed improvement with MINIMAL_STEALTH
- [ ] **Data quality maintained**: >95% field completeness vs legacy
- [ ] **All tests pass**: `uv run pytest tests/ -v`
- [ ] **No linting errors**: `uv run ruff check linkedin_mcp_server/`
- [ ] **No type errors**: `uv run ty check linkedin_mcp_server/`
- [ ] **MCP tool compatibility**: Exact output format preserved
- [ ] **Environment variable configuration**: Profile switching works
- [ ] **A/B testing capability**: USE_NEW_STEALTH flag enables gradual rollout
- [ ] **Performance telemetry**: Monitoring and optimization feedback working
- [ ] **Backward compatibility**: Legacy system fallback functional
- [ ] **Documentation updated**: CLAUDE.md reflects new stealth commands

---

## Anti-Patterns to Avoid

- ❌ **Don't skip performance benchmarking** - validate every optimization claim
- ❌ **Don't break MCP tool interfaces** - maintain exact compatibility
- ❌ **Don't remove legacy system immediately** - enable gradual migration
- ❌ **Don't ignore data completeness** - speed improvements must preserve data quality  
- ❌ **Don't hardcode stealth settings** - everything must be configurable
- ❌ **Don't use synchronous operations** - all stealth must be async/await
- ❌ **Don't modify Patchright internals** - work within the provided API
- ❌ **Don't disable telemetry in production** - performance monitoring is critical
- ❌ **Don't implement without validation loops** - test each component thoroughly
- ❌ **Don't optimize prematurely** - profile first, then optimize based on data

---

## Success Metrics & Expected Outcomes

### Performance Improvements
```yaml
Profile Scraping Speed:
  Current Baseline: 295 seconds
  MINIMAL_STEALTH Target: 75 seconds (75% improvement)
  NO_STEALTH Target: 50 seconds (83% improvement)
  
Speed Breakdown Improvement:
  Navigation: 45s → 5s (89% improvement)
  Content Loading: 30s → 12s (60% improvement)  
  Section Extraction: 160s → 25s (84% improvement)
  Random Delays: 65s → 8s (88% improvement)

Scalability Gains:
  Job Scraping: N/A → 30-45s (new capability)
  Company Scraping: N/A → 40-60s (new capability)
  Multi-content Sessions: N/A → Enabled (new capability)
```

### Architectural Benefits
- **Single Point of Control**: Replace 150+ scattered stealth calls with centralized system
- **Configuration-Driven**: Environment variable control for easy deployment optimization
- **Future-Proof Design**: Multi-content framework for jobs, companies, feeds expansion
- **Intelligent Operation**: Smart content detection replaces hardcoded waits
- **Performance Visibility**: Built-in telemetry for continuous optimization

This PRP provides the comprehensive context and implementation roadmap needed to transform the LinkedIn MCP server from a slow, scattered system into a high-performance, centralized architecture that maintains data quality while achieving dramatic speed improvements.