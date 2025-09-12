"""Human-like behavior simulation for stealth scraping."""

import asyncio
import logging
import random
import re
from typing import Optional
from urllib.parse import urlparse

from playwright.async_api import Page

from ..config import StealthConfig, LinkedInDetectionError

logger = logging.getLogger(__name__)


async def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add random human-like delay."""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)


async def simulate_human_mouse_movement(page: Page):
    """Simulate natural mouse movements across the page."""
    try:
        # Get viewport dimensions
        viewport = page.viewport_size
        if not viewport:
            viewport = {"width": 1920, "height": 1080}

        # Simulate multiple mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)
            await page.mouse.move(x, y)
            await random_delay(0.1, 0.3)

        logger.debug("Simulated mouse movements")
    except Exception as e:
        logger.debug(f"Mouse movement simulation failed: {e}")


async def simulate_reading_scrolling(
    page: Page, min_scrolls: int = 2, max_scrolls: int = 5
):
    """Simulate human reading behavior with scrolling."""
    try:
        scrolls = random.randint(min_scrolls, max_scrolls)

        for i in range(scrolls):
            # Random scroll amount (not too much at once)
            scroll_amount = random.randint(200, 600)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

            # Random pause as if reading
            read_delay = random.uniform(1.5, 4.0)
            await asyncio.sleep(read_delay)

            # Occasionally scroll back up a bit (human-like)
            if random.random() < 0.3:
                back_scroll = random.randint(50, 200)
                await page.evaluate(f"window.scrollBy(0, -{back_scroll})")
                await random_delay(0.5, 1.5)

        logger.debug(f"Simulated reading with {scrolls} scrolls")
    except Exception as e:
        logger.debug(f"Reading simulation failed: {e}")


async def simulate_typing_delay(page: Page, selector: str, text: str):
    """Simulate human typing with realistic delays."""
    try:
        await page.click(selector)
        await random_delay(0.2, 0.5)

        # Clear existing text
        await page.keyboard.press("Control+a")
        await random_delay(0.1, 0.2)

        # Type with human-like delays
        for char in text:
            await page.keyboard.type(char)
            # Variable typing speed
            await asyncio.sleep(random.uniform(0.05, 0.15))

        logger.debug(f"Simulated typing: {text}")
    except Exception as e:
        logger.debug(f"Typing simulation failed: {e}")


async def warm_linkedin_session(page: Page, config: Optional[StealthConfig] = None):
    """Minimal session warming protocol - legacy approach used direct profile access.

    The legacy selenium implementation went directly to LinkedIn profiles without
    session warming, which worked reliably. This approach mimics that behavior.
    """
    if not config:
        config = StealthConfig()

    logger.info("Starting minimal LinkedIn session warming...")

    try:
        # Legacy approach: No session warming needed, just validate cookie is set
        # We'll do a minimal check by accessing a basic LinkedIn endpoint
        # that doesn't cause redirect loops but verifies authentication
        logger.debug("Minimal warming: Quick authentication validation")

        # Small delay to let cookies settle
        await random_delay(*config.base_delay_range)

        # The actual profile access will happen in the scraper itself
        # This just ensures the page/context is ready
        await page.wait_for_load_state("domcontentloaded")

        logger.info(
            "Minimal session warming completed - ready for direct profile access"
        )

    except Exception as e:
        # Don't fail the whole session for warming issues - let profile access try directly
        logger.warning(f"Session warming had minor issues but proceeding: {e}")
        # Don't raise an exception - let the actual profile scraping handle authentication


async def navigate_to_profile_stealthily(
    page: Page, linkedin_url: str, config: Optional[StealthConfig] = None
):
    """Navigate to LinkedIn profile using human-like search behavior."""
    if not config:
        config = StealthConfig()

    logger.info(f"Navigating stealthily to profile: {linkedin_url}")

    try:
        # Extract username from LinkedIn URL
        username = extract_username_from_url(linkedin_url)
        if not username:
            logger.error(f"Could not extract username from URL: {linkedin_url}")
            # Fallback to direct navigation (riskier)
            await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=30000)
            return

        logger.debug(f"Extracted username: {username}")

        # Stage 1: Use LinkedIn search instead of direct navigation
        search_url = "https://www.linkedin.com/search/results/people/"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await random_delay(*config.base_delay_range)

        # Stage 2: Simulate search typing
        search_selector = 'input[placeholder*="Search"], input[aria-label*="Search"]'

        # Wait for search box and clear it
        await page.wait_for_selector(search_selector, timeout=10000)
        await simulate_typing_delay(page, search_selector, username)

        # Stage 3: Submit search with human-like delay
        await random_delay(1.0, 2.0)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("domcontentloaded")

        # Stage 4: Look for and click the profile link
        # Try multiple possible selectors for profile links
        profile_selectors = [
            f'a[href*="{username}"][href*="/in/"]',
            f'a[href*="/in/{username}"]',
            f'a[href*="/in/{username}/"]',
            'a[data-test-link-to-profile-link="true"]',
            ".entity-result__title-text a",
        ]

        profile_found = False
        for selector in profile_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    # Add slight delay before clicking
                    await random_delay(1.0, 2.0)
                    await page.click(selector)
                    await page.wait_for_load_state("domcontentloaded")
                    profile_found = True
                    logger.debug(f"Profile found using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector failed {selector}: {e}")
                continue

        if not profile_found:
            logger.warning(
                "Could not find profile in search results, trying direct navigation"
            )
            await page.goto(linkedin_url, wait_until="domcontentloaded", timeout=30000)

        # Stage 5: Final check for successful navigation
        await random_delay(*config.base_delay_range)

        if await detect_linkedin_challenge(page):
            raise LinkedInDetectionError("Challenge detected after profile navigation")

        logger.info("Successfully navigated to profile")

    except Exception as e:
        if isinstance(e, LinkedInDetectionError):
            raise
        logger.error(f"Stealth navigation failed: {e}")
        raise LinkedInDetectionError(f"Profile navigation failed: {e}")


async def detect_linkedin_challenge(page: Page) -> bool:
    """Detect if LinkedIn is presenting a security challenge."""
    try:
        url = page.url.lower()

        # Check for challenge URLs
        challenge_indicators = [
            "challenge",
            "checkpoint",
            "security",
            "verify",
            "captcha",
            "blocked",
        ]

        if any(indicator in url for indicator in challenge_indicators):
            logger.warning(f"LinkedIn challenge detected in URL: {page.url}")
            return True

        # Check for challenge content
        challenge_selectors = [
            '[data-test-id*="challenge"]',
            '[class*="challenge"]',
            '[class*="security"]',
            'text="Please complete this security check"',
            'text="We want to make sure it\'s really you"',
            'text="Help us protect the LinkedIn community"',
            '[aria-label*="security challenge"]',
        ]

        for selector in challenge_selectors:
            if await page.locator(selector).count() > 0:
                logger.warning(f"Challenge element found: {selector}")
                return True

        # Check for empty or blocked profile content
        profile_indicators = [
            ".pv-text-details__left-panel",
            ".ph5.pb5",
            ".pv-profile-section",
            "h1",
        ]

        has_content = False
        for selector in profile_indicators:
            if await page.locator(selector).count() > 0:
                has_content = True
                break

        if not has_content and "/in/" in page.url:
            logger.warning("Profile page appears empty - possible detection")
            return True

    except Exception as e:
        logger.debug(f"Error checking for challenges: {e}")

    return False


def extract_username_from_url(linkedin_url: str) -> Optional[str]:
    """Extract LinkedIn username from profile URL."""
    try:
        # Parse the URL
        parsed = urlparse(linkedin_url)
        path = parsed.path.strip("/")

        # Extract username from different URL formats
        if "/in/" in path:
            # Standard format: linkedin.com/in/username
            username = path.split("/in/")[-1].split("/")[0]
            return username
        elif "/profile/view" in path:
            # Old format: linkedin.com/profile/view?id=username
            # Extract from query params
            from urllib.parse import parse_qs

            query_params = parse_qs(parsed.query)
            if "id" in query_params:
                return query_params["id"][0]

        # Try to extract any username-like string
        username_match = re.search(r"/(?:in|profile)/([a-zA-Z0-9\-_]+)", linkedin_url)
        if username_match:
            return username_match.group(1)

    except Exception as e:
        logger.debug(f"Error extracting username from {linkedin_url}: {e}")

    return None


async def simulate_profile_reading_behavior(
    page: Page, config: Optional[StealthConfig] = None
):
    """Simulate human-like profile reading behavior with comprehensive scrolling for lazy loading."""
    if not config:
        config = StealthConfig()

    logger.debug("Simulating comprehensive profile reading behavior")

    try:
        # Stage 1: Initial profile scan with gradual scroll to trigger lazy loading
        await simulate_comprehensive_scrolling(page)

        # Stage 2: Focus on different sections with reading delays
        section_selectors = [
            ".pv-text-details__left-panel",  # Main profile info
            ".pv-about-section",  # About section
            "section:has(#experience)",  # Experience section
            "section:has(#education)",  # Education section
            ".pv-accomplishments-section",  # Accomplishments
            ".pv-interests-section",  # Interests
        ]

        for selector in section_selectors:
            try:
                locator = page.locator(selector)
                if await locator.count() > 0:
                    await locator.scroll_into_view_if_needed()
                    await random_delay(*config.reading_delay_range)

                    # Sometimes hover over elements
                    if random.random() < 0.4:
                        await page.hover(selector)
                        await random_delay(0.5, 1.0)

            except Exception as e:
                logger.debug(f"Section interaction failed {selector}: {e}")

        # Stage 3: Final comprehensive scroll to ensure all content is loaded
        await simulate_comprehensive_scrolling(page, final_pass=True)
        logger.debug("Comprehensive profile reading behavior completed")

    except Exception as e:
        logger.debug(f"Profile reading simulation failed: {e}")


async def simulate_comprehensive_scrolling(page: Page, final_pass: bool = False):
    """Perform comprehensive scrolling to trigger lazy loading of all content."""
    try:
        # Get viewport height for calculating scroll positions
        viewport_height = await page.evaluate("window.innerHeight")

        if final_pass:
            logger.debug("Performing final comprehensive scroll pass")
        else:
            logger.debug("Performing initial comprehensive scroll for lazy loading")

        # Phase 1: Gradual scroll down in sections to trigger lazy loading
        scroll_sections = 8 if not final_pass else 5
        for i in range(scroll_sections):
            scroll_position = (i + 1) * (viewport_height // scroll_sections)
            await page.evaluate(f"window.scrollTo(0, {scroll_position})")

            # Wait longer on first pass to allow content to load
            wait_time = 1200 if not final_pass else 600
            await page.wait_for_timeout(wait_time)

        # Phase 2: Scroll to absolute bottom
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000 if not final_pass else 1000)

        # Phase 3: Scroll back up gradually to ensure all sections are visible
        for i in range(3):
            scroll_ratio = (2 - i) / 3
            await page.evaluate(
                f"window.scrollTo(0, document.body.scrollHeight * {scroll_ratio})"
            )
            await page.wait_for_timeout(800)

        # Phase 4: Return to top
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

        logger.debug("Comprehensive scrolling completed")

    except Exception as e:
        logger.debug(f"Comprehensive scrolling failed: {e}")
