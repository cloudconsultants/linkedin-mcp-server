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
    random_delay
)
from .accomplishments import scrape_accomplishments
from .contacts import scrape_contacts
from .education import scrape_educations
from .experience import scrape_experiences
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
                raise LinkedInDetectionError("LinkedIn challenge detected during profile access")
            
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
                raise LinkedInDetectionError(f"Both stealth and fallback navigation failed: {fallback_error}")

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
                await scrape_experiences(self.page, person)
                await random_delay(2.0, 4.0)  # Longer delays for section navigation
            except Exception as e:
                logger.warning(f"Experience scraping failed: {e}")
                person.scraping_errors["experience"] = str(e)

        if PersonScrapingFields.EDUCATION in fields:
            try:
                logger.debug("Scraping education section")
                await scrape_educations(self.page, person)
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
            logger.warning("Challenge detected after profile scraping - profile may be incomplete")
            person.scraping_errors["post_scraping_challenge"] = "LinkedIn challenge detected"

        logger.info(f"Profile scraping completed for: {url}")
        return person

    async def _scrape_basic_info(self, person: Person) -> None:
        """Scrape basic profile information (name, location, about)."""
        # Get name and location
        try:
            top_panel = self.page.locator(".mt2.relative").first
            name_element = top_panel.locator("h1").first
            if await name_element.is_visible():
                person.name = await name_element.inner_text()
        except Exception:
            pass

        try:
            location_element = self.page.locator(
                ".text-body-small.inline.t-black--light.break-words"
            ).first
            if await location_element.is_visible():
                person.add_location(await location_element.inner_text())
        except Exception:
            pass

        # Get headline - simplified approach based on DOM structure
        try:
            # From MCP DOM analysis, the headline appears right after the name
            # Try multiple selectors that should work universally
            headline_selectors = [
                # Direct approach: find h1 then get the next generic element
                "h1 + div",
                "h1 ~ div:first-of-type",
                # Alternative: look in the main profile section
                ".mt2.relative div:has(h1) + div",
                # Fallback: find elements that typically contain headlines
                ".pv-text-details__left-panel > div:nth-child(2)",
                ".pv-top-card-v2-section-info > div:nth-child(2)",
            ]

            for selector in headline_selectors:
                headline_element = self.page.locator(selector).first
                if await headline_element.is_visible():
                    headline_text = (await headline_element.inner_text()).strip()
                    # Make sure it's not the name and has substantial content
                    if (
                        headline_text
                        and headline_text != person.name
                        and len(headline_text) > 5
                        and headline_text not in ["", "null", "undefined"]
                    ):
                        person.add_headline(headline_text)
                        break
        except Exception:
            pass

        # Get about section - following Selenium approach exactly
        try:
            about = (
                self.page.locator("#about").locator("..").locator(".display-flex").first
            )
            if await about.is_visible():
                about_text = await about.inner_text()
                person.add_about(about_text)
        except Exception:
            pass

        # Check if open to work
        try:
            profile_picture = self.page.locator(
                ".pv-top-card-profile-picture img"
            ).first
            if await profile_picture.is_visible():
                title_attr = await profile_picture.get_attribute("title")
                person.open_to_work = title_attr and "#OPEN_TO_WORK" in title_attr
        except Exception:
            person.open_to_work = False
