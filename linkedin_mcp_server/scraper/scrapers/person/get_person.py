"""Stealth-enhanced person profile scraper using Playwright."""

import logging
from playwright.async_api import Page
from pydantic import HttpUrl

from ...config import PersonScrapingFields, LinkedInDetectionError
from ...models.person import Person
from ...browser.behavioral import (
    navigate_to_profile_stealthily,
    simulate_profile_reading_behavior,
    detect_linkedin_challenge,
    random_delay,
)
from .accomplishments import scrape_accomplishments
from .contacts import scrape_contacts
from .education import scrape_educations_main_page
from .experience import scrape_experiences_main_page
from .interests import scrape_interests

logger = logging.getLogger(__name__)


class PersonScraper:
    """Scraper for LinkedIn person profiles."""

    def __init__(self, page: Page):
        """Initialize the scraper with a Playwright page.

        Args:
            page: Authenticated Playwright page instance
        """
        self.page = page

    async def scrape_profile(
        self, url: str, fields: PersonScrapingFields = PersonScrapingFields.MINIMAL
    ) -> Person:
        """Scrape a LinkedIn person profile using stealth navigation patterns.

        Args:
            url: LinkedIn profile URL as string
            fields: PersonScrapingFields enum specifying which fields to scrape

        Returns:
            Person model with scraped data

        Raises:
            LinkedInDetectionError: If LinkedIn detection is suspected
        """
        # Validate URL
        linkedin_url = HttpUrl(url)
        logger.info(f"Starting stealth profile scraping for: {url}")

        # Initialize Person model
        person = Person(linkedin_url=linkedin_url)

        try:
            # Stealth navigation to profile using search-first approach
            await navigate_to_profile_stealthily(self.page, str(linkedin_url))

            # Check for detection after navigation
            if await detect_linkedin_challenge(self.page):
                raise LinkedInDetectionError(
                    "LinkedIn challenge detected during profile access"
                )

            # Simulate human profile reading behavior
            await simulate_profile_reading_behavior(self.page)

            # Add small delay before starting data extraction
            await random_delay(1.0, 2.0)

        except LinkedInDetectionError:
            logger.error("LinkedIn detection during profile navigation")
            raise
        except Exception as e:
            logger.error(f"Profile navigation failed: {e}")
            person.scraping_errors["navigation"] = str(e)
            # Try fallback direct navigation (riskier but might work)
            try:
                await self.page.goto(str(linkedin_url), wait_until="networkidle")
                await random_delay(2.0, 4.0)
            except Exception as fallback_error:
                raise LinkedInDetectionError(
                    f"Both stealth and fallback navigation failed: {fallback_error}"
                )

        # Start data extraction with stealth delays
        logger.debug("Starting data extraction with human-like timing")

        # Always scrape basic information (it's on the main page)
        if PersonScrapingFields.BASIC_INFO in fields:
            try:
                await self._scrape_basic_info(person)
                # Human-like delay between sections
                await random_delay(1.5, 3.0)
            except Exception as e:
                logger.warning(f"Basic info scraping failed: {e}")
                person.scraping_errors["basic_info"] = str(e)

        # Check for detection after basic scraping
        if await detect_linkedin_challenge(self.page):
            raise LinkedInDetectionError("Detection suspected during profile scraping")

        # Conditionally scrape other fields with error isolation and stealth timing
        if PersonScrapingFields.EXPERIENCE in fields:
            try:
                logger.debug("Scraping experience section")
                await scrape_experiences_main_page(self.page, person)
                await random_delay(2.0, 4.0)  # Longer delays for section navigation
            except Exception as e:
                logger.warning(f"Experience scraping failed: {e}")
                person.scraping_errors["experience"] = str(e)

        if PersonScrapingFields.EDUCATION in fields:
            try:
                logger.debug("Scraping education section")
                await scrape_educations_main_page(self.page, person)
                await random_delay(2.0, 4.0)
            except Exception as e:
                logger.warning(f"Education scraping failed: {e}")
                person.scraping_errors["education"] = str(e)

        if PersonScrapingFields.INTERESTS in fields:
            try:
                logger.debug("Scraping interests section")
                await scrape_interests(self.page, person)
                await random_delay(2.0, 4.0)
            except Exception as e:
                logger.warning(f"Interests scraping failed: {e}")
                person.scraping_errors["interests"] = str(e)

        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            try:
                logger.debug("Scraping accomplishments section")
                await scrape_accomplishments(self.page, person)
                await random_delay(2.0, 4.0)
            except Exception as e:
                logger.warning(f"Accomplishments scraping failed: {e}")
                person.scraping_errors["accomplishments"] = str(e)

        if PersonScrapingFields.CONTACTS in fields:
            try:
                logger.debug("Scraping contacts section")
                await scrape_contacts(self.page, person)
                await random_delay(2.0, 4.0)
            except Exception as e:
                logger.warning(f"Contacts scraping failed: {e}")
                person.scraping_errors["contacts"] = str(e)

        # Final detection check
        if await detect_linkedin_challenge(self.page):
            logger.warning(
                "Challenge detected after profile scraping - profile may be incomplete"
            )
            person.scraping_errors["post_scraping_challenge"] = (
                "LinkedIn challenge detected"
            )

        logger.info(f"Profile scraping completed for: {url}")
        return person

    async def _scrape_basic_info(self, person: Person) -> None:
        """Scrape basic profile information using robust proven selectors."""
        from .selectors import LinkedInSelectors, PerformanceBenchmark
        from ...browser.behavioral import simulate_profile_reading_behavior

        logger.info("Starting basic info extraction with proven selectors")

        with PerformanceBenchmark.time_section("basic_info", logger) as timer:
            # CRITICAL: Use existing stealth behavior - DO NOT MODIFY
            await simulate_profile_reading_behavior(self.page)

            # Extract name using proven selector
            try:
                name_element = self.page.locator(LinkedInSelectors.PROFILE_NAME).first
                if await name_element.is_visible():
                    name_text = (await name_element.inner_text()).strip()
                    if name_text:
                        person.name = name_text
                        logger.debug(f"Extracted name: {name_text}")
            except Exception as e:
                logger.warning(f"Name extraction failed: {e}")

            # Extract headline using proven selector fallback chain
            try:
                headline_found = False
                for selector in LinkedInSelectors.PROFILE_HEADLINE:
                    try:
                        headline_element = self.page.locator(selector).first
                        if await headline_element.is_visible():
                            headline_text = (
                                await headline_element.inner_text()
                            ).strip()
                            # Validate headline: not empty, not same as name, substantial content
                            if (
                                headline_text
                                and headline_text != person.name
                                and len(headline_text) > 5
                                and headline_text not in ["", "null", "undefined"]
                            ):
                                person.add_headline(headline_text)
                                logger.debug(f"Extracted headline: {headline_text}")
                                headline_found = True
                                break
                    except Exception:
                        continue

                if not headline_found:
                    logger.debug("No headline found with proven selectors")

            except Exception as e:
                logger.warning(f"Headline extraction failed: {e}")

            # Extract location using proven selector fallback chain
            try:
                location_found = False
                for selector in LinkedInSelectors.PROFILE_LOCATION:
                    try:
                        location_element = self.page.locator(selector).first
                        if await location_element.is_visible():
                            location_text = (
                                await location_element.inner_text()
                            ).strip()
                            if location_text:
                                person.add_location(location_text)
                                logger.debug(f"Extracted location: {location_text}")
                                location_found = True
                                break
                    except Exception:
                        continue

                if not location_found:
                    logger.debug("No location found with proven selectors")

            except Exception as e:
                logger.warning(f"Location extraction failed: {e}")

            # Extract about section using proven selectors
            try:
                about_found = False
                for selector in LinkedInSelectors.PROFILE_ABOUT:
                    try:
                        about_element = self.page.locator(selector).first
                        if await about_element.is_visible():
                            about_text = (await about_element.inner_text()).strip()
                            if about_text:
                                person.add_about(about_text)
                                logger.debug(f"Extracted about: {about_text[:100]}...")
                                about_found = True
                                break
                    except Exception:
                        continue

                if not about_found:
                    logger.debug("No about section found with proven selectors")

            except Exception as e:
                logger.warning(f"About extraction failed: {e}")

            # Extract open to work status
            try:
                profile_picture = self.page.locator(
                    ".pv-top-card-profile-picture img"
                ).first
                if await profile_picture.is_visible():
                    title_attr = await profile_picture.get_attribute("title")
                    person.open_to_work = title_attr and "#OPEN_TO_WORK" in title_attr
                    logger.debug(f"Open to work status: {person.open_to_work}")
                else:
                    person.open_to_work = False
            except Exception as e:
                logger.warning(f"Open to work extraction failed: {e}")
                person.open_to_work = False

            # Set item count for benchmarking (1 for basic info section)
            timer.set_item_count(1)

        logger.info("Basic info extraction completed")
