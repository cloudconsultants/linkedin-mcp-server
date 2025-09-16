"""Stealth-enhanced person profile scraper using Playwright."""

import logging
from patchright.async_api import Page
from pydantic import HttpUrl

from ...config import PersonScrapingFields, LinkedInDetectionError
from ...models.person import Person
from ...browser.behavioral import (
    random_delay,
)
# Note: Individual scraper imports removed - now using unified ProfilePageScraper

logger = logging.getLogger(__name__)


class PersonScraper:
    """Scraper for LinkedIn person profiles."""

    def __init__(self, page: Page):
        """Initialize the scraper with a Playwright page.

        Args:
            page: Playwright page instance.
        """
        self.page = page

    async def scrape_profile(
        self, url: str, fields: PersonScrapingFields
    ) -> Person:
        """Scrape a LinkedIn profile using A/B testing between new and legacy systems.

        Args:
            url: LinkedIn profile URL
            fields: Fields to scrape

        Returns:
            Person: Extracted profile data
        """
        import os

        # Check if new stealth system should be used
        use_new_stealth = os.getenv("USE_NEW_STEALTH", "false").lower() == "true"

        if use_new_stealth:
            logger.info(f"Using NEW stealth system for profile scraping: {url}")
            return await self._scrape_profile_new_system(url, fields)
        else:
            logger.info(f"Using LEGACY stealth system for profile scraping: {url}")
            return await self._scrape_profile_legacy_system(url, fields)

    async def _scrape_profile_new_system(
        self, url: str, fields: PersonScrapingFields
    ) -> Person:
        """Scrape profile using the new centralized stealth system."""
        try:
            from linkedin_mcp_server.scraper.pages.profile_page import (
                ProfilePageScraper,
            )

            # Create profile page scraper with centralized stealth
            profile_scraper = ProfilePageScraper()

            # Use the new unified scraping approach
            return await profile_scraper.scrape_profile_page(
                page=self.page, url=url, fields=fields
            )

        except Exception as e:
            logger.error(f"New stealth system failed: {e}")
            logger.warning("Falling back to legacy system")
            return await self._scrape_profile_legacy_system(url, fields)

    async def _scrape_profile_legacy_system(
        self, url: str, fields: PersonScrapingFields
    ) -> Person:
        """Scrape profile using the new unified system with legacy stealth profile."""
        try:
            from linkedin_mcp_server.scraper.pages.profile_page import (
                ProfilePageScraper,
            )
            import os

            logger.debug(f"Using unified ProfilePageScraper with legacy stealth profile for: {url}")

            # Set legacy stealth profile for backward compatibility
            original_profile = os.getenv("STEALTH_PROFILE")
            os.environ["STEALTH_PROFILE"] = "MAXIMUM_STEALTH"  # Match original behavior

            try:
                # Create profile page scraper with legacy stealth settings
                profile_scraper = ProfilePageScraper()

                # Use the unified scraping approach with legacy stealth profile
                return await profile_scraper.scrape_profile_page(
                    page=self.page, url=url, fields=fields
                )
            finally:
                # Restore original stealth profile
                if original_profile:
                    os.environ["STEALTH_PROFILE"] = original_profile
                elif "STEALTH_PROFILE" in os.environ:
                    del os.environ["STEALTH_PROFILE"]

        except Exception as e:
            logger.error(f"Unified system with legacy profile failed: {e}")
            return await self._scrape_profile_fallback_system(url, fields)

    async def _scrape_profile_fallback_system(
        self, url: str, fields: PersonScrapingFields
    ) -> Person:
        """Emergency fallback scraping with minimal extraction."""
        # Validate URL
        linkedin_url = HttpUrl(url)
        logger.warning(f"Using emergency fallback system for: {url}")

        # Initialize Person model with minimal data
        person = Person(linkedin_url=linkedin_url)

        try:
            # Basic navigation
            await self.page.goto(str(linkedin_url))
            await self.page.wait_for_load_state("networkidle")
            await random_delay(2.0, 4.0)

            # Basic name extraction only (emergency fallback)
            try:
                name_element = self.page.locator("h1").first
                if await name_element.is_visible():
                    person.name = await name_element.inner_text()
            except Exception:
                pass

            logger.warning("Emergency fallback completed with minimal data")
            return person

        except Exception as e:
            logger.error(f"Emergency fallback failed: {e}")
            person.scraping_errors["emergency_fallback"] = str(e)
            raise LinkedInDetectionError(f"All scraping methods failed: {e}")