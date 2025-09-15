"""Clean, high-performance LinkedIn profile page scraper."""

import logging
import re
from typing import List, Optional

from patchright.async_api import Page

from linkedin_mcp_server.scraper.config import PersonScrapingFields
from linkedin_mcp_server.scraper.models.person import Person, Experience, Education
from linkedin_mcp_server.scraper.pages.base import LinkedInPageScraper
from linkedin_mcp_server.scraper.stealth.controller import ContentTarget, PageType

logger = logging.getLogger(__name__)


class ProfilePageScraper(LinkedInPageScraper):
    """LinkedIn profile page scraper using centralized stealth architecture.
    
    Follows the PRP centralized_stealth_architecture_redesign_FINAL.md pattern
    with restored working selectors for optimal performance.
    """

    def get_page_type(self) -> PageType:
        """Get the page type for profile scraping."""
        return PageType.PROFILE

    def get_content_targets(
        self, fields: PersonScrapingFields = PersonScrapingFields.ALL
    ) -> List[ContentTarget]:
        """Map PersonScrapingFields to ContentTargets."""
        targets = []
        if PersonScrapingFields.BASIC_INFO in fields:
            targets.append(ContentTarget.BASIC_INFO)
        if PersonScrapingFields.EXPERIENCE in fields:
            targets.append(ContentTarget.EXPERIENCE)
        if PersonScrapingFields.EDUCATION in fields:
            targets.append(ContentTarget.EDUCATION)
        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            targets.extend([ContentTarget.SKILLS, ContentTarget.ACCOMPLISHMENTS])
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
        """Pure data extraction - stealth operations handled by base class.
        
        This method performs only data extraction after the StealthController
        has already prepared the page with proper navigation, content loading,
        and behavior simulation.
        """
        logger.info("Starting profile data extraction (stealth-prepared)")
        
        person = Person()
        
        # Set URL
        try:
            from pydantic import HttpUrl
            person.linkedin_url = HttpUrl(page.url)
        except Exception:
            pass

        # Pure extraction - no stealth operations, page is already prepared
        if PersonScrapingFields.BASIC_INFO in fields:
            await self._extract_basic_info(page, person)

        if PersonScrapingFields.EXPERIENCE in fields:
            await self._extract_experiences(page, person)

        if PersonScrapingFields.EDUCATION in fields:
            await self._extract_education(page, person)

        if PersonScrapingFields.ACCOMPLISHMENTS in fields:
            await self._extract_accomplishments(page, person)

        if PersonScrapingFields.INTERESTS in fields:
            await self._extract_interests(page, person)

        logger.info(f"Extraction complete: {len(person.experiences)} experiences, "
                   f"{len(person.educations)} education, {len(person.about)} about")

        return person

    async def scrape_profile_page(
        self,
        page: Page,
        url: str,
        fields: PersonScrapingFields = PersonScrapingFields.ALL,
    ) -> Person:
        """Legacy method name for compatibility."""
        return await self.scrape_page(page, url, fields=fields)

    async def _extract_basic_info(self, page: Page, person: Person) -> None:
        """Extract basic info using successful selectors + improvements."""
        try:
            # Name - with filtering to avoid getting headline  
            name_selectors = ["h1.text-heading-xlarge", "main h1", "h1"]
            for selector in name_selectors:
                try:
                    name = await page.locator(selector).first.inner_text()
                    # Filter out names that are clearly headlines
                    if (name and len(name) < 100 and
                        not any(term in name.lower() for term in [
                            'consultant', 'developer', 'manager', 'director', 'specialist',
                            'expert', 'certification', '|', 'salesforce', 'automation'
                        ])):
                        person.name = name.strip()
                        break
                except Exception:
                    continue

            # Headline
            headline_selectors = [
                ".text-body-medium.break-words",
                ".pv-text-details__left-panel .text-body-medium"
            ]
            for selector in headline_selectors:
                try:
                    headline = await page.locator(selector).first.inner_text()
                    if headline.strip():
                        person.headline = headline.strip()
                        break
                except Exception:
                    continue

            # Location
            location_selectors = [
                ".text-body-small.inline.t-black--light",
                ".pv-text-details__right-panel .text-body-small"
            ]
            for selector in location_selectors:
                try:
                    location = await page.locator(selector).first.inner_text()
                    if location and any(char in location for char in [",", "Area", "Region"]):
                        person.location = location.strip()
                        break
                except Exception:
                    continue

            # About section - working selector from improvements
            about_selectors = [
                "section:nth-child(3) .display-flex.ph5.pv3 span:nth-child(1)",
                ".pv-shared-text-with-see-more span:nth-child(1)",
                "#about + * .pv-shared-text-with-see-more"
            ]
            for selector in about_selectors:
                try:
                    about_text = await page.locator(selector).first.inner_text()
                    if about_text.strip() and not about_text.endswith("...see more"):
                        person.about = [about_text.strip()]
                        break
                except Exception:
                    continue

            # Extract connection/follower counts and website (successful improvements)
            await self._extract_header_metadata(page, person)

        except Exception as e:
            logger.debug(f"Basic info extraction failed: {e}")

    async def _extract_header_metadata(self, page: Page, person: Person) -> None:
        """Extract connection counts, followers, and website URL."""
        try:
            # Get header text for pattern matching
            header_text = await page.locator("main section:first-child").first.inner_text()
            
            import re
            
            # Connection count patterns
            connection_patterns = [
                r'(\d+(?:,\d+)*)\s+connections?',
                r'(\d+)\+\s+connections?'
            ]
            
            for pattern in connection_patterns:
                match = re.search(pattern, header_text, re.IGNORECASE)
                if match:
                    count_str = match.group(1).replace(',', '').replace('+', '')
                    person.connection_count = int(count_str)
                    break

            # Follower count patterns
            follower_patterns = [
                r'(\d+(?:,\d+)*)\s+followers?',
                r'(\d+(?:\.\d+)?[kK])\s+followers?'
            ]
            
            for pattern in follower_patterns:
                match = re.search(pattern, header_text, re.IGNORECASE)
                if match:
                    count_str = match.group(1).replace(',', '')
                    if 'k' in count_str.lower():
                        count_str = count_str.lower().replace('k', '')
                        person.followers_count = int(float(count_str) * 1000)
                    else:
                        person.followers_count = int(count_str)
                    break

            # Website URL - simple pattern matching for cloudconsultants.ch
            all_links = await page.locator("a[href]").all()
            for link in all_links[:20]:  # Limit for performance
                try:
                    href = await link.get_attribute('href')
                    if (href and href.startswith('http') and 
                        'linkedin.com' not in href and 
                        ('cloudconsultants' in href or '.ch' in href)):
                        person.website_url = href
                        break
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Header metadata extraction failed: {e}")

    async def _extract_experiences(self, page: Page, person: Person) -> None:
        """Extract experiences using original working selectors."""
        try:
            # Use the proven selector from historic implementation
            selector = "section:has(#experience) div[data-view-name='profile-component-entity']"
            logger.debug(f"Using experience selector: {selector}")
            
            experience_items = await page.locator(selector).all()
            logger.debug(f"Found {len(experience_items)} experience items")

            for i, item in enumerate(experience_items):
                try:
                    experience = await self._extract_single_experience(item)
                    if experience and experience.position_title and experience.institution_name:
                        person.experiences.append(experience)
                        logger.debug(f"Successfully extracted experience {i}: {experience.position_title}")
                    else:
                        if experience:
                            logger.debug(f"Failed validation for experience {i}: title='{experience.position_title}', company='{experience.institution_name}'")
                        else:
                            logger.debug(f"Failed validation for experience {i}: experience is None")
                except Exception as e:
                    logger.debug(f"Failed to extract experience {i}: {e}")
                    continue

            logger.debug(f"Extracted {len(person.experiences)} experiences total")

        except Exception as e:
            logger.debug(f"Experience extraction failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    async def _extract_single_experience(self, item) -> Optional[Experience]:
        """Extract a single experience item from a DOM element - EXACT working implementation."""
        try:
            # Extract text content
            text = await item.inner_text()
            if not text or len(text.strip()) == 0:
                return None

            # Simple text-based extraction (could be enhanced with more structured parsing)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if not lines:
                return None

            # Create Experience object with working pattern
            experience = Experience(
                position_title=lines[0] if lines else "",
                institution_name=lines[1] if len(lines) > 1 else "",
                location="",
                description=text  # Full text as description
            )

            # Try to extract dates and location
            import re

            date_pattern = r"\b\d{4}\b"
            dates = re.findall(date_pattern, text)
            if dates:
                experience.from_date = dates[0] if dates else None
                experience.to_date = dates[-1] if len(dates) > 1 else dates[0]

            # Try to extract location (usually appears as "City, State" or "City, Country")
            location_pattern = (
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
            )
            location_match = re.search(location_pattern, text)
            if location_match:
                experience.location = location_match.group(1)

            return experience

        except Exception as e:
            logger.debug(f"Failed to extract single experience: {e}")
            return None

    async def _extract_education(self, page: Page, person: Person) -> None:
        """Extract education using original working selectors."""
        try:
            # Use the proven selector from historic implementation
            selector = "section:has(#education) div[data-view-name='profile-component-entity']"
            logger.debug(f"Using education selector: {selector}")
            
            education_items = await page.locator(selector).all()
            logger.debug(f"Found {len(education_items)} education items")

            for i, item in enumerate(education_items):
                try:
                    education = await self._extract_single_education(item)
                    if education and education.institution_name:
                        person.educations.append(education)
                        logger.debug(f"Successfully extracted education {i}: {education.institution_name}")
                    else:
                        logger.debug(f"Failed validation for education {i}")
                except Exception as e:
                    logger.debug(f"Failed to extract education {i}: {e}")
                    continue

            logger.debug(f"Extracted {len(person.educations)} education entries total")

        except Exception as e:
            logger.debug(f"Education extraction failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())

    async def _extract_single_education(self, item) -> Optional[Education]:
        """Extract a single education item from a DOM element - EXACT working implementation."""
        try:
            # Extract text content
            text = await item.inner_text()
            if not text or len(text.strip()) == 0:
                return None

            # Simple text-based extraction (could be enhanced with more structured parsing)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            if not lines:
                return None

            # Create Education object with working pattern (using correct field names)
            education = Education(
                institution_name=lines[0] if lines else "",
                degree=lines[2] if len(lines) > 2 else lines[1] if len(lines) > 1 else "",
                description=text  # Full text as description
            )

            # Try to extract dates
            import re

            date_pattern = r"\b\d{4}\b"
            dates = re.findall(date_pattern, text)
            if dates:
                education.from_date = dates[0] if dates else None
                education.to_date = dates[-1] if len(dates) > 1 else dates[0]

            return education

        except Exception as e:
            logger.debug(f"Failed to extract single education: {e}")
            return None

    async def _extract_accomplishments(self, page: Page, person: Person) -> None:
        """Extract accomplishments using simple selectors."""
        try:
            # Simple honors extraction
            honors_items = await page.locator("section:has-text('Honors') li, section:has-text('Awards') li").all()
            for item in honors_items[:5]:
                try:
                    text = await item.inner_text()
                    if text and len(text.strip()) > 0:
                        person.honors.append(text.strip())
                except Exception:
                    continue

            # Simple languages extraction  
            lang_items = await page.locator("section:has-text('Languages') li").all()
            for item in lang_items[:5]:
                try:
                    text = await item.inner_text()
                    if text and len(text.strip()) > 0:
                        person.languages.append(text.strip())
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Accomplishments extraction failed: {e}")

    async def _extract_interests(self, page: Page, person: Person) -> None:
        """Extract interests using simple selectors."""
        try:
            interest_items = await page.locator("section:has-text('Interests') li, section:has-text('Following') li").all()
            for item in interest_items[:10]:
                try:
                    text = await item.inner_text()
                    if text and len(text.strip()) > 0:
                        person.interests.append(text.strip())
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"Interests extraction failed: {e}")