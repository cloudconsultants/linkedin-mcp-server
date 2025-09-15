"""Unified LinkedIn profile page scraper using centralized stealth architecture."""

import logging
from typing import List, Optional

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
                # Convert string URL to HttpUrl type if needed
                from pydantic import HttpUrl
                person.linkedin_url = HttpUrl(page.url)
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
        """Extract work experience using consolidated logic."""
        try:
            logger.debug("Starting experience extraction")

            # Experience section selectors
            EXPERIENCE_SECTION = "section:has(#experience)"
            EXPERIENCE_SECTION_ALT = [
                "section[data-view-name='profile-experience']",
                "section:has-text('Experience')",
                "main section:has-text('Experience')",
            ]
            EXPERIENCE_ITEMS = "div[data-view-name='profile-component-entity']"
            EXPERIENCE_ITEMS_ALT = [
                "ul.pvs-list li",
                ".pvs-entity",
                ".pvs-list__paged-list-item",
            ]

            # Find experience section
            experience_section = None
            try:
                experience_section = page.locator(EXPERIENCE_SECTION).first
                if not await experience_section.is_visible():
                    experience_section = None
            except Exception:
                experience_section = None

            # Try fallback selectors
            if not experience_section:
                for alt_selector in EXPERIENCE_SECTION_ALT:
                    try:
                        section = page.locator(alt_selector).first
                        if await section.is_visible():
                            experience_section = section
                            break
                    except Exception:
                        continue

            if not experience_section:
                logger.debug("Experience section not found")
                return

            # Scroll to section
            await experience_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # Extract experience items
            experience_items = []
            try:
                experience_items = await experience_section.locator(EXPERIENCE_ITEMS).all()
            except Exception:
                # Try fallback selectors
                for alt_selector in EXPERIENCE_ITEMS_ALT:
                    try:
                        experience_items = await experience_section.locator(alt_selector).all()
                        if experience_items:
                            break
                    except Exception:
                        continue

            # Process each experience item
            for item in experience_items:
                try:
                    experience = await self._extract_single_experience(item)
                    if experience:
                        person.experiences.append(experience)
                except Exception as e:
                    logger.debug(f"Failed to extract experience item: {e}")
                    continue

            logger.debug(f"Extracted {len(person.experiences)} experiences")

        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")
            raise

    async def _extract_education(self, page: Page, person: Person) -> None:
        """Extract education information using consolidated logic."""
        try:
            logger.debug("Starting education extraction")

            # Education section selectors
            EDUCATION_SECTION = "section:has(#education)"
            EDUCATION_SECTION_ALT = [
                "section[data-view-name='profile-education']",
                "section:has-text('Education')",
                "main section:has-text('Education')",
            ]
            EDUCATION_ITEMS = "div[data-view-name='profile-component-entity']"
            EDUCATION_ITEMS_ALT = [
                "ul.pvs-list li",
                ".pvs-entity",
                ".pvs-list__paged-list-item",
            ]

            # Find education section
            education_section = None
            try:
                education_section = page.locator(EDUCATION_SECTION).first
                if not await education_section.is_visible():
                    education_section = None
            except Exception:
                education_section = None

            # Try fallback selectors
            if not education_section:
                for alt_selector in EDUCATION_SECTION_ALT:
                    try:
                        section = page.locator(alt_selector).first
                        if await section.is_visible():
                            education_section = section
                            break
                    except Exception:
                        continue

            if not education_section:
                logger.debug("Education section not found")
                return

            # Scroll to section
            await education_section.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)

            # Extract education items
            education_items = []
            try:
                education_items = await education_section.locator(EDUCATION_ITEMS).all()
            except Exception:
                # Try fallback selectors
                for alt_selector in EDUCATION_ITEMS_ALT:
                    try:
                        education_items = await education_section.locator(alt_selector).all()
                        if education_items:
                            break
                    except Exception:
                        continue

            # Process each education item
            for item in education_items:
                try:
                    education = await self._extract_single_education(item)
                    if education:
                        person.educations.append(education)
                except Exception as e:
                    logger.debug(f"Failed to extract education item: {e}")
                    continue

            logger.debug(f"Extracted {len(person.educations)} education entries")

        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            # Don't raise - education is optional

    async def _extract_accomplishments(self, page: Page, person: Person) -> None:
        """Extract accomplishments (honors, languages, skills) using consolidated logic."""
        try:
            logger.debug("Starting accomplishments extraction")

            # Look for accomplishments sections
            accomplishment_sections = [
                "section:has-text('Honors')",
                "section:has-text('Awards')",
                "section:has-text('Languages')",
                "section:has-text('Skills')",
                "section:has-text('Accomplishments')"
            ]

            for section_selector in accomplishment_sections:
                try:
                    section = page.locator(section_selector).first
                    if await section.is_visible():
                        await section.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)

                        # Extract items from this section
                        items = await section.locator("li, .pvs-entity").all()
                        for item in items:
                            try:
                                text = await item.inner_text()
                                if text and len(text.strip()) > 0:
                                    # Simple extraction - could be enhanced
                                    if "honor" in section_selector.lower() or "award" in section_selector.lower():
                                        person.honors.append(text.strip())
                                    elif "language" in section_selector.lower():
                                        person.languages.append(text.strip())
                            except Exception:
                                continue
                except Exception:
                    continue

            logger.debug(
                f"Extracted accomplishments: {len(person.honors)} honors, "
                f"{len(person.languages)} languages"
            )

        except Exception as e:
            logger.error(f"Accomplishments extraction failed: {e}")
            # Don't raise - accomplishments are optional

    async def _extract_interests(self, page: Page, person: Person) -> None:
        """Extract interests/following information using consolidated logic."""
        try:
            logger.debug("Starting interests extraction")

            # Look for interests sections
            interest_sections = [
                "section:has-text('Interests')",
                "section:has-text('Following')",
                "section[data-view-name='profile-interests']"
            ]

            for section_selector in interest_sections:
                try:
                    section = page.locator(section_selector).first
                    if await section.is_visible():
                        await section.scroll_into_view_if_needed()
                        await page.wait_for_timeout(500)

                        # Extract interest items
                        items = await section.locator("li, .pvs-entity, .follow-item").all()
                        for item in items:
                            try:
                                text = await item.inner_text()
                                if text and len(text.strip()) > 0:
                                    person.interests.append(text.strip())
                            except Exception:
                                continue
                except Exception:
                    continue

            logger.debug(f"Extracted {len(person.interests)} interests")

        except Exception as e:
            logger.error(f"Interests extraction failed: {e}")
            # Don't raise - interests are optional

    async def _extract_contacts(self, page: Page, person: Person) -> None:
        """Extract contact information using consolidated logic."""
        try:
            logger.debug("Starting contact extraction")

            # Extract connection count from profile header
            try:
                connection_elements = await page.locator(
                    "span:has-text('connection'), span:has-text('follower')"
                ).all()

                for element in connection_elements:
                    text = await element.inner_text()
                    # Extract number from text like "500+ connections"
                    import re
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        # Store as string for now (could be enhanced)
                        setattr(person, 'connections_count', text)
                        break
            except Exception:
                pass

            # Look for contact info button/section
            try:
                contact_button = page.locator("button:has-text('Contact info')")
                if await contact_button.is_visible():
                    # Could click and extract contact details
                    # For now, just note that contact info is available
                    pass
            except Exception:
                pass

            logger.debug("Extracted contact and connection information")

        except Exception as e:
            logger.error(f"Contact extraction failed: {e}")
            # Don't raise - contacts are optional

    async def _extract_single_education(self, item) -> Optional[dict]:
        """Extract a single education item from a DOM element."""
        try:
            # Extract text content
            text = await item.inner_text()
            if not text or len(text.strip()) == 0:
                return None

            # Simple text-based extraction (could be enhanced with more structured parsing)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None

            education = {
                'school': lines[0] if lines else '',
                'degree': lines[1] if len(lines) > 1 else '',
                'field_of_study': lines[2] if len(lines) > 2 else '',
                'description': '\n'.join(lines[3:]) if len(lines) > 3 else ''
            }

            # Try to extract dates
            import re
            date_pattern = r'\b\d{4}\b'
            dates = re.findall(date_pattern, text)
            if dates:
                education['start_year'] = dates[0] if dates else None
                education['end_year'] = dates[-1] if len(dates) > 1 else dates[0]

            return education

        except Exception as e:
            logger.debug(f"Failed to extract single education: {e}")
            return None

    async def _extract_single_experience(self, item) -> Optional[dict]:
        """Extract a single experience item from a DOM element."""
        try:
            # Extract text content
            text = await item.inner_text()
            if not text or len(text.strip()) == 0:
                return None

            # Simple text-based extraction (could be enhanced with more structured parsing)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if not lines:
                return None

            experience = {
                'job_title': lines[0] if lines else '',
                'company': lines[1] if len(lines) > 1 else '',
                'location': '',
                'description': '\n'.join(lines[2:]) if len(lines) > 2 else ''
            }

            # Try to extract dates and location
            import re
            date_pattern = r'\b\d{4}\b'
            dates = re.findall(date_pattern, text)
            if dates:
                experience['start_year'] = dates[0] if dates else None
                experience['end_year'] = dates[-1] if len(dates) > 1 else dates[0]

            # Try to extract location (usually appears as "City, State" or "City, Country")
            location_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            location_match = re.search(location_pattern, text)
            if location_match:
                experience['location'] = location_match.group(1)

            return experience

        except Exception as e:
            logger.debug(f"Failed to extract single experience: {e}")
            return None
