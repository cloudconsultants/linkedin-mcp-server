# CSS Selector Validation & Main-Page Scraping Enhancement PRP

**Description**: Restore LinkedIn profile scraping functionality by fixing outdated CSS selectors and eliminating session-breaking detail page navigation. Implement robust main-page-only extraction with proven CSS selectors that work consistently to achieve 100% compatibility with testdata/testscrape.txt baseline.

## Goal
Restore LinkedIn MCP Server profile scraping to full functionality by:
- Fixing broken CSS selectors that produce malformed output (HTML containers vs clean text)
- Eliminating `/details/experience` and `/details/education` navigation that causes session kick-outs
- Implementing robust main-page-only data extraction with proven CSS selectors
- Achieving exact output format compatibility with `testdata/testscrape.txt` baseline (8 experiences, 4 educations)

## Why
- **Critical Business Impact**: Profile scraping is completely broken - authentication fails, malformed output, missing data
- **User Experience**: Current implementation returns unusable data with HTML noise instead of clean structured information
- **Session Stability**: Detail page navigation triggers LinkedIn anti-bot detection, causing account lockouts
- **Data Quality**: Only extracting 4/8 experience entries and 0/4 education entries vs baseline expectations

## What
User-visible behavior and technical requirements:

### Success Criteria
- [ ] **Zero session kick-outs**: No navigation to `/details/*` pages during scraping
- [ ] **Perfect format match**: 100% JSON structure compatibility with `testdata/testscrape.txt`
- [ ] **Complete data extraction**: Extract 8 experience entries + 4 education entries for test profile `amir-nahvi-94814819`
- [ ] **Clean text output**: No raw HTML containers in extracted fields (company, job_title, etc.)
- [ ] **Proven selector reliability**: CSS selectors work consistently like the legacy selenium version
- [ ] **Validation framework**: Automated testing against known baseline with executable validation commands
- [ ] **Performance benchmarks**: Clear timing metrics for each profile section extraction

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://scrapfly.io/blog/posts/how-to-scrape-linkedin-person-profile-company-job-data
  why: Modern 2024-2025 LinkedIn scraping patterns, JSON-LD extraction methods
  critical: Uses `//script[@type='application/ld+json']` instead of DOM parsing
- url: https://github.com/joeyism/linkedin_scraper
  why: Legacy proven selector patterns that generated testdata/testscrape.txt
  critical: Main selector `div[data-view-name='profile-component-entity']` for both experience/education
- file: testdata/testscrape.txt
  why: Exact baseline format that must be matched - 8 experiences, 4 educations
  critical: Profile `amir-nahvi-94814819` is the validation target
- file: linkedin_mcp_server/scraper/scrapers/person/get_person.py:162-233
  why: Current broken basic info extraction implementation
- file: linkedin_mcp_server/scraper/scrapers/person/experience.py
  why: Broken experience scraper that navigates to `/details/experience`
  critical: Must be rewritten for main-page-only extraction
- file: linkedin_mcp_server/scraper/scrapers/person/education.py
  why: Broken education scraper that navigates to `/details/education`
  critical: Currently returns empty array, must be fixed
- file: docs/legacy-linkedin-mcp-server/linkedin_mcp_server/tools/person.py
  why: Working legacy implementation using linkedin_scraper library
  critical: Shows successful main-page-only approach with perfect output
```

### Current Codebase
```bash
linkedin_mcp_server/
├── scraper/
│   ├── scrapers/
│   │   ├── person/
│   │   │   ├── get_person.py          # Main scraper class - basic info broken
│   │   │   ├── experience.py          # BROKEN: navigates to /details/experience
│   │   │   ├── education.py           # BROKEN: navigates to /details/education
│   │   │   ├── utils.py               # Helper functions
│   │   │   ├── accomplishments.py     # Working
│   │   │   ├── contacts.py            # Working
│   │   │   └── interests.py           # Working
│   │   └── utils.py                   # Scroll utilities
│   ├── models/person.py               # Person, Experience, Education models
│   ├── browser/stealth_manager.py     # Anti-detection (working) - MUST USE
│   └── auth/cookie.py                 # Authentication (working) - li_at from .env
└── tools/person.py                    # MCP tool interface (working)
testdata/testscrape.txt                # CRITICAL: Validation baseline
```

### Desired Codebase
```bash
linkedin_mcp_server/scraper/scrapers/person/
├── get_person.py          # ENHANCED: main-page-only scraping + robust selectors
├── experience.py          # REWRITTEN: main-page extraction with fallback selectors
├── education.py           # REWRITTEN: main-page extraction with fallback selectors
├── selectors.py           # NEW: Multi-layer selector strategy classes
└── validation.py          # NEW: testscrape.txt validation framework
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Current implementation navigates to detail pages
# linkedin_mcp_server/scraper/scrapers/person/experience.py:25
experience_url = os.path.join(str(person.linkedin_url), "details/experience")
await page.goto(experience_url)  # ❌ CAUSES SESSION KICK-OUT

# CRITICAL: Current selectors extract HTML containers instead of clean text
# linkedin_mcp_server/scraper/scrapers/person/get_person.py:170
top_panel = self.page.locator(".mt2.relative").first  # Gets entire container with HTML

# CRITICAL: Must use existing stealth libraries - DO NOT MODIFY
# linkedin_mcp_server/scraper/browser/stealth_manager.py contains working anti-detection
# Use: await simulate_profile_reading_behavior(self.page)

# CRITICAL: Authentication via .env file li_at cookie - already working
# linkedin_mcp_server/scraper/auth/cookie.py handles authentication properly

# CRITICAL: LinkedIn DOM structure changed - old selectors outdated
# Legacy selenium used: `div[data-view-name='profile-component-entity']`
# Must adapt to Playwright equivalents with same targeting logic

# GOTCHA: Playwright locator.inner_text() includes hidden HTML
# Use locator('selector span[aria-hidden="true"]') for clean text extraction

# GOTCHA: LinkedIn lazy-loads content on scroll - MUST scroll to reveal sections
# Use: await element.scroll_into_view_if_needed() before extraction

# CRITICAL: Fail fast approach - if critical selectors fail, stop immediately
# Better to return clear error than partial/malformed data
```

## Implementation Blueprint

### Data models and structure
Current models are correct - no changes needed to Person, Experience, Education classes.

```python
# Existing models in linkedin_mcp_server/scraper/models/person.py are adequate:
@dataclass
class Experience:
    position_title: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    duration: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    # ... rest of fields match testscrape.txt structure perfectly
```

### List of tasks to be completed to fulfill the PRP

```yaml
Task 1: CREATE linkedin_mcp_server/scraper/scrapers/person/selectors.py
  - PURPOSE: Proven CSS selector constants adapted from working selenium implementation
  - PATTERN: Direct selector mapping from legacy selenium success patterns
  - CRITICAL: Use exact selector equivalents that worked in docs/legacy-linkedin-mcp-server/

Task 2: MODIFY linkedin_mcp_server/scraper/scrapers/person/get_person.py
  - FIND: _scrape_basic_info method (lines 162-233)
  - REPLACE: Broken selectors with proven working CSS selectors
  - PRESERVE: All existing stealth behavior - use stealth_manager.py functions
  - CRITICAL: Use reliable selectors that extract clean text like selenium version

Task 3: REWRITE linkedin_mcp_server/scraper/scrapers/person/experience.py
  - REMOVE: All detail page navigation (await page.goto details/experience)
  - CREATE: scrape_experiences_main_page() function using ONLY main profile page
  - PATTERN: Translate legacy selenium div[data-view-name='profile-component-entity'] to Playwright
  - CRITICAL: Must extract exact 8 experiences like legacy selenium version

Task 4: REWRITE linkedin_mcp_server/scraper/scrapers/person/education.py
  - REMOVE: All detail page navigation (await page.goto details/education)
  - CREATE: scrape_educations_main_page() function using ONLY main profile page
  - PATTERN: Mirror experience approach with education-specific selectors
  - CRITICAL: Must extract exact 4 educations like legacy selenium version

Task 5: MODIFY linkedin_mcp_server/scraper/scrapers/person/get_person.py
  - FIND: scrape_profile method calls to experience/education scrapers
  - REPLACE: Detail page scraper calls with main-page-only versions
  - PRESERVE: All existing error handling and stealth patterns from stealth_manager.py
  - CRITICAL: Use fail-fast approach - clear errors over partial data
```

### Per task pseudocode

```python
# Task 1: Proven selector constants + Performance benchmarking
class LinkedInSelectors:
    """Reliable CSS selectors adapted from working selenium implementation."""

    # Experience section selectors
    EXPERIENCE_SECTION = "section:has(#experience)"
    EXPERIENCE_ITEMS = "div[data-view-name='profile-component-entity']"

    # Education section selectors
    EDUCATION_SECTION = "section:has(#education)"
    EDUCATION_ITEMS = "div[data-view-name='profile-component-entity']"

    # Clean text extraction
    CLEAN_TEXT = "span[aria-hidden='true']"
    POSITION_TITLE = "h3 span[aria-hidden='true']"
    COMPANY_NAME = ".mr1.hoverable-link-text span[aria-hidden='true']"

class PerformanceBenchmark:
    """Performance timing utilities for profile section extraction."""

    @staticmethod
    def log_section_timing(section_name: str, start_time: float, end_time: float, item_count: int):
        """Log timing metrics for each profile section."""
        duration = end_time - start_time
        avg_per_item = duration / item_count if item_count > 0 else duration
        logger.info(f"BENCHMARK - {section_name}: {duration:.2f}s total, {item_count} items, {avg_per_item:.3f}s/item")

# Task 2: Fix basic info extraction with proven selectors + benchmarking
async def _scrape_basic_info_robust(self, person: Person) -> None:
    """Enhanced basic info using proven CSS selectors from selenium version."""

    import time
    start_time = time.time()

    # CRITICAL: Use existing stealth behavior - DO NOT MODIFY
    await simulate_profile_reading_behavior(self.page)

    # Use proven headline selector (adapted from selenium success)
    try:
        headline_element = self.page.locator("h1 + div span[aria-hidden='true']").first
        if await headline_element.is_visible():
            headline_text = (await headline_element.inner_text()).strip()
            if headline_text and headline_text != person.name:
                person.add_headline(headline_text)
    except Exception:
        # If proven selector fails, LinkedIn DOM changed - fail fast
        raise LinkedInScrapingError("LinkedIn DOM structure changed - headline extraction failed")

    # Log performance benchmark
    end_time = time.time()
    PerformanceBenchmark.log_section_timing("basic_info", start_time, end_time, 1)

# Task 3: Main-page experience extraction with benchmarking
async def scrape_experiences_main_page(page: Page, person: Person) -> None:
    """Extract experiences from main profile page only - using proven selectors."""

    import time
    start_time = time.time()

    # CRITICAL: Stay on main page - no navigation whatsoever
    await simulate_profile_reading_behavior(page)

    # Use proven experience section selector
    experience_section = page.locator("section:has(#experience)").first
    if not await experience_section.is_visible():
        raise LinkedInScrapingError("Experience section not found")

    # Scroll to reveal content (LinkedIn lazy-loads)
    await experience_section.scroll_into_view_if_needed()
    await page.wait_for_timeout(2000)

    # Use proven selector from selenium version
    experience_items = await experience_section.locator(
        "div[data-view-name='profile-component-entity']"
    ).all()

    # Extract each experience using proven patterns
    extracted_count = 0
    for item in experience_items:
        experience = await _extract_single_experience(item)
        if experience:
            person.add_experience(experience)
            extracted_count += 1

    # Log performance benchmark
    end_time = time.time()
    PerformanceBenchmark.log_section_timing("experience", start_time, end_time, extracted_count)

# Task 4: Education extraction with benchmarking
async def scrape_educations_main_page(page: Page, person: Person) -> None:
    """Extract educations from main profile page only - using proven selectors."""

    import time
    start_time = time.time()

    # Use proven education section selector
    education_section = page.locator("section:has(#education)").first
    if not await education_section.is_visible():
        raise LinkedInScrapingError("Education section not found")

    # Scroll to reveal content
    await education_section.scroll_into_view_if_needed()
    await page.wait_for_timeout(2000)

    # Use same proven selector pattern as experience
    education_items = await education_section.locator(
        "div[data-view-name='profile-component-entity']"
    ).all()

    # Extract each education using proven patterns
    extracted_count = 0
    for item in education_items:
        education = await _extract_single_education(item)
        if education:
            person.add_education(education)
            extracted_count += 1

    # Log performance benchmark
    end_time = time.time()
    PerformanceBenchmark.log_section_timing("education", start_time, end_time, extracted_count)

# Task 5: Integration with existing stealth and error handling
async def scrape_profile(self, url: str, fields: PersonScrapingFields) -> Person:
    """Modified to use main-page-only extraction - no fallbacks, proven selectors only."""

    # PRESERVE: All existing stealth navigation and error handling
    await navigate_to_profile_stealthily(self.page, url)
    await simulate_profile_reading_behavior(self.page)

    # REPLACE: Detail page scraper calls with main-page versions
    if PersonScrapingFields.EXPERIENCE in fields:
        await scrape_experiences_main_page(self.page, person)  # NEW - main page only

    if PersonScrapingFields.EDUCATION in fields:
        await scrape_educations_main_page(self.page, person)   # NEW - main page only
```

### Integration Points
```yaml
AUTHENTICATION:
  - preserve: linkedin_mcp_server/scraper/auth/cookie.py (working)
  - pattern: li_at cookie from .env file - already functional
  - NO CHANGES: Authentication is working correctly

STEALTH_BEHAVIOR:
  - preserve: linkedin_mcp_server/scraper/browser/stealth_manager.py (working)
  - pattern: MUST use simulate_profile_reading_behavior() and existing functions
  - NO CHANGES: Anti-detection is working - do not modify

PAGE_NAVIGATION:
  - modify: PersonScraper.scrape_profile() method only
  - remove: All calls to detail page scrapers (experience.py, education.py)
  - add: Main-page-only scraper calls
  - preserve: navigate_to_profile_stealthily() and stealth patterns

VALIDATION:
  - use: Existing test framework patterns
  - pattern: Follow current pytest structure in tests/
  - critical: Validate against testdata/testscrape.txt exact format
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check linkedin_mcp_server/scraper/scrapers/person/ --fix
uv run mypy linkedin_mcp_server/scraper/scrapers/person/
# Expected: No errors. If errors exist, READ the error and fix immediately.
```

### Level 2: Unit Tests
Create comprehensive test coverage following existing patterns:

```python
# MODIFY existing test files - do not create new test structure
def test_experience_extraction_main_page():
    """Experience extraction works from main page only - matches legacy selenium."""
    # Mock Playwright page with known experience section HTML
    experiences = await scrape_experiences_main_page(mock_page, person)
    assert len(experiences) == 8  # Must match legacy selenium success
    assert experiences[0].position_title is not None
    assert experiences[0].company is not None
    # Validate clean text (no HTML containers)
    assert '<div>' not in experiences[0].company
    assert '\n    \n\n    \n' not in experiences[0].company

def test_education_extraction_main_page():
    """Education extraction works from main page only - matches legacy selenium."""
    educations = await scrape_educations_main_page(mock_page, person)
    assert len(educations) == 4  # Must match legacy selenium success
    assert educations[0].institution_name is not None
    assert educations[0].degree is not None

def test_fail_fast_behavior():
    """Fail-fast approach works - clear errors over partial data."""
    with pytest.raises(LinkedInScrapingError) as exc_info:
        await scrape_experiences_main_page(broken_mock_page, person)
    assert "selector patterns may be outdated" in str(exc_info.value)
```

```bash
# Run and iterate until passing:
uv run pytest tests/ -v -k "experience"
uv run pytest tests/ -v -k "education"
# If failing: Read error, understand root cause, fix code, re-run
# DO NOT mock to pass - fix the actual implementation
```

### Level 3: Integration Test
```bash
# Test against actual LinkedIn profile (testscrape.txt baseline)
# Authentication via .env li_at cookie (already working)
uv run python -c "
from linkedin_mcp_server.scraper.scrapers.person.get_person import PersonScraper
import asyncio
import os
async def test():
    # Use existing authentication - li_at from .env
    scraper = PersonScraper(authenticated_page)
    profile = await scraper.scrape_profile('https://www.linkedin.com/in/amir-nahvi-94814819/')
    print(f'Experiences: {len(profile.experiences)}')  # Must be 8
    print(f'Educations: {len(profile.educations)}')    # Must be 4
    print(f'Company clean: {profile.company}')  # Must be clean text, not HTML
    print(f'Name: {profile.name}')  # Must be 'Amir Nahvi'
asyncio.run(test())
"
# Expected: 8 experiences, 4 educations, clean text fields matching testscrape.txt
# If error: Check logs for selector failures, adjust fallback chains
# Fail-fast: Clear error messages, no partial data
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check linkedin_mcp_server/scraper/scrapers/person/`
- [ ] No type errors: `uv run mypy linkedin_mcp_server/scraper/scrapers/person/`
- [ ] testscrape.txt exact match: Profile extraction matches baseline format exactly
- [ ] Manual integration test: 8 experiences + 4 educations extracted successfully
- [ ] Zero detail page navigation: Network logs confirm no `/details/*` requests
- [ ] Clean text output: No HTML containers in any extracted fields
- [ ] Fail-fast validation: Clear error messages when selectors fail
- [ ] Stealth preservation: All existing anti-detection patterns maintained
- [ ] Performance benchmarks logged: Timing metrics for basic_info, experience, and education sections

---

## Anti-Patterns to Avoid
- ❌ Don't navigate to `/details/experience` or `/details/education` pages
- ❌ Don't modify stealth_manager.py or authentication.py - they work correctly
- ❌ Don't use single selectors without fail-fast fallback chains
- ❌ Don't extract entire HTML containers - target clean text with span[aria-hidden='true']
- ❌ Don't ignore testscrape.txt baseline - it's the exact success format from legacy selenium
- ❌ Don't skip scroll behavior - LinkedIn lazy-loads content that must be revealed
- ❌ Don't continue with partial data on selector failure - fail fast with clear errors
- ❌ Don't add new dependencies - use existing Playwright + stealth libraries only
- ❌ Don't modify working components (auth, stealth, models) - focus only on broken scrapers

**Confidence Score: 10/10** - With clarified requirements and proper markdown formatting, this PRP provides complete context for one-pass implementation success matching the legacy selenium version's proven results.
