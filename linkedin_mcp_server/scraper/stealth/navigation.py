"""Navigation strategies for accessing LinkedIn content with configurable stealth."""

import logging
import random
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

from patchright.async_api import Page

from linkedin_mcp_server.scraper.config import LinkedInDetectionError
from linkedin_mcp_server.scraper.stealth.controller import PageType
from linkedin_mcp_server.scraper.stealth.profiles import NavigationMode, StealthProfile

logger = logging.getLogger(__name__)


class NavigationStrategy:
    """Smart navigation strategies for LinkedIn pages.

    This class provides different navigation approaches based on the configured
    stealth profile, enabling fast direct navigation or slow search-first patterns.
    """

    def __init__(self, mode: NavigationMode):
        """Initialize navigation strategy.

        Args:
            mode: Navigation mode (DIRECT or SEARCH_FIRST)
        """
        self.mode = mode
        logger.debug(f"NavigationStrategy initialized with mode: {mode.value}")

    async def navigate_to_page(
        self,
        page: Page,
        url: str,
        page_type: PageType,
        profile: StealthProfile,
    ) -> None:
        """Navigate to a LinkedIn page using the configured strategy.

        Args:
            page: Patchright page instance
            url: Target LinkedIn URL
            page_type: Type of LinkedIn page
            profile: Stealth profile for timing configurations
        """
        logger.info(f"Navigating to {page_type.value} using {self.mode.value} strategy")

        # Check for challenges before navigation
        if await self._detect_linkedin_challenge(page):
            raise LinkedInDetectionError("Challenge detected before navigation")

        # Route to appropriate navigation method
        if self.mode == NavigationMode.DIRECT:
            await self._navigate_direct(page, url, profile)
        elif self.mode == NavigationMode.SEARCH_FIRST:
            if page_type == PageType.PROFILE:
                await self._navigate_search_first(page, url, profile)
            else:
                # For non-profile pages, use direct navigation
                await self._navigate_direct(page, url, profile)

        # Post-navigation challenge detection
        if await self._detect_linkedin_challenge(page):
            raise LinkedInDetectionError("Challenge detected after navigation")

        logger.debug(f"Successfully navigated to {url}")

    async def _navigate_direct(
        self,
        page: Page,
        url: str,
        profile: StealthProfile,
    ) -> None:
        """Direct navigation to LinkedIn URL (fast path).

        This is the optimized navigation path that goes directly to the URL,
        achieving significant speed improvements over search-first approach.
        """
        logger.debug(f"Direct navigation to: {url}")

        try:
            # Simple direct navigation with configurable timeout
            timeout = 30000 if profile.simulation.value != "none" else 15000

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout,
            )

            # Brief delay based on profile
            if profile.simulation.value != "none":
                nav_delays = profile.delays.navigation
                delay = random.uniform(nav_delays[0], nav_delays[1])
                await page.wait_for_timeout(int(delay * 1000))

        except Exception as e:
            logger.error(f"Direct navigation failed: {e}")
            raise LinkedInDetectionError(f"Navigation failed: {e}")

    async def _navigate_search_first(
        self,
        page: Page,
        url: str,
        profile: StealthProfile,
    ) -> None:
        """Search-first navigation pattern (slow but stealthy).

        This mimics human behavior by searching for the profile first,
        then clicking on the result. This is the current default approach.
        """
        logger.debug(f"Search-first navigation to: {url}")

        try:
            # Extract username from LinkedIn URL
            username = self._extract_username_from_url(url)
            if not username:
                logger.warning(
                    f"Could not extract username from URL: {url}, "
                    "falling back to direct navigation"
                )
                await self._navigate_direct(page, url, profile)
                return

            logger.debug(f"Extracted username: {username}")

            # Stage 1: Navigate to LinkedIn search
            search_url = "https://www.linkedin.com/search/results/people/"
            await page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            # Random delay after navigation
            delay = random.uniform(*profile.delays.base)
            await page.wait_for_timeout(int(delay * 1000))

            # Stage 2: Type in search box
            search_selectors = [
                'input[placeholder*="Search"]',
                'input[aria-label*="Search"]',
                ".search-global-typeahead__input",
            ]

            search_box = None
            for selector in search_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        search_box = selector
                        break
                except Exception:
                    continue

            if not search_box:
                logger.warning("Could not find search box, using direct navigation")
                await self._navigate_direct(page, url, profile)
                return

            # Clear and type with human-like delays
            await page.locator(search_box).clear()
            await self._simulate_typing(page, search_box, username, profile)

            # Stage 3: Submit search
            delay = random.uniform(1.0, 2.0)
            await page.wait_for_timeout(int(delay * 1000))
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("domcontentloaded")

            # Stage 4: Click on profile result
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
                    if await page.locator(selector).first.is_visible():
                        # Delay before clicking
                        delay = random.uniform(*profile.delays.base)
                        await page.wait_for_timeout(int(delay * 1000))

                        await page.locator(selector).first.click()
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
                await self._navigate_direct(page, url, profile)

            # Final delay
            delay = random.uniform(*profile.delays.base)
            await page.wait_for_timeout(int(delay * 1000))

        except Exception as e:
            if isinstance(e, LinkedInDetectionError):
                raise
            logger.error(f"Search-first navigation failed: {e}")
            raise LinkedInDetectionError(f"Navigation failed: {e}")

    async def _simulate_typing(
        self,
        page: Page,
        selector: str,
        text: str,
        profile: StealthProfile,
    ) -> None:
        """Simulate human-like typing with configurable delays."""
        element = page.locator(selector).first
        await element.focus()

        for char in text:
            await page.keyboard.type(char)
            # Random delay between keystrokes
            delay = random.uniform(*profile.delays.typing)
            await page.wait_for_timeout(int(delay * 1000))

    def _extract_username_from_url(self, linkedin_url: str) -> Optional[str]:
        """Extract LinkedIn username from profile URL."""
        try:
            parsed = urlparse(linkedin_url)
            path = parsed.path.strip("/")

            # Extract username from different URL formats
            if "/in/" in path:
                # Standard format: linkedin.com/in/username
                username = path.split("/in/")[-1].split("/")[0]
                return username
            elif "/profile/view" in path:
                # Old format: linkedin.com/profile/view?id=username
                query_params = parse_qs(parsed.query)
                if "id" in query_params:
                    return query_params["id"][0]

            # Try regex extraction
            username_match = re.search(
                r"/(?:in|profile)/([a-zA-Z0-9\-_]+)", linkedin_url
            )
            if username_match:
                return username_match.group(1)

        except Exception as e:
            logger.debug(f"Error extracting username from {linkedin_url}: {e}")

        return None

    async def _detect_linkedin_challenge(self, page: Page) -> bool:
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

            # Check for empty profile content (potential soft block)
            if "/in/" in page.url:
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

                if not has_content:
                    logger.warning("Profile page appears empty - possible detection")
                    return True

        except Exception as e:
            logger.debug(f"Error checking for challenges: {e}")

        return False
