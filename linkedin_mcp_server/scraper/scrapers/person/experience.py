"""Experience scraping module for LinkedIn profiles.

Main-page-only extraction using proven CSS selectors to avoid session kick-outs.
Based on successful patterns from legacy selenium implementation.
"""

import logging
from typing import List, Optional

from playwright.async_api import Page, Locator
from pydantic import HttpUrl

from ...models.person import Person, Experience
from ...browser.behavioral import simulate_profile_reading_behavior
from .selectors import LinkedInSelectors, PerformanceBenchmark
from .utils import (
    clean_single_string_duplicates,
    extract_description_and_skills_from_element,
    is_date_range,
    is_employment_type,
    extract_employment_type,
    is_geographic_location,
)

logger = logging.getLogger(__name__)


async def scrape_experiences_main_page(page: Page, person: Person) -> None:
    """Extract experiences from main profile page only - using proven selectors.
    
    This function stays on the main profile page and uses the proven selector pattern
    div[data-view-name='profile-component-entity'] that successfully generated the
    testdata/testscrape.txt baseline (8 experiences).
    
    Args:
        page: Playwright page instance (already on main profile page)  
        person: Person model to populate with experiences
    """
    logger.info("Starting main-page experience extraction")
    
    with PerformanceBenchmark.time_section("experience", logger) as timer:
        # CRITICAL: Use existing stealth behavior to avoid detection
        await simulate_profile_reading_behavior(page)
        
        # Find experience section using proven selector
        experience_section = None
        
        # Try primary selector first
        try:
            experience_section = page.locator(LinkedInSelectors.EXPERIENCE_SECTION).first
            if not await experience_section.is_visible():
                experience_section = None
        except Exception:
            experience_section = None
            
        # Fall back to alternative selectors if needed
        if not experience_section:
            for alt_selector in LinkedInSelectors.EXPERIENCE_SECTION_ALT:
                try:
                    section = page.locator(alt_selector).first
                    if await section.is_visible():
                        experience_section = section
                        logger.debug(f"Experience section found with fallback: {alt_selector}")
                        break
                except Exception:
                    continue
                    
        if not experience_section:
            logger.warning("Experience section not found on main page")
            timer.set_item_count(0)
            return
            
        # Scroll to reveal content (LinkedIn lazy-loads)
        await experience_section.scroll_into_view_if_needed()
        await page.wait_for_timeout(2000)
        
        # Extract experience items using proven selector
        extracted_count = 0
        
        # Try primary item selector
        try:
            experience_items = await experience_section.locator(
                LinkedInSelectors.EXPERIENCE_ITEMS
            ).all()
            
            logger.debug(f"Found {len(experience_items)} experience items with primary selector")
            
            if experience_items:
                extracted_count = await _extract_experiences_from_items(
                    experience_items, person
                )
            
        except Exception as e:
            logger.warning(f"Primary experience selector failed: {e}")
            
        # Fall back to alternative selectors if primary failed
        if extracted_count == 0:
            for alt_selector in LinkedInSelectors.EXPERIENCE_ITEMS_ALT:
                try:
                    experience_items = await experience_section.locator(alt_selector).all()
                    logger.debug(f"Trying fallback selector {alt_selector}: found {len(experience_items)} items")
                    
                    if experience_items:
                        extracted_count = await _extract_experiences_from_items(
                            experience_items, person
                        )
                        if extracted_count > 0:
                            logger.debug(f"Successfully extracted {extracted_count} experiences with fallback")
                            break
                            
                except Exception as e:
                    logger.debug(f"Fallback selector {alt_selector} failed: {e}")
                    continue
        
        timer.set_item_count(extracted_count)
        
        if extracted_count == 0:
            logger.warning("No experiences extracted - selectors may be outdated")
        else:
            logger.info(f"Successfully extracted {extracted_count} experiences from main page")


async def _extract_experiences_from_items(
    experience_items: List[Locator], 
    person: Person
) -> int:
    """Extract experience data from a list of experience item locators.
    
    Args:
        experience_items: List of Playwright locators for experience items
        person: Person model to add experiences to
        
    Returns:
        Number of experiences successfully extracted
    """
    extracted_count = 0
    
    for item in experience_items:
        try:
            experience = await _extract_single_experience(item)
            if experience:
                person.add_experience(experience)
                extracted_count += 1
                logger.debug(f"Extracted experience: {experience.position_title} at {experience.institution_name}")
                
        except Exception as e:
            logger.debug(f"Failed to extract single experience: {e}")
            continue
            
    return extracted_count


async def _extract_single_experience(item: Locator) -> Optional[Experience]:
    """Extract experience data from a single experience item.
    
    This follows the proven extraction pattern that generated testscrape.txt,
    focusing on clean text extraction and proper field mapping to match the baseline format.
    
    Args:
        item: Playwright locator for single experience item
        
    Returns:
        Experience object or None if extraction fails
    """
    try:
        # Get main elements - logo and details (proven pattern)
        elements = await item.locator("> *").all()
        if len(elements) < 2:
            return None
            
        company_logo_elem = elements[0] 
        position_details = elements[1]
        
        # Extract company LinkedIn URL
        company_linkedin_url = await _extract_company_url(company_logo_elem)
        
        # Extract position details using proven parsing logic
        position_details_list = await position_details.locator("> *").all()
        position_summary_details = (
            position_details_list[0] if len(position_details_list) > 0 else None
        )
        position_summary_text = (
            position_details_list[1] if len(position_details_list) > 1 else None  
        )
        
        if not position_summary_details:
            return None
            
        # Extract position information using proven parsing
        position_info = await _parse_position_info(position_summary_details)
        
        # Check for multiple positions within same company (proven pattern)
        inner_positions = await _extract_inner_positions(position_summary_text)
        
        if len(inner_positions) > 1:
            # Handle multiple positions at same company - return the first one for now
            # This matches the testscrape.txt format where companies with multiple roles
            # are represented as separate experience entries
            inner_position = inner_positions[0]
            experience_data = await _extract_inner_position_data(inner_position)
            if experience_data:
                return Experience(
                    position_title=experience_data.get("position_title", ""),
                    from_date=experience_data.get("from_date", ""),
                    to_date=experience_data.get("to_date", ""),
                    duration=experience_data.get("duration"),
                    location=experience_data.get("location"),
                    employment_type=experience_data.get("employment_type"),
                    description=experience_data.get("description", ""),
                    skills=experience_data.get("skills", []),
                    institution_name=position_info.get("company", ""),
                    linkedin_url=HttpUrl(company_linkedin_url) if company_linkedin_url else None,
                )
        else:
            # Single position - extract description and skills
            description, skills = await extract_description_and_skills_from_element(
                position_summary_text
            )
            
            return Experience(
                position_title=position_info.get("position_title", ""),
                from_date=position_info.get("from_date", ""), 
                to_date=position_info.get("to_date", ""),
                duration=position_info.get("duration"),
                location=position_info.get("location", ""),
                employment_type=position_info.get("employment_type"),
                description=description,
                skills=skills,
                institution_name=position_info.get("company", ""),
                linkedin_url=HttpUrl(company_linkedin_url) if company_linkedin_url else None,
            )
            
    except Exception as e:
        logger.debug(f"Single experience extraction failed: {e}")
        return None


# Keep existing helper functions for compatibility
async def scrape_experiences(page: Page, person: Person) -> None:
    """Legacy function - redirects to main-page-only version.
    
    This maintains API compatibility while using the new main-page-only approach.
    """
    logger.warning("Legacy scrape_experiences called - using main-page-only version")
    await scrape_experiences_main_page(page, person)


async def _extract_company_url(company_logo_elem: Locator) -> Optional[str]:
    """Extract company LinkedIn URL from logo element."""
    try:
        link_elem = company_logo_elem.locator("> *").first
        if await link_elem.is_visible():
            href = await link_elem.get_attribute("href")
            return href if href else None
    except Exception:
        pass
    return None


async def _parse_position_info(outer_positions: List[Locator]) -> dict:
    """Parse position information from outer position elements - following Selenium approach."""
    position_info = {
        "position_title": "",
        "company": "",
        "work_times": "",
        "location": "",
        "employment_type": "",
        "from_date": "",
        "to_date": "",
        "duration": None,
    }

    try:
        # Follow Selenium logic exactly but with improved field classification
        if len(outer_positions) == 4:
            title_text = await outer_positions[0].locator("span").first.inner_text()
            position_info["position_title"] = clean_single_string_duplicates(title_text)
            company_text = await outer_positions[1].locator("span").first.inner_text()
            # Check if company text contains employment type after dot separator
            if "·" in company_text:
                company_parts = company_text.split("·")
                position_info["company"] = company_parts[0].strip()
                # Check if the part after dot is employment type
                if len(company_parts) > 1 and is_employment_type(
                    company_parts[1].strip()
                ):
                    position_info["employment_type"] = extract_employment_type(
                        company_parts[1].strip()
                    )
            else:
                position_info["company"] = company_text
            position_info["work_times"] = (
                await outer_positions[2].locator("span").first.inner_text()
            )

            # Smart classification for the 4th element (could be location or employment type)
            fourth_element_text = (
                await outer_positions[3].locator("span").first.inner_text()
            )
            if is_employment_type(fourth_element_text):
                # Only update if we don't already have an employment type from company text
                if not position_info["employment_type"]:
                    position_info["employment_type"] = extract_employment_type(
                        fourth_element_text
                    )
                position_info["location"] = ""
            elif is_geographic_location(fourth_element_text):
                position_info["location"] = fourth_element_text
                # Don't clear employment_type if already set from company text
            else:
                # Default to location for backward compatibility
                position_info["location"] = fourth_element_text
                # Don't clear employment_type if already set from company text
        elif len(outer_positions) == 3:
            # Check if second or third element contains work times (has ·, - and year patterns)
            second_element_text = await outer_positions[1].inner_text()
            third_element_text = await outer_positions[2].inner_text()

            # Check for date patterns using regex (more accurate than string checks)
            # Experience dates have format like "Oct 2024 - Apr 2025 · 7 mos"
            is_second_dates = "·" in second_element_text and any(
                is_date_range(part.strip()) for part in second_element_text.split("·")
            )
            is_third_dates = "·" in third_element_text and any(
                is_date_range(part.strip()) for part in third_element_text.split("·")
            )

            if is_second_dates:
                # Pattern: company, work_times, location/employment_type
                position_info["position_title"] = ""
                company_text = (
                    await outer_positions[0].locator("span").first.inner_text()
                )
                # Check if company text contains employment type after dot separator
                if "·" in company_text:
                    company_parts = company_text.split("·")
                    position_info["company"] = company_parts[0].strip()
                    # Check if the part after dot is employment type
                    if len(company_parts) > 1 and is_employment_type(
                        company_parts[1].strip()
                    ):
                        position_info["employment_type"] = extract_employment_type(
                            company_parts[1].strip()
                        )
                else:
                    position_info["company"] = company_text
                position_info["work_times"] = (
                    await outer_positions[1].locator("span").first.inner_text()
                )

                # Smart classification for the 3rd element
                third_element_text = (
                    await outer_positions[2].locator("span").first.inner_text()
                )
                if is_employment_type(third_element_text):
                    # Only update if we don't already have an employment type from company text
                    if not position_info["employment_type"]:
                        position_info["employment_type"] = extract_employment_type(
                            third_element_text
                        )
                    position_info["location"] = ""
                elif is_geographic_location(third_element_text):
                    position_info["location"] = third_element_text
                    # Don't clear employment_type if already set from company text
                else:
                    # Default to location for backward compatibility
                    position_info["location"] = third_element_text
                    # Don't clear employment_type if already set from company text
            elif is_third_dates:
                # Pattern: position_title, company, work_times
                title_text = await outer_positions[0].locator("span").first.inner_text()
                position_info["position_title"] = clean_single_string_duplicates(
                    title_text
                )
                company_text = (
                    await outer_positions[1].locator("span").first.inner_text()
                )
                # Check if company text contains employment type after dot separator
                if "·" in company_text:
                    company_parts = company_text.split("·")
                    position_info["company"] = company_parts[0].strip()
                    # Check if the part after dot is employment type
                    if len(company_parts) > 1 and is_employment_type(
                        company_parts[1].strip()
                    ):
                        position_info["employment_type"] = extract_employment_type(
                            company_parts[1].strip()
                        )
                else:
                    position_info["company"] = company_text
                position_info["work_times"] = (
                    await outer_positions[2].locator("span").first.inner_text()
                )
                position_info["location"] = ""
                # Don't clear employment_type if already set from company text
            else:
                # Fallback: assume no dates, treat as company, unknown, location/employment_type
                position_info["position_title"] = ""
                company_text = (
                    await outer_positions[0].locator("span").first.inner_text()
                )
                # Check if company text contains employment type after dot separator
                if "·" in company_text:
                    company_parts = company_text.split("·")
                    position_info["company"] = company_parts[0].strip()
                    # Check if the part after dot is employment type
                    if len(company_parts) > 1 and is_employment_type(
                        company_parts[1].strip()
                    ):
                        position_info["employment_type"] = extract_employment_type(
                            company_parts[1].strip()
                        )
                else:
                    position_info["company"] = company_text
                position_info["work_times"] = ""

                # Smart classification for the 3rd element
                third_element_text = (
                    await outer_positions[2].locator("span").first.inner_text()
                )
                if is_employment_type(third_element_text):
                    # Only update if we don't already have an employment type from company text
                    if not position_info["employment_type"]:
                        position_info["employment_type"] = extract_employment_type(
                            third_element_text
                        )
                    position_info["location"] = ""
                elif is_geographic_location(third_element_text):
                    position_info["location"] = third_element_text
                    # Don't clear employment_type if already set from company text
                else:
                    # Default to location for backward compatibility
                    position_info["location"] = third_element_text
                    # Don't clear employment_type if already set from company text
        else:
            # Default case
            position_info["position_title"] = ""
            if len(outer_positions) > 0:
                company_text = (
                    await outer_positions[0].locator("span").first.inner_text()
                )
                # Check if company text contains employment type after dot separator
                if "·" in company_text:
                    company_parts = company_text.split("·")
                    position_info["company"] = company_parts[0].strip()
                    # Check if the part after dot is employment type
                    if len(company_parts) > 1 and is_employment_type(
                        company_parts[1].strip()
                    ):
                        position_info["employment_type"] = extract_employment_type(
                            company_parts[1].strip()
                        )
                else:
                    position_info["company"] = company_text
            if len(outer_positions) > 1:
                position_info["work_times"] = (
                    await outer_positions[1].locator("span").first.inner_text()
                )
            position_info["location"] = ""
            # Don't clear employment_type if already set from company text

        # Validate field assignments using regex (more accurate than string checks)
        if position_info["location"] and "·" in position_info["location"]:
            # Check if location accidentally contains date ranges
            if any(
                is_date_range(part.strip())
                for part in position_info["location"].split("·")
            ):
                # Clear location if it contains date-like content
                position_info["location"] = ""

        if position_info["work_times"] and "·" in position_info["work_times"]:
            # Check if work_times contains actual date ranges
            has_dates = any(
                is_date_range(part.strip())
                for part in position_info["work_times"].split("·")
            )
            if not has_dates:
                # Clear work_times if it doesn't contain actual dates
                position_info["work_times"] = ""

        # Parse work times into dates - following Selenium approach
        if position_info["work_times"]:
            parts = position_info["work_times"].split("·")
            times = parts[0].strip() if parts else ""
            duration = parts[1].strip() if len(parts) > 1 else None

            position_info["duration"] = duration

            # Parse dates from times - handle LinkedIn format properly
            if times:
                # Handle different date formats:
                # "Oct 2024 - Apr 2025"
                # "Sep 2023 - Jan 2024"
                # "2015 -" (ongoing)
                if " - " in times:
                    date_parts = times.split(" - ")
                    position_info["from_date"] = date_parts[0].strip()
                    if len(date_parts) > 1 and date_parts[1].strip():
                        position_info["to_date"] = date_parts[1].strip()
                elif times.endswith(" -"):
                    # Ongoing position like "2015 -"
                    position_info["from_date"] = times.replace(" -", "").strip()
                else:
                    # Fallback for other formats
                    time_parts = times.split()
                    if len(time_parts) >= 2:
                        position_info["from_date"] = " ".join(time_parts[:2])

    except Exception:
        pass

    return position_info


def _parse_work_times(work_times: str) -> dict:
    """Parse work times string into from_date, to_date, and duration."""
    try:
        parts = work_times.split("·")
        times = parts[0].strip() if parts else ""
        duration = parts[1].strip() if len(parts) > 1 else None

        if times:
            time_parts = times.split(" ")
            from_date = " ".join(time_parts[:2]) if len(time_parts) >= 2 else ""
            to_date = " ".join(time_parts[3:]) if len(time_parts) > 3 else ""
        else:
            from_date = ""
            to_date = ""

        return {
            "from_date": from_date,
            "to_date": to_date,
            "duration": duration,
        }
    except Exception:
        return {
            "from_date": "",
            "to_date": "",
            "duration": None,
        }


async def _extract_clean_description(element: Optional[Locator]) -> str:
    """Extract clean description text from nested list structure.

    Args:
        element: The element containing description lists

    Returns:
        Clean description text without skills or metadata
    """
    description, _ = await extract_description_and_skills_from_element(element)
    return description


async def _extract_inner_positions(
    position_summary_text: Optional[Locator],
) -> List[Locator]:
    """Extract inner positions if multiple roles at same company."""
    inner_positions = []

    if not position_summary_text:
        return inner_positions

    try:
        # Check if there's a nested list container
        pvs_containers = await position_summary_text.locator(
            ".pvs-list__container"
        ).all()
        if pvs_containers:
            for container in pvs_containers:
                nested_items = await container.locator(
                    ".pvs-list__paged-list-item"
                ).all()
                inner_positions.extend(nested_items)
    except Exception:
        pass

    return inner_positions


async def _extract_inner_position_data(inner_position: Locator) -> Optional[dict]:
    """Extract data from inner position element."""
    try:
        link_elem = inner_position.locator("a").first
        if not await link_elem.is_visible():
            return None

        elements = await link_elem.locator("> *").all()
        if len(elements) < 2:
            return None

        position_title_elem = elements[0]

        # Intelligently detect which element contains dates vs location vs employment type
        work_times = ""
        location = ""
        employment_type = ""

        # Check elements[1] and elements[2] for date patterns, employment types, and locations
        for i in range(1, len(elements)):
            elem_text = (
                await elements[i].locator("*").first.inner_text()
                if await elements[i].is_visible()
                else ""
            )

            # Check if this element contains date patterns using regex
            has_dates = "·" in elem_text and any(
                is_date_range(part.strip()) for part in elem_text.split("·")
            )

            if has_dates and not work_times:
                work_times = elem_text
            elif is_employment_type(elem_text) and not employment_type:
                employment_type = extract_employment_type(elem_text)
            elif is_geographic_location(elem_text) and not location:
                location = elem_text
            elif not has_dates and not location and not employment_type:
                # Fallback: if we haven't assigned this text yet, check what it might be
                if is_employment_type(elem_text):
                    employment_type = extract_employment_type(elem_text)
                elif is_geographic_location(elem_text):
                    location = elem_text
                else:
                    # As last resort, if no date patterns and not clearly employment type or location,
                    # assign to location (but this shouldn't happen with improved logic)
                    location = elem_text

        title_text = (
            await position_title_elem.locator("*").first.inner_text()
            if await position_title_elem.is_visible()
            else ""
        )
        position_title = clean_single_string_duplicates(title_text)

        # Parse work times
        times_info = _parse_work_times(work_times)

        # Extract description and skills from the inner position structure
        description, skills = await extract_description_and_skills_from_element(
            inner_position
        )

        return {
            "position_title": position_title,
            "work_times": work_times,
            "location": location,
            "employment_type": employment_type,
            "description": description,
            "skills": skills,
            **times_info,
        }
    except Exception:
        return None
