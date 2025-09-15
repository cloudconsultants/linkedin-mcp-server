"""Unified LinkedIn profile page scraper using centralized stealth architecture."""

import logging
from typing import List

from patchright.async_api import Page

from linkedin_mcp_server.scraper.config import PersonScrapingFields
from linkedin_mcp_server.scraper.models.person import Person
from linkedin_mcp_server.scraper.pages.base import LinkedInPageScraper
from linkedin_mcp_server.scraper.stealth.controller import ContentTarget, PageType

logger = logging.getLogger(__name__)


class ProfilePageScraper(LinkedInPageScraper):
    """Unified LinkedIn profile page scraper.

    This scraper replaces the scattered section-based approach with a single
    unified scraper that uses centralized stealth operations and parallel
    data extraction for maximum performance.
    """

    def get_page_type(self) -> PageType:
        """Get the page type for profile scraping."""
        return PageType.PROFILE

    def get_content_targets(
        self, fields: PersonScrapingFields = PersonScrapingFields.ALL
    ) -> List[ContentTarget]:
        """Map PersonScrapingFields to ContentTargets for intelligent loading.

        Args:
            fields: Person scraping fields to determine content targets

        Returns:
            List of ContentTarget enums for the requested fields
        """
        targets = []

        if PersonScrapingFields.BASIC_INFO in fields:
            targets.append(ContentTarget.BASIC_INFO)

        if PersonScrapingFields.EXPERIENCE in fields:
            targets.append(ContentTarget.EXPERIENCE)

        if PersonScrapingFields.EDUCATION in fields:
            targets.append(ContentTarget.EDUCATION)

        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            targets.extend(
                [
                    ContentTarget.SKILLS,
                    ContentTarget.ACCOMPLISHMENTS,
                ]
            )

        if PersonScrapingFields.INTERESTS in fields:
            targets.append(ContentTarget.INTERESTS)

        if PersonScrapingFields.CONTACTS in fields:
            targets.append(ContentTarget.CONTACTS)

        return targets

    async def extract_data(
        self,
        page: Page,
        fields: PersonScrapingFields = PersonScrapingFields.ALL,
        **kwargs,
    ) -> Person:
        """Extract profile data from the loaded page.

        This method performs parallel extraction of all requested sections
        after stealth operations are complete, achieving significant performance
        improvements over the sequential section-based approach.

        Args:
            page: Patchright page instance with content loaded
            fields: Fields to extract from the profile
            **kwargs: Additional extraction parameters

        Returns:
            Person model with extracted data
        """
        logger.info("Starting unified profile data extraction")

        # Initialize person with URL
        person = Person()
        if hasattr(kwargs, "url"):
            person.linkedin_url = kwargs.get("url")
        else:
            try:
                person.linkedin_url = page.url
            except Exception:
                pass

        # Extract all requested sections in parallel
        extraction_tasks = []

        if PersonScrapingFields.BASIC_INFO in fields:
            extraction_tasks.append(self._extract_basic_info(page, person))

        if PersonScrapingFields.EXPERIENCE in fields:
            extraction_tasks.append(self._extract_experiences(page, person))

        if PersonScrapingFields.EDUCATION in fields:
            extraction_tasks.append(self._extract_education(page, person))

        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            extraction_tasks.append(self._extract_accomplishments(page, person))

        if PersonScrapingFields.INTERESTS in fields:
            extraction_tasks.append(self._extract_interests(page, person))

        if PersonScrapingFields.CONTACTS in fields:
            extraction_tasks.append(self._extract_contacts(page, person))

        # Execute all extractions in parallel
        import asyncio

        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Log extraction results
        sections = []
        if PersonScrapingFields.BASIC_INFO in fields:
            sections.append("basic_info")
        if PersonScrapingFields.EXPERIENCE in fields:
            sections.append("experience")
        if PersonScrapingFields.EDUCATION in fields:
            sections.append("education")
        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            sections.append("accomplishments")
        if PersonScrapingFields.INTERESTS in fields:
            sections.append("interests")
        if PersonScrapingFields.CONTACTS in fields:
            sections.append("contacts")

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self._handle_extraction_error(sections[i], result)
                person.scraping_errors[sections[i]] = str(result)
            else:
                self._log_extraction_progress(sections[i], True)

        logger.info(
            f"Profile extraction complete: "
            f"{len([r for r in results if not isinstance(r, Exception)])} sections successful, "
            f"{len([r for r in results if isinstance(r, Exception)])} failed"
        )

        return person

    async def scrape_profile_page(
        self,
        page: Page,
        url: str,
        fields: PersonScrapingFields = PersonScrapingFields.ALL,
    ) -> Person:
        """Convenience method for profile scraping with field specification.

        Args:
            page: Patchright page instance
            url: LinkedIn profile URL
            fields: Fields to extract from the profile

        Returns:
            Person model with extracted data
        """
        return await self.scrape_page(page, url, fields=fields)

    # Private extraction methods for each section

    async def _extract_basic_info(self, page: Page, person: Person) -> None:
        """Extract basic profile information."""
        try:
            # Name
            name_selectors = [
                "h1.text-heading-xlarge",
                ".pv-text-details__left-panel h1",
                "[data-generated-suggestion-target]",
                "h1",
            ]

            for selector in name_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        name = await element.inner_text()
                        if name.strip():
                            person.name = name.strip()
                            break
                except Exception:
                    continue

            # Headline
            headline_selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium",
                "[data-generated-suggestion-target] + .text-body-medium",
            ]

            for selector in headline_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        headline = await element.inner_text()
                        if headline.strip():
                            person.headline = headline.strip()
                            break
                except Exception:
                    continue

            # Location
            location_selectors = [
                ".text-body-small.inline.t-black--light",
                ".pv-text-details__right-panel .text-body-small",
                ".mt2 .text-body-small",
            ]

            for selector in location_selectors:
                try:
                    elements = await page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            text = await element.inner_text()
                            # Simple heuristic: locations often contain city/state patterns
                            if any(
                                char in text
                                for char in [",", "CA", "NY", "Area", "Region"]
                            ):
                                person.location = text.strip()
                                break
                    if person.location:
                        break
                except Exception:
                    continue

            # About section
            about_selectors = [
                ".pv-about-section .pv-shared-text-with-see-more",
                ".pv-about-section .inline-show-more-text",
                "#about + * .pv-shared-text-with-see-more",
            ]

            for selector in about_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible():
                        about_text = await element.inner_text()
                        if about_text.strip():
                            person.about = [about_text.strip()]
                            break
                except Exception:
                    continue

            logger.debug("Basic info extraction completed")

        except Exception as e:
            logger.error(f"Basic info extraction failed: {e}")
            raise

    async def _extract_experiences(self, page: Page, person: Person) -> None:
        """Extract work experience using existing proven logic."""
        try:
            # Import existing extraction logic
            from linkedin_mcp_server.scraper.scrapers.person.experience import (
                scrape_experiences_main_page,
            )

            # Use existing proven extraction method
            await scrape_experiences_main_page(page, person)

            logger.debug(f"Extracted {len(person.experiences)} experiences")

        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")
            raise

    async def _extract_education(self, page: Page, person: Person) -> None:
        """Extract education information."""
        try:
            # Import existing extraction logic
            from linkedin_mcp_server.scraper.scrapers.person.education import (
                scrape_education_main_page,
            )

            # Use existing proven extraction method
            await scrape_education_main_page(page, person)

            logger.debug(f"Extracted {len(person.educations)} education entries")

        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            # Don't raise - education is optional
            pass

    async def _extract_accomplishments(self, page: Page, person: Person) -> None:
        """Extract accomplishments (honors, languages, skills)."""
        try:
            # Import existing extraction logic
            from linkedin_mcp_server.scraper.scrapers.person.accomplishments import (
                scrape_accomplishments_main_page,
            )

            # Use existing proven extraction method
            await scrape_accomplishments_main_page(page, person)

            logger.debug(
                f"Extracted {len(person.honors)} honors, "
                f"{len(person.languages)} languages"
            )

        except Exception as e:
            logger.error(f"Accomplishments extraction failed: {e}")
            # Don't raise - accomplishments are optional
            pass

    async def _extract_interests(self, page: Page, person: Person) -> None:
        """Extract interests and following information."""
        try:
            # Import existing extraction logic
            from linkedin_mcp_server.scraper.scrapers.person.interests import (
                scrape_interests_main_page,
            )

            # Use existing proven extraction method
            await scrape_interests_main_page(page, person)

            logger.debug(f"Extracted {len(person.interests)} interests")

        except Exception as e:
            logger.error(f"Interests extraction failed: {e}")
            # Don't raise - interests are optional
            pass

    async def _extract_contacts(self, page: Page, person: Person) -> None:
        """Extract contact information and connections."""
        try:
            # Import existing extraction logic
            from linkedin_mcp_server.scraper.scrapers.person.contacts import (
                scrape_contact_info,
            )
            from linkedin_mcp_server.scraper.scrapers.person.connections import (
                scrape_connections_info,
            )

            # Extract contact info and connections
            await scrape_contact_info(page, person)
            await scrape_connections_info(page, person)

            logger.debug(
                f"Extracted contact info and {len(person.connections)} connections"
            )

        except Exception as e:
            logger.error(f"Contacts extraction failed: {e}")
            # Don't raise - contacts are optional
            pass
