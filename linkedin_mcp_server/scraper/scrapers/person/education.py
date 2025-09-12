"""Education scraping module for LinkedIn profiles.

Main-page-only extraction using proven CSS selectors to avoid session kick-outs.
Based on successful patterns from legacy selenium implementation.
"""

import logging
from typing import List, Optional

from playwright.async_api import Page, Locator
from pydantic import HttpUrl

from ...models.person import Person, Education
from ...browser.behavioral import simulate_profile_reading_behavior
from .selectors import LinkedInSelectors, PerformanceBenchmark
from .utils import (
    clean_single_string_duplicates,
    extract_description_and_skills,
    is_date_range,
    parse_date_range_smart,
)

logger = logging.getLogger(__name__)


async def scrape_educations_main_page(page: Page, person: Person) -> None:
    """Extract educations from main profile page only - using proven selectors.

    This function stays on the main profile page and uses the proven selector pattern
    div[data-view-name='profile-component-entity'] that successfully generated the
    testdata/testscrape.txt baseline (4 educations).

    Args:
        page: Playwright page instance (already on main profile page)
        person: Person model to populate with education data
    """
    logger.info("Starting main-page education extraction")

    with PerformanceBenchmark.time_section("education", logger) as timer:
        # CRITICAL: Use existing stealth behavior to avoid detection
        await simulate_profile_reading_behavior(page)

        # Find education section using proven selector
        education_section = None

        # Try primary selector first
        try:
            education_section = page.locator(LinkedInSelectors.EDUCATION_SECTION).first
            if not await education_section.is_visible():
                education_section = None
        except Exception:
            education_section = None

        # Fall back to alternative selectors if needed
        if not education_section:
            for alt_selector in LinkedInSelectors.EDUCATION_SECTION_ALT:
                try:
                    section = page.locator(alt_selector).first
                    if await section.is_visible():
                        education_section = section
                        logger.debug(
                            f"Education section found with fallback: {alt_selector}"
                        )
                        break
                except Exception:
                    continue

        if not education_section:
            logger.warning("Education section not found on main page")
            timer.set_item_count(0)
            return

        # Scroll to reveal content (LinkedIn lazy-loads)
        await education_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(2000)

        # Extract education items using proven selector
        extracted_count = 0

        # Try primary item selector
        try:
            education_items = await education_section.locator(
                LinkedInSelectors.EDUCATION_ITEMS
            ).all()

            logger.debug(
                f"Found {len(education_items)} education items with primary selector"
            )

            if education_items:
                extracted_count = await _extract_educations_from_items(
                    education_items, person
                )

        except Exception as e:
            logger.warning(f"Primary education selector failed: {e}")

        # Fall back to alternative selectors if primary failed
        if extracted_count == 0:
            for alt_selector in LinkedInSelectors.EDUCATION_ITEMS_ALT:
                try:
                    education_items = await education_section.locator(
                        alt_selector
                    ).all()
                    logger.debug(
                        f"Trying fallback selector {alt_selector}: found {len(education_items)} items"
                    )

                    if education_items:
                        extracted_count = await _extract_educations_from_items(
                            education_items, person
                        )
                        if extracted_count > 0:
                            logger.debug(
                                f"Successfully extracted {extracted_count} educations with fallback"
                            )
                            break

                except Exception as e:
                    logger.debug(f"Fallback selector {alt_selector} failed: {e}")
                    continue

        timer.set_item_count(extracted_count)

        if extracted_count == 0:
            logger.warning("No educations extracted - selectors may be outdated")
        else:
            logger.info(
                f"Successfully extracted {extracted_count} educations from main page"
            )


async def _extract_educations_from_items(
    education_items: List[Locator], person: Person
) -> int:
    """Extract education data from a list of education item locators.

    Args:
        education_items: List of Playwright locators for education items
        person: Person model to add educations to

    Returns:
        Number of educations successfully extracted
    """
    extracted_count = 0

    for item in education_items:
        try:
            education = await _extract_single_education(item)
            if education:
                person.add_education(education)
                extracted_count += 1
                logger.debug(
                    f"Extracted education: {education.degree} from {education.institution_name}"
                )

        except Exception as e:
            logger.debug(f"Failed to extract single education: {e}")
            continue

    return extracted_count


async def _extract_single_education(item: Locator) -> Optional[Education]:
    """Extract education data from a single education item.

    This follows the proven extraction pattern that generated testscrape.txt,
    focusing on clean text extraction and proper field mapping to match the baseline format.

    Args:
        item: Playwright locator for single education item

    Returns:
        Education object or None if extraction fails
    """
    try:
        # Get main elements - logo and details (proven pattern)
        elements = await item.locator("> *").all()
        if len(elements) < 2:
            return None

        institution_logo_elem = elements[0]
        position_details = elements[1]

        # Extract institution LinkedIn URL
        institution_linkedin_url = await _extract_institution_url(institution_logo_elem)

        # Extract education details
        position_details_list = await position_details.locator("> *").all()
        position_summary_details = (
            position_details_list[0] if len(position_details_list) > 0 else None
        )
        position_summary_text = (
            position_details_list[1] if len(position_details_list) > 1 else None
        )

        if not position_summary_details:
            return None

        # Extract education information using proven parsing
        education_info = await _extract_education_info(position_summary_details)

        # Extract description and skills from summary text
        description = ""
        skills = []
        if position_summary_text and await position_summary_text.is_visible():
            raw_text = await position_summary_text.inner_text()
            logger.debug(f"Education raw text: {repr(raw_text)}")
            # Clean single element duplicates before processing
            cleaned_text = clean_single_string_duplicates(raw_text)
            description, skills = extract_description_and_skills(cleaned_text)
            logger.debug(
                f"Education extracted - description: {repr(description)}, skills: {skills}"
            )

        # Create education object matching testscrape.txt format
        return Education(
            from_date=education_info.get("from_date") or None,
            to_date=education_info.get("to_date") or None,
            description=description if description else None,
            degree=education_info.get("degree") or None,
            institution_name=education_info.get("institution_name", ""),
            skills=skills,
            linkedin_url=HttpUrl(institution_linkedin_url)
            if institution_linkedin_url
            else None,
        )

    except Exception as e:
        logger.debug(f"Single education extraction failed: {e}")
        return None


async def _extract_institution_url(institution_logo_elem: Locator) -> Optional[str]:
    """Extract institution LinkedIn URL from logo element."""
    try:
        link_elem = institution_logo_elem.locator("> *").first
        if await link_elem.is_visible():
            href = await link_elem.get_attribute("href")
            return href if href else None
    except Exception:
        pass
    return None


async def _extract_education_info(position_summary_details: Locator) -> dict:
    """Extract education information from position summary element.

    This uses proven parsing logic to extract institution name, degree, and dates
    in a format that matches the testscrape.txt baseline.
    """
    education_info = {
        "institution_name": "",
        "degree": "",
        "from_date": "",
        "to_date": "",
    }

    try:
        outer_positions = (
            await position_summary_details.locator("> *").locator("> *").all()
        )

        # Extract institution name (first element)
        if len(outer_positions) > 0:
            institution_span = outer_positions[0].locator("span").first
            if await institution_span.is_visible():
                education_info["institution_name"] = await institution_span.inner_text()

        # Intelligently extract degree and dates using regex validation
        for i in range(1, len(outer_positions)):
            span = outer_positions[i].locator("span").first
            if await span.is_visible():
                text = await span.inner_text()

                # Use regex to check if this text is a date range
                if is_date_range(text) and not education_info["from_date"]:
                    # This is the dates field - use smart parser
                    from_date, to_date = parse_date_range_smart(text)
                    education_info["from_date"] = from_date
                    education_info["to_date"] = to_date
                elif not is_date_range(text) and not education_info["degree"]:
                    # This is the degree field
                    education_info["degree"] = text

    except Exception as e:
        logger.debug(f"Education info extraction failed: {e}")
        pass

    return education_info


# Keep existing helper functions for compatibility
async def scrape_educations(page: Page, person: Person) -> None:
    """Legacy function - redirects to main-page-only version.

    This maintains API compatibility while using the new main-page-only approach.
    """
    logger.warning("Legacy scrape_educations called - using main-page-only version")
    await scrape_educations_main_page(page, person)


async def _extract_institution_url(institution_logo_elem: Locator) -> Optional[str]:
    """Extract institution LinkedIn URL from logo element."""
    try:
        link_elem = institution_logo_elem.locator("> *").first
        if await link_elem.is_visible():
            href = await link_elem.get_attribute("href")
            return href if href else None
    except Exception:
        pass
    return None


async def _extract_education_info(position_summary_details: Locator) -> dict:
    """Extract education information from position summary element."""
    education_info = {
        "institution_name": "",
        "degree": "",
        "from_date": "",
        "to_date": "",
    }

    try:
        outer_positions = (
            await position_summary_details.locator("> *").locator("> *").all()
        )

        # Extract institution name
        if len(outer_positions) > 0:
            institution_span = outer_positions[0].locator("span").first
            if await institution_span.is_visible():
                education_info["institution_name"] = await institution_span.inner_text()

        # Intelligently extract degree and dates using regex validation
        for i in range(1, len(outer_positions)):
            span = outer_positions[i].locator("span").first
            if await span.is_visible():
                text = await span.inner_text()

                # Use regex to check if this text is a date range
                if is_date_range(text) and not education_info["from_date"]:
                    # This is the dates field - use smart parser
                    from_date, to_date = parse_date_range_smart(text)
                    education_info["from_date"] = from_date
                    education_info["to_date"] = to_date
                elif not is_date_range(text) and not education_info["degree"]:
                    # This is the degree field
                    education_info["degree"] = text

    except Exception:
        pass

    return education_info
